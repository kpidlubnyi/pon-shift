import zipfile
import csv
import logging
import io
import gc
from typing import Generator, List

from django.db import connection

from .models import *

logger = logging.getLogger(__name__)

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


def convert_gtfs_data_to_model_objects(carrier: str, model: models.Model, data_batch: list) -> list:
    """Converts a batch of data into model objects"""
     
    allowed_fields = get_allowed_fields(model)
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
            
            if model in models_should_have_carrier_prefix:
                filtered_row = add_carrier_prefix_to_fields(carrier, model, filtered_row)                   
            
            records.append(model(**filtered_row))
        except Exception as e:
            logger.warning(f"Error in line: {e}")
            raise
            
    return records

