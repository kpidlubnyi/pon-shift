import requests
import zipfile
import logging
import csv
import io

from django.db import transaction, close_old_connections, reset_queries, connection
from django.conf import settings
from django.core.management import CommandError

from ...models.staging import *
from .common import *
from ..redis import *


logger = logging.getLogger(__name__)


def validate_carrier(options):
    name = options['carrier'][0]

    if name not in settings.ALLOWED_CARRIERS:
        raise CommandError(f'{name}: перевізник не облуговується або його не існує!')
    return name

def validate_command_args(options: dict) -> tuple[str, dict]:
    carrier = validate_carrier(options)    
    cron_names = ['minute', 'hour', 'day_of_month', 'month_of_year', 'day_of_week']
    cron_args = {name: options[name][0] for name in cron_names}
    return carrier, cron_args

def get_from_feed(feed, key):
    return feed.get('feeds')[0].get('feed_versions')[0].get(key)

def get_recent_feed(carrier: str):  
    onestop_id = settings.ONESTOP_IDS[carrier]
    api_key = settings.TRANSITLAND_API_KEY
    url = f'https://transit.land/api/v2/rest/feeds?onestop_id={onestop_id}&api_key={api_key}'

    feed = requests.get(url)
    feed.raise_for_status()

    feed = feed.json()
    return feed

def is_feed_new(feed, carrier:str):
    redis_sha = get_redis_sha(carrier)
    feed_sha = get_from_feed(feed, 'sha1')

    return feed_sha != redis_sha

def update_sha_in_redis(feed, carrier:str):
    feed_sha = get_from_feed(feed, 'sha1')
    set_sha_in_redis(feed_sha, carrier)

def get_gtfs(feed):
    url = get_from_feed(feed, 'url')
    return requests.get(url).content

def fetch_gtfs_zip(gtfs_zip) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(gtfs_zip))

def get_data_from_zip(zip_file: zipfile.ZipFile) -> dict[str, list]:
    required_files = set(REQUIRED_MODELS.keys())
    data = dict()

    try:
        for file_info in zip_file.infolist():
            filename, extension = file_info.filename.split('.')

            if filename in required_files and extension in {'csv', 'txt'}:
                with zip_file.open(file_info) as file:
                    decoded_file = io.TextIOWrapper(file, encoding='utf-8')
                    reader = csv.DictReader(decoded_file)
                    data[filename] = list(reader)
    except Exception as e:
        logger.error(f'Не вдалося взяти дані з zip-файлу: {e}')
        return
    
    return data


def import_to_staging(data, carrier: str):
    importing_order = list(REQUIRED_MODELS.keys())
    deleted = delete_old_data(carrier)
    if not deleted:
        logger.warning(f'Даних перевізника {carrier} не було знайдено!' +
                       'Якщо це перший запуск для даного перевізника - зігноруй попередження,' + 
                       'в іншому разі - негайно провір базу даних!')

    for filename in importing_order:
        if filename not in data:
            logger.warning(f'Файл {filename}.txt не було знайдено у GTFS перевізника {carrier}!')
            continue
        
        with transaction.atomic():
            model = REQUIRED_MODELS[filename]
            data_for_model = data[filename]
            imported_count = process_model_data(carrier, model, data_for_model)
                
        reset_queries()
        close_old_connections()
        gc.collect()


    return

def get_table_name(model: models.Model):
    return model._meta.db_table

def swap_tables():
    def rename_table(old:str, new:str) -> str:
        return f'ALTER TABLE "{old}" RENAME TO "{new}";'
    
    with transaction.atomic():
        for model_staging in list(REQUIRED_MODELS.values()) + [ShapeStaging]:
            model_name = get_table_name(model_staging._base_model)
            model_name_staging = get_table_name(model_staging)
            model_name_old = model_name + '_OLD'

            with connection.cursor() as cursor:
                cursor.execute(rename_table(model_name, model_name_old))
                cursor.execute(rename_table(model_name_staging, model_name))
                cursor.execute(rename_table(model_name_old, model_name_staging))

def backup_from_regular_tables():
    CarrierStaging.objects.all().delete()
    models_staging = list(REQUIRED_MODELS.values())
    models_staging.insert(1, ShapeStaging)
    
    with transaction.atomic():
        with connection.cursor() as cursor:
            for model_staging in models_staging:
                model = model_staging._base_model

                if model.objects.count() > 0:
                    model_name = get_table_name(model)
                    model_staging_name = get_table_name(model_staging)

                    cursor.execute(f'INSERT INTO "{model_staging_name}" SELECT * FROM "{model_name}";')
                
                if hasattr(model, 'id'):
                    cursor.execute(f'SELECT MAX(id) FROM "{model_staging_name}"')
                    max_id = cursor.fetchone()[0]
                    logger.info(f'Max id: {max_id}')
                    sequence_name_staging = f'"{model_staging_name}_id_seq"'
                    sequence_name = f'"{model_name}_id_seq"'
                    
                    cursor.execute(f"SELECT setval('{sequence_name}', {max_id+1});")
                    cursor.execute(f"SELECT setval('{sequence_name_staging}', {max_id+1});")