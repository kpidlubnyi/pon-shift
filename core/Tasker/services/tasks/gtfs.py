import requests
import zipfile
import logging
import csv
import io

from django.db import transaction, models
from django.conf import settings
from django.core.management import CommandError

from .common import *
from ..redis import *


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
INTEGER_FIELDS_WITH_NULL = {'hidden_block_id'}


logger = logging.getLogger('Tasker.tasks')


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
    