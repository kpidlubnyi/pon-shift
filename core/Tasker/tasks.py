from celery import shared_task
import logging

from .services.tasks import *
from .services.redis import *
from .services.mongo import *


logger = logging.getLogger(__name__)

@shared_task
def update_gtfs(carrier: str):    
    logger.info(f'Запуск таски з оновлення GTFS перевізника {carrier}...')
    feed = get_recent_feed(carrier)

    if not is_feed_new(feed, carrier):
        logger.info('GTFS не оновився від часу останньої провірки.')
        return 
    
    gtfs = get_gtfs(feed)
    gtfs_zip = fetch_gtfs_zip(gtfs)
    data = get_data_from_zip(gtfs_zip)
    
    try:
        import_to_staging(data, carrier)
        logger.info("Імпорт завершено! Перестановка таблиць...")
        swap_tables()
        logger.info('Перестановка успішна!')
        update_sha_in_redis(feed, carrier)
    except Exception as e:
        logger.error(f'Помилка ппід час імпорту до тестових таблиць: {e}')
    
    backup_from_regular_tables()
    logger.info('Бекап пройшов успішно!')

@shared_task
def update_realtime_gtfs(carrier: str):
    if carrier == 'ZTM':
        names = ['ZTM_RT_V', 'ZTM_RT_A']
    elif carrier == 'WKD':
        names = ['WKD_RT_V']

    feeds = [(name, get_recent_feed(name)) for name in names]
    gtfs_list = [(name, get_rt_gtfs(feed)) for name, feed in feeds]

    for name, gtfs in gtfs_list:
        entities = gtfs.get('entity')
        replace_data(name, entities)