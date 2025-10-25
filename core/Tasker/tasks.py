from celery import shared_task
from celery.signals import worker_ready
import logging

from django.conf import settings

from .services.tasks import *
from .services.redis import *
from .services.mongo import *

logger = logging.getLogger(__name__)

@shared_task
def check_gtfs_updates():
    was_any_updated = False

    for carrier in settings.ALLOWED_CARRIERS:
        if check_task_availability(carrier):
            logger.info(f'A separate task for updating GTFS for {carrier} carrier exists. Skipping...')
            continue

        feed = get_recent_feed(carrier)

        if not is_feed_new(feed, carrier):
            logger.info(f'GTFS for {carrier} carrier has not been updated since the last check.')
            continue
        else:
            if not was_any_updated:
                notify_otp_builder()
                was_any_updated = True
            
            logger.info(f"There is new GTFS for {carrier} carrier!")
            update_gtfs.apply_async(args=[feed, carrier])
        

@shared_task(queue = 'gtfs_updates')
def update_gtfs(feed, carrier: str):
    logger.info(f'Running GTFS update task for {carrier} carrier...')
    
    try:
        download_and_process_gtfs(feed, carrier)
        logger.info("Import complete! Table rearrangement...")
        swap_tables()
        logger.info('The rearrangement is successful!')
        update_sha_in_redis(feed, carrier)
    except Exception as e:
        logger.error(f'Error during import to test tables: {e}')

    backup_from_regular_tables()
    logger.info('The backup was successful!')
    gc.collect()

@worker_ready.connect
def on_worker_ready(sender, **kwargs):
    """Starts when the worker is ready"""
    if 'gtfs@' in sender.hostname:
        logger.info("GTFS worker ready! Running initial check...")
        check_gtfs_updates.apply_async()
        logger.info("Initial GTFS check scheduled!")
        
@shared_task
def update_gtfs_realtime(feed_name):
    logger.info(f'Searching recent feed for {feed_name}...')
    feed = get_recent_feed(feed_name)
    logger.info('Getting GTFS-RT...')
    gtfs = get_rt_gtfs(feed)

    entities = gtfs.get('entity')
    logger.info('Replacing GTFS-RT data in MongoDB database...')
    replace_data(feed_name, entities)

@shared_task
def update_veturilo_data():
    logger.info('Start of work on updating Veturilo data...')
    try:
        logger.info('Loading new data...')
        data = fetch_veturilo_api()        
        
        logger.info('Processing new data...')
        data = process_veturilo_data(data)
        
        logger.info('Importing new data...')
        import_veturilo_data(data)
        logger.info('Successfully completed!')
    except Exception as e:
        logger.error(f'Error during Veturilo data update: {e}')
    return
 
@shared_task
def update_scooter_data():
    try:
        logger.info('Start of work on updating scooter data...')
        
        logger.info('Loading data from API...')
        bolt_data = fetch_bolt_api()
        dott_data = fetch_dott_api()
        
        logger.info('Data processing...')
        bolt_data = standardize_scooter_data(bolt_data)
        dott_data = standardize_scooter_data(dott_data)
        data = bolt_data + dott_data

        logger.info('Data import...')
        import_scooter_data(data)
        logger.info('Successfully completed!')
    except Exception as e:
        logger.error(f'Error during scooter data update: {e}')
    return
