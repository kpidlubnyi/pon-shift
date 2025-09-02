from celery import shared_task
import logging

from .services.task import *


logger = logging.getLogger(__name__)

@shared_task
def update_gtfs():    
    logger.info('Початок роботи завдання з оновлення GTFS...')
    feed = get_recent_feed()

    if not is_feed_new(feed):
        logger.info('GTFS не оновився від часу останньої провірки.')
        return 
    
    gtfs = get_gtfs(feed)
    gtfs_zip = fetch_gtfs_zip(gtfs)
    data = get_data_from_zip(gtfs_zip)
    import_data(data)
    logger.info("Імпорт завершено!")
