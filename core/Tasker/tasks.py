from celery import shared_task
import logging

from .services.tasks import *
from .services.redis import *
from .services.mongo import *


logger = logging.getLogger(__name__)

@shared_task
def update_gtfs(carrier: str):
    logger.info(f'Running GTFS update task for carrier {carrier}...')
    
    feed = get_recent_feed(carrier)
    if not is_feed_new(feed, carrier):
        logger.info('GTFS has not been updated since the last check.')
        return

    try:
        download_and_process_gtfs(feed, carrier)
        logger.info("Import complete! Table rearrangement...")
        swap_tables()
        logger.info('The rearrangement is successful!')
        update_sha_in_redis(feed, carrier)
    except Exception as e:
        logger.error(f'Error during import to test tables: {e}')

    backup_from_regular_tables()
    logger.info('The backup was successful.!')
    gc.collect()

@shared_task
def update_gtfs_realtime(carrier: str):
    if carrier == 'ZTM':
        names = ['ZTM_RT_V', 'ZTM_RT_A']
    elif carrier == 'WKD':
        names = ['WKD_RT_V']

    feeds = [(name, get_recent_feed(name)) for name in names]
    gtfs_list = [(name, get_rt_gtfs(feed)) for name, feed in feeds]

    for name, gtfs in gtfs_list:
        entities = gtfs.get('entity')
        replace_data(name, entities)

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

