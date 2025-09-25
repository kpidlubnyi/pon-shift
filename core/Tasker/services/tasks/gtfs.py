import requests
import zipfile
import logging
import csv
import io
from typing import List, Generator

from django.db import transaction, close_old_connections, reset_queries, connection
from django.conf import settings
from django.core.management import CommandError

from ...models.staging import *
from .common import *
from ..redis import *


logger = logging.getLogger(__name__)


def validate_carrier(options):
    name = options['carrier'][0]

    if name not in settings.ALLOWED_CARRIERS and name != 'all':
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

def get_data_from_zip(zip_file: zipfile.ZipFile) -> Generator[tuple[str, dict], None, None]:
    """Генератор, який повертає дані по одному рядку"""
    required_files = set(REQUIRED_MODELS.keys())

    try:
        for file_info in zip_file.infolist():
            filename, extension = file_info.filename.split('.')

            if filename in required_files and extension in {'csv', 'txt'}:
                logger.info(f'Обробка файлу {filename}...')
                with zip_file.open(file_info) as file:
                    decoded_file = io.TextIOWrapper(file, encoding='utf-8')
                    reader = csv.DictReader(decoded_file)
                    
                    for row in reader:
                        yield filename, row
                        
                logger.info(f'Файл {filename} оброблено')
                        
    except Exception as e:
        logger.error(f'Не вдалося взяти дані з zip-файлу: {e}')
        return

def process_file_in_batches(zip_file: zipfile.ZipFile, filename: str, batch_size: int = 10000) -> Generator[List[dict], None, None]:
    """Генератор, який повертає дані файлу батчами"""
    try:
        file_info = None
        for info in zip_file.infolist():
            if info.filename.startswith(filename) and info.filename.endswith(('.csv', '.txt')):
                file_info = info
                break
                
        if not file_info:
            logger.warning(f'Файл {filename} не знайдено в архіві')
            return
            
        with zip_file.open(file_info) as file:
            decoded_file = io.TextIOWrapper(file, encoding='utf-8')
            reader = csv.DictReader(decoded_file)
            batch = []

            for row in reader:
                batch.append(row)
                if len(batch) >= batch_size:
                    yield batch
                    batch = []
                    gc.collect()
                    
            if batch:
                yield batch
                
    except Exception as e:
        logger.error(f'Помилка під час обробки файлу {filename}: {e}')
        return
    

def process_model_batch(carrier: str, model, batch_data: List[dict]) -> int:
    if not batch_data:
        return 0
        
    try:
        records = convert_to_model_objects(carrier, model, batch_data)
        if records:
            model.objects.bulk_create(records, batch_size=200_000)
        return len(records)
    except Exception as e:
        logger.error(f"Помилка під час обробки батчу для {model._meta.label}: {e}")
        raise

def import_to_staging(zip_file: zipfile.ZipFile, carrier: str, batch_size: int = 200_000):
    importing_order = list(REQUIRED_MODELS.keys())
    deleted = delete_old_data(carrier)
    
    if not deleted:
        logger.warning(f'Даних перевізника {carrier} не було знайдено!' +
                       'Якщо це перший запуск для даного перевізника - зігноруй попередження,' + 
                       'в іншому разі - негайно провір базу даних!')

    available_files = set()
    for file_info in zip_file.infolist():
        filename = file_info.filename.split('.')[0]
        if filename in importing_order:
            available_files.add(filename)

    for filename in importing_order:
        if filename not in available_files:
            logger.warning(f'Файл {filename}.txt не було знайдено у GTFS перевізника {carrier}!')
            continue
            
        logger.info(f'Початок обробки файлу {filename}')
        model = REQUIRED_MODELS[filename]
        total_imported = 0
        
        for batch in process_file_in_batches(zip_file, filename, batch_size):
            try:
                with transaction.atomic():
                    imported_count = process_model_batch(carrier, model, batch)
                    total_imported += imported_count
                    
                reset_queries()
                close_old_connections()
                gc.collect()
                                
            except Exception as e:
                logger.error(f'Помилка під час імпорту батчу для {filename}: {e}')
                raise
                
        logger.info(f'Завершено обробку {filename}: {total_imported} записів')

def download_and_process_gtfs(feed, carrier: str):
    url = get_from_feed(feed, 'url')
    
    logger.info('Початок завантаження GTFS архіву...')
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    gtfs_buffer = io.BytesIO()
    
    total_size = 0
    chunk_size = 8192
    
    for chunk in response.iter_content(chunk_size=chunk_size):
        if chunk:
            gtfs_buffer.write(chunk)
            total_size += len(chunk)
    
    logger.info(f'Завантаження завершено. Розмір: {total_size // (1024 * 1024)} MB')
    
    gtfs_buffer.seek(0)
    
    try:
        with zipfile.ZipFile(gtfs_buffer) as zip_file:
            import_to_staging(zip_file, carrier, batch_size=200_000)
    finally:
        gtfs_buffer.close()
        del gtfs_buffer
        gc.collect()

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
                    sequence_name_staging = f'"{model_staging_name}_id_seq"'
                    sequence_name = f'"{model_name}_id_seq"'
                    
                    cursor.execute(f"SELECT setval('{sequence_name}', {max_id+1});")
                    cursor.execute(f"SELECT setval('{sequence_name_staging}', {max_id+1});")