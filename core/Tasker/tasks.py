from celery import shared_task
import logging

from .services.tasks import *
from .services.redis import *
from .services.mongo import *


logger = logging.getLogger(__name__)

@shared_task
def update_gtfs(carrier: str):
    """Оптимізована версія update_gtfs"""
    logger.info(f'Запуск таски з оновлення GTFS перевізника {carrier}...')
    
    feed = get_recent_feed(carrier)
    if not is_feed_new(feed, carrier):
        logger.info('GTFS не оновився від часу останньої провірки.')
        return

    try:
        download_and_process_gtfs(feed, carrier)
        logger.info("Імпорт завершено! Перестановка таблиць...")
        swap_tables()
        logger.info('Перестановка успішна!')
        update_sha_in_redis(feed, carrier)
    except Exception as e:
        logger.error(f'Помилка під час імпорту до тестових таблиць: {e}')

    backup_from_regular_tables()
    logger.info('Бекап пройшов успішно!')
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
    logger.info('Початок роботи таски з оновлення даних Veturilo...')
    try:
        logger.info('Завантаження нових данних...')
        data = fetch_veturilo_api()        
        
        logger.info('Обробка нових даних...')
        data = process_veturilo_data(data)
        
        logger.info('Імпорт нових даних...')
        import_veturilo_data(data)
        logger.info('Завершено успішно!')
    except Exception as e:
        logger.error(f'Помилка під час оновлення даних Veturilo: {e}')
    return
 
@shared_task
def update_scooter_data():
    try:
        logger.info('Початок роботи таски з оновлення даних самокатів...')
        
        logger.info('Завантаження даних з API...')
        bolt_data = fetch_bolt_api()
        dott_data = fetch_dott_api()
        
        logger.info('Обробка даних...')
        bolt_data = standardize_scooter_data(bolt_data)
        dott_data = standardize_scooter_data(dott_data)
        data = bolt_data + dott_data

        logger.info('Імпорт даних...')
        import_scooter_data(data)
        logger.info('Завершено успішно!')
    except Exception as e:
        logger.error(f'Помилка під час оновлення даних самокатів: {e}')
    return

