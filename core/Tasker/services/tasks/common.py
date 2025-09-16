import logging
import gc

from ...models import *


logger = logging.getLogger('Tasker.tasks')


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
                    if v:
                        filtered_row[k] = None if v in {None, ''} else v
                
            records.append(model(**filtered_row))
        except Exception as e:
            logger.warning(f"Помилка в рядку: {e}")
            raise
            
    return records

def process_model_data(model: models.Model, model_data: list, batch_size: int = 100_000):
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
            model.objects.bulk_create(records, batch_size=20_000)
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
