import requests
import zipfile
import logging
import csv
import io
import gc
import os
from typing import List, Generator

from django.db import transaction, close_old_connections, reset_queries, connection
from django.db.models import Q
from django.conf import settings
from django.core.management import CommandError
from django_celery_beat.models import PeriodicTask, CrontabSchedule

from common.models.staging import *
from common.services.redis import *
from Trips.models import *

logger = logging.getLogger(__name__)


REQUIRED_MODELS = {
    'agency': CarrierStaging,
    'calendar_dates': CalendarDateStaging,
    'routes': RouteStaging,
    'shapes': ShapeSequenceStaging,
    'stops': StopStaging,
    'trips': TripStaging,
    'stop_times': StopTimeStaging,
    'frequencies': FrequenceStaging,
    'transfers': TransferStaging,
}


FLAGS_DIR = "/app/flags"

def ensure_flags_dir():
    """Make sure the shared flag directory exists and is writable."""
    if not os.path.exists(FLAGS_DIR):
        try:
            os.makedirs(FLAGS_DIR, exist_ok=True)
            logger.info(f"Created missing flags directory: {FLAGS_DIR}")
        except Exception as e:
            logger.error(f"Failed to create flags directory {FLAGS_DIR}: {e}")
            raise


def create_flag_file(service: str, about: str):
    """
    Creates a flag file for ORS/OTP so that their watchdog containers 
    can detect and rebuild graphs with new data.
    """
    assert service in {'ors', 'otp'}, f"Invalid service: {service}"
    assert about in {'map', 'gtfs'}, f"Invalid flag type: {about}"

    ensure_flags_dir()
    flag_file = f"{service}_there_is_new_{about}"
    path = os.path.join(FLAGS_DIR, flag_file)

    try:
        if not os.path.exists(path):
            with open(path, "w") as f:
                f.write(".")
            logger.info(f"Flag file created: {path}")
        else:
            logger.info(f"Flag file already exists: {path}")
    except Exception as e:
        logger.error(f"Failed to create flag file {path}: {e}")


def notify_about_new_gtfs():
    """Notify OTP watchdog about new GTFS data, unless it's the first import."""
    create_flag_file('otp', 'gtfs')


def notify_about_new_map():
    """Notify both ORS and OTP watchdogs about new map availability."""
    create_flag_file('otp', 'map')
    create_flag_file('ors', 'map')


def check_task_availability(carrier: str) -> bool:
    task_name = f'GTFS_UPDATING_{carrier}'
    
    try:
        task = PeriodicTask.objects.get(name=task_name)
    except Exception:
        return False
    
    return True

def delete_old_gtfs_data(carrier: str):
    """Deletes old data for this carrier from staging tables"""
    close_old_connections()
    return CarrierStaging.objects.filter(carrier_code=carrier).delete()[0]

def get_allowed_fields(model: models.Model) -> list:
    return [field.attname for field in model._meta.fields]

def convert_gtfs_data_to_model_objects(carrier: str, model: models.Model, data_batch: list) -> list:
    """Converts a batch of data into model objects"""

    def add_prefix(val):
        nonlocal carrier
        return f'{carrier}-{val}'
    
    allowed_fields = get_allowed_fields(model)
    trip_related_models = TripStaging._meta.related_objects
    models_with_trip_field = {TripStaging} | {rel.related_model for rel in trip_related_models if rel.one_to_many}
    records = []

    if model == CarrierStaging:
        carrier_name = data_batch[0]['agency_name']
        carrier_code = carrier
        carrier = CarrierStaging(carrier_name=carrier_name, carrier_code=carrier_code)
        return [carrier]

    carrier_obj = CarrierStaging.objects.get(carrier_code=carrier)
    
    if model == ShapeSequenceStaging:
        unique_shape_ids = {row.get('shape_id') for row in data_batch}
        
        shapes = []
        for shape_id in unique_shape_ids:
            shapes.append(ShapeStaging(shape_id=shape_id, carrier=carrier_obj))

        ShapeStaging.objects.bulk_create(shapes, ignore_conflicts=True)

    for row in data_batch:
        filtered_row = dict()

        try:
            filtered_row['carrier'] = carrier_obj 
            for k, v in row.items():
                if k in allowed_fields:
                    filtered_row[k] = None if v in {None, ''} else v
            
            if model in models_with_trip_field:
                if model == TransferStaging:
                    filtered_row['from_trip_id'] = add_prefix(filtered_row['from_trip_id'])
                    filtered_row['to_trip_id'] = add_prefix(filtered_row['to_trip_id'])
                else:
                    filtered_row['trip_id'] = add_prefix(filtered_row['trip_id'])
                    
            records.append(model(**filtered_row))
        except Exception as e:
            logger.warning(f"Error in line: {e}")
            raise
            
    return records


def validate_carrier(options):
    name = options['carrier'][0]

    if name not in settings.ALLOWED_CARRIERS:
        raise CommandError(f'{name}: the carrier is not serviced or does not exist!')
    return name

