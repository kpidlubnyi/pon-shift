import logging
import gc

from django.db import close_old_connections

from ...models.staging import *

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


logger = logging.getLogger(__name__)


def delete_old_data(carrier: str):
    """Видаляє старі дані даного перевізника з staging таблиць"""
    close_old_connections()
    return CarrierStaging.objects.filter(carrier_code=carrier).delete()[0]

def convert_to_model_objects(carrier: str, model: models.Model, data_batch: list) -> list:
    """Конвертує батч даних в об'єкти моделі"""

    def add_prefix(val):
        nonlocal carrier
        return f'{carrier}-{val}'
    
    allowed_fields = [field.attname for field in model._meta.fields]
    models_with_fk_to_trips = {rel.related_model for rel in TripStaging._meta.related_objects if rel.one_to_many}
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
                
            if model == TripStaging:
                filtered_row['trip_id'] = add_prefix(filtered_row['trip_id'])
            elif model in models_with_fk_to_trips:
                if model == TransferStaging:
                    filtered_row['from_trip_id'] = add_prefix(filtered_row['from_trip_id'])
                    filtered_row['to_trip_id'] = add_prefix(filtered_row['to_trip_id'])
                else:
                    filtered_row['trip_id'] = add_prefix(filtered_row['trip_id'])
                    
            records.append(model(**filtered_row))
        except Exception as e:
            logger.warning(f"Помилка в рядку: {e}")
            raise
            
    return records

def process_model_data(carrier: str, model: models.Model, model_data: list, batch_size: int = 100_000,):
    """Обробляє дані моделі по батчах"""
    total_rows = len(model_data)
    logger.info(f"Початок імпорту {total_rows} записів для {model._meta.label}")
    
    imported_count = 0
    
    for i in range(0, total_rows, batch_size):
        batch = model_data[i:i + batch_size]
        
        try:
            records = convert_to_model_objects(carrier, model, batch)
            model.objects.bulk_create(records, batch_size=15_000)
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
