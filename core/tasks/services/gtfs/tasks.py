import requests
import zipfile
import logging
import io
import gc
import os

from django.conf import settings
from django.core.management import CommandError
from django_celery_beat.models import PeriodicTask, CrontabSchedule, IntervalSchedule

from common.services.redis import *
from common.models import Route
from .download import get_from_feed
from .db_operations import import_to_staging, refresh_trip_stops


logger = logging.getLogger(__name__)

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


def cache_carriers_info():
    def cache_routes_set_info(carrier_code:str):
        available_routes = list(
            Route.objects
                .filter(carrier__carrier_code=carrier_code)
                .values_list('route_id', flat=True)
        )

        if not available_routes:
            logger.warning(f"There is no routes for '{carrier_code}' carrier. Ignore it if it's a first cycle of GTFS updating.")
            return True

        key = f'{carrier_code}_ROUTES_SET'
        return recreate_redis_set(key, *available_routes)

    for carrier_code in settings.ALLOWED_CARRIERS:
        assert cache_routes_set_info(carrier_code)


def clear_gtfs_cache(carrier:str):
    try:
        keys_to_delete = ['STOP_LIST', f'{carrier}_ROUTES_SET']

        if carrier == 'WTP':
            keys_to_delete += list(get_redis_keys_by_regexp('WTP_ROUTE_SCHEDULE_*'))
            
        remove_from_redis(*keys_to_delete)
        logger.info(f"Cleared {len(keys_to_delete)} GTFS cache keys for {carrier}")
        
    except Exception as e:
        logger.error(f'Error while clearing cache from redis: {e}')


def check_task_availability(carrier: str) -> bool:
    task_name = f'GTFS_UPDATING_{carrier}'
    
    try:
        task = PeriodicTask.objects.get(name=task_name)
    except Exception:
        return False
    
    return True


def validate_carrier(options):
    name = options['carrier'][0]

    if name not in settings.ALLOWED_CARRIERS:
        raise CommandError(f'{name}: the carrier is not serviced or does not exist!')
    return name


def validate_cron(options) -> CrontabSchedule | None:
    try:
        cron_names = ['minute', 'hour', 'day_of_month', 'month_of_year', 'day_of_week']
        cron_args = {name: options[name] for name in cron_names}
        cron, _ = CrontabSchedule.objects.get_or_create(**cron_args)
        return cron
    except Exception as e:
        logger.error(f'Error during validation of crontab arguments: {e}')
        return None
    

def validate_interval(options) -> IntervalSchedule | None:
    try:
        interval_names = ['every', 'period']
        interval_args = {name: options[name] for name in interval_names}
        interval, _ = IntervalSchedule.objects.get_or_create(**interval_args)
        return interval
    except Exception as e:
        logger.error(f'Error during validation of interval arguments: {e}')
        return None


def update_sha_in_redis(feed, carrier:str):
    feed_sha = get_from_feed(feed, 'sha1')
    set_hash_in_redis(feed_sha, carrier)


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