def validate_cron(options):
    try:
        cron_names = ['minute', 'hour', 'day_of_month', 'month_of_year', 'day_of_week']
        cron_args = {name: options[name] for name in cron_names}
        cron, _ = CrontabSchedule.objects.get_or_create(**cron_args)
        return cron
    except Exception as e:
        logger.error(f'Error during validation of crontab arguments: {e}')
        return None
    
def validate_command_args(options: dict) -> tuple[str, dict]:
    carrier = validate_carrier(options)
    cron_args = validate_cron(options)    
    return carrier, cron_args

def get_from_feed(feed, key):
    return feed.get('feeds')[0].get('feed_versions')[0].get(key)

def get_recent_feed(carrier: str):  
    onestop_id = settings.ONESTOP_IDS[carrier]
    api_key = settings.TRANSITLAND_API_KEY
    url = f'https://transit.land/api/v2/rest/feeds?onestop_id={onestop_id}&api_key={api_key}'

    feed = requests.get(url)
    feed.raise_for_status()

    return feed.json()

def is_feed_new(feed, carrier:str):
    redis_sha = get_hash_from_redis(carrier)
    feed_sha = get_from_feed(feed, 'sha1')

    return feed_sha != redis_sha

def update_sha_in_redis(feed, carrier:str):
    feed_sha = get_from_feed(feed, 'sha1')
    set_hash_in_redis(feed_sha, carrier)

def get_gtfs(feed):
    url = get_from_feed(feed, 'url')
    return requests.get(url).content

def fetch_gtfs_zip(gtfs_zip) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(gtfs_zip))

def get_data_from_zip(zip_file: zipfile.ZipFile) -> Generator[tuple[str, dict], None, None]:
    """Generator that returns data one row at a time"""
    required_files = set(REQUIRED_MODELS.keys())

    try:
        for file_info in zip_file.infolist():
            filename, extension = file_info.filename.split('.')

            if filename in required_files and extension in {'csv', 'txt'}:
                logger.info(f'Processing file {filename}...')
                with zip_file.open(file_info) as file:
                    decoded_file = io.TextIOWrapper(file, encoding='utf-8')
                    reader = csv.DictReader(decoded_file)
                    
                    for row in reader:
                        yield filename, row
                        
                logger.info(f'File {filename} processed')
                        
    except Exception as e:
        logger.error(f'Unable to retrieve data from zip file: {e}')
        return

def process_file_in_batches(zip_file: zipfile.ZipFile, filename: str, batch_size: int = 100_000) -> Generator[List[dict], None, None]:
    """Generator that returns file data in batches"""
    try:
        file_info = None
        for info in zip_file.infolist():
            if info.filename.startswith(filename) and info.filename.endswith(('.csv', '.txt')):
                file_info = info
                break
                
        if not file_info:
            logger.warning(f'File {filename} not found in archive')
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
        logger.error(f'Error while processing file {filename}: {e}')
        return
    
def bulk_copy_to_db(model, records: list):
    """Uses PostgreSQL COPY for fast import"""
    if not records:
        return 0

    model_fields = {f.attname: f for f in model._meta.fields if f.attname != 'id'}
    fields = list(model_fields.keys())

    buffer = io.StringIO()
    for record in records:
        row = []
        for field_name in fields:
            value = getattr(record, field_name, None)
            
            if value is None:
                row.append('\\N')
            elif isinstance(value, bool):
                row.append('t' if value else 'f')
            else:
                str_value = str(value)
                str_value = str_value.replace('\\', '\\\\')
                str_value = str_value.replace('\n', '\\n')
                str_value = str_value.replace('\r', '\\r')
                str_value = str_value.replace('\t', '\\t')
                row.append(str_value)
                
        buffer.write('\t'.join(row) + '\n')

    buffer.seek(0)

    table_name = model._meta.db_table

    try:
        with connection.cursor() as cursor:
            cursor.copy_from(
                buffer, 
                table_name, 
                columns=fields,
                null='\\N'
            )
        logger.info(f"Successfully copied {len(records)} records to {table_name}")
        return len(records)
    except Exception as e:
        logger.error(f"Error during COPY for {model._meta.label}: {e}")
        logger.error(f"Table: {table_name}")
        logger.error(f"Fields: {fields}")
        logger.error(f"First record sample: {getattr(records[0], fields[0], 'N/A') if records else 'No records'}")
        raise

def process_model_batch(carrier: str, model: models.Model, batch_data: List[dict]) -> int:
    if not batch_data:
        return 0
        
    try:
        records = convert_gtfs_data_to_model_objects(carrier, model, batch_data)
        if records:
            bulk_copy_to_db(model, records)
        return len(records)
    except Exception as e:
        logger.error(f"Error during batch processing for {model._meta.label}: {e}")
        raise

