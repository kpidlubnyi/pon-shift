import zipfile
import logging

from django.db import transaction, close_old_connections, reset_queries

from trips.models import *
from .models import *
from .process import *


logger = logging.getLogger(__name__)


def delete_old_gtfs_data(carrier: str):
    """Deletes old data for this carrier from staging tables"""
    close_old_connections()
    return CarrierStaging.objects.filter(carrier_code=carrier).delete()[0]


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
