import requests
import zipfile
import logging
import csv
import io
import gc

from django.conf import settings
from django.core.management import CommandError
from django.db import transaction


from ..services.redis import *
from ..models import *


ACCEPTED_CARRIERS = ['ztm']
REQUIRED_MODELS = {
    'calendar_dates': CalendarDate,
    'routes': Route,
    'shapes': ShapeSequence,
    'stops': Stop,
    'trips': Trip,
    'stop_times': StopTime,
    'frequencies': Frequence,
}
INTEGER_FIELDS_WITH_NULL = {'hidden_block_id',}


logger = logging.getLogger(__name__)


def validate_carrier(options):
    name = options['carrier'][0]

    if name not in ACCEPTED_CARRIERS:
        raise CommandError(f'{name}: перевізник не облуговується або його не існує!')
    return name

def validate_command_args(options: dict) -> tuple[str, dict]:
    carrier = validate_carrier(options)    
    cron_names = ['minute', 'hour', 'day_of_month', 'month_of_year', 'day_of_week']
    cron_args = {name: options[name][0] for name in cron_names}
    return carrier, cron_args

def get_from_feed(feed, key):
    return feed.get('feeds')[0].get('feed_versions')[0].get(key)

def get_recent_feed():    
    onestop_id = settings.ZTM_ONESTOP_ID
    api_key = settings.TRANSITLAND_API_KEY
    url = f'https://transit.land/api/v2/rest/feeds?onestop_id={onestop_id}&api_key={api_key}'

    feed = requests.get(url)
    feed.raise_for_status()

    feed = feed.json()
    return feed

def is_feed_new(feed):
    redis_sha = get_redis_sha()
    feed_sha = get_from_feed(feed, 'sha1') 
    if  feed_sha != redis_sha:
        set_sha_in_redis(feed_sha)
        return True
    return False

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

@transaction.atomic
def import_data(data):
    def convert_to_model_objects(model: models.Model, data_batch: list) -> list:
        """Конвертує батч даних в об'єкти моделі"""
        allowed_fields = [field.attname for field in model._meta.fields]
        records = []
        
        if model == ShapeSequence:
            unique_shape_ids = {row.get('shape_id') for row in data_batch}
            
            shapes = []
            for shape_id in unique_shape_ids:
                shapes.append(Shape(shape_id=shape_id))

            Shape.objects.bulk_create(shapes, ignore_conflicts=True)

        for row in data_batch:
            filtered_row = dict()

            try:
                for k, v in row.items():
                    if k in allowed_fields:
                        filtered_row[k] = None if not v and k in INTEGER_FIELDS_WITH_NULL else v
                records.append(model(**filtered_row))
            except Exception as e:
                logger.warning(f"Помилка в рядку: {e}")
                raise
                
        return records
    
    def process_model_data(model: models.Model, model_data: list, batch_size: int = 200_000):
        """Обробляє дані моделі по батчах"""
        total_rows = len(model_data)
        logger.info(f"Початок імпорту {total_rows} записів для {model._meta.label}")
        
        deleted_count = model.objects.all().delete()[0]
        logger.info(f"Видалено {deleted_count} старих записів для {model._meta.label}")
        
        imported_count = 0
        
        for i in range(0, total_rows, batch_size):
            batch = model_data[i:i + batch_size]
            
            try:
                records = convert_to_model_objects(model, batch)
                model.objects.bulk_create(records, batch_size=50_000)
                imported_count += len(records)
                logger.info(f'Імпортовано логів: {imported_count}')
                
                del records
                del batch
                gc.collect()
                
            except Exception as e:
                logger.error(f"Помилка під час імпорту батчу {i}-{i+len(batch)} для {model._meta.label}: {e}")
                raise
        
        logger.info(f"Завершено імпорт {imported_count} записів для {model._meta.label}")
        return imported_count

    importing_order = list(REQUIRED_MODELS.keys())
    total_imported = {}
    
    try:
        for filename in importing_order:
            model: models.Model = REQUIRED_MODELS[filename]
            data_for_model = data[filename]
            imported_count = process_model_data(model, data_for_model)
            total_imported[filename] = imported_count
            gc.collect()
    except Exception as e:
        logger.error(f'Критична помилка під час імпорту: {e}')
        raise
    