def import_to_staging(zip_file: zipfile.ZipFile, carrier: str, batch_size: int = 500_000):
    importing_order = list(REQUIRED_MODELS.keys())
    deleted = delete_old_gtfs_data(carrier)
    
    if not deleted:
        logger.warning(f'No data found for carrier {carrier}!' +
                       'If this is the first launch for this carrier, ignore the warning,' + 
                       'otherwise, check the database immediately!')

    available_files = set()
    for file_info in zip_file.infolist():
        filename = file_info.filename.split('.')[0]
        if filename in importing_order:
            available_files.add(filename)

    for filename in importing_order:
        if filename not in available_files:
            logger.warning(f'The file {filename}.txt was not found in GTFS carrier {carrier}!')
            continue
            
        logger.info(f'Start processing the file {filename}')
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
                logger.error(f'Error during batch import for {filename}: {e}')
                raise
                
        logger.info(f'Processing of {filename} completed: {total_imported} records')

def download_and_process_gtfs(feed, carrier: str):
    url = get_from_feed(feed, 'url')
    
    logger.info('Start downloading GTFS archive...')
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    gtfs_buffer = io.BytesIO()
    
    total_size = 0
    chunk_size = 128_000
    
    for chunk in response.iter_content(chunk_size=chunk_size):
        if chunk:
            gtfs_buffer.write(chunk)
            total_size += len(chunk)
    
    logger.info(f'Download complete. Size: {total_size // (1024 * 1024)} MB')
    
    gtfs_buffer.seek(0)
    
    try:
        with zipfile.ZipFile(gtfs_buffer) as zip_file:
            import_to_staging(zip_file, carrier, batch_size=500_000)
    finally:
        gtfs_buffer.close()
        del gtfs_buffer
        gc.collect()

    refresh_trip_stops(carrier)

def get_table_name(model: models.Model):
    return model._meta.db_table

def swap_tables():
    def rename_table(old:str, new:str) -> str:
        return f'ALTER TABLE "{old}" RENAME TO "{new}";'
    
    with transaction.atomic():
        for model_staging in list(REQUIRED_MODELS.values()) + [ShapeStaging, TripStopsStaging]:
            model_name = get_table_name(model_staging._base_model)
            model_name_staging = get_table_name(model_staging)
            model_name_old = model_name + '_OLD'

            with connection.cursor() as cursor:
                cursor.execute(rename_table(model_name, model_name_old))
                cursor.execute(rename_table(model_name_staging, model_name))
                cursor.execute(rename_table(model_name_old, model_name_staging))

def backup_from_regular_tables():
    CarrierStaging.objects.all().delete()
    models_staging = list(REQUIRED_MODELS.values()) + [TripStopsStaging]
    models_staging.insert(1, ShapeStaging)
    
    with transaction.atomic():
        with connection.cursor() as cursor:
            for model_staging in models_staging:
                model = model_staging._base_model
                model_name = get_table_name(model)
                model_staging_name = get_table_name(model_staging)

                if model.objects.count() > 0:
                    cursor.execute(f'INSERT INTO "{model_staging_name}" SELECT * FROM "{model_name}";')
                
                    if hasattr(model, 'id'):
                        cursor.execute(f'SELECT MAX(id) FROM "{model_staging_name}"')
                        max_id = cursor.fetchone()[0]
                        
                        if max_id is not None:
                            sequence_name_staging = f'"{model_staging_name}_id_seq"'
                            sequence_name = f'"{model_name}_id_seq"'
                            
                            cursor.execute(f"SELECT setval('{sequence_name}', {max_id+1});")
                            cursor.execute(f"SELECT setval('{sequence_name_staging}', {max_id+1});")


def toggle_carrier_fk(enable=True):
    with connection.cursor() as cursor:
        if not enable:
            cursor.execute('ALTER TABLE "trips_TripStops_Staging" DROP CONSTRAINT IF EXISTS "trips_TripStops_Staging_carrier_id_fkey";')
        else:
            cursor.execute('''
                ALTER TABLE "trips_TripStops_Staging"
                ADD CONSTRAINT "trips_TripStops_Staging_carrier_id_fkey"
                FOREIGN KEY (carrier_id) REFERENCES "common_Carriers_Staging"(id)
                ON DELETE CASCADE;
            ''')


def refresh_trip_stops(carrier_code):
    logger.info("Running TripStops materialized view refresher...")
    carrier = CarrierStaging.objects.get(carrier_code=carrier_code)
    
    toggle_carrier_fk(enable=False)
    with transaction.atomic():
        query, params = TripStopsStaging._get_definition(**{'t.carrier_id':carrier.pk})
        
        insertion_query = f"""
            INSERT INTO "trips_TripStops_Staging" (
                trip_id,
                direction_id,
                route_id,
                stop_ids,
                carrier_id
            )
            {query};
        """

        with connection.cursor() as cursor:
            cursor.execute(insertion_query, params)
        
    toggle_carrier_fk(enable=True)
    logger.info(f"Data for {carrier_code} carrier in TripStops table was successfully updated!")
