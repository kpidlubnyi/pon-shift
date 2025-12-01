from pymongo import MongoClient

from django.conf import settings


class MongoConnection:
    def __init__(self):
        self.connection_string = settings.MONGO_URI
        self.database_name = settings.MONGO_DB_NAME
        self.client = None
        self.db = None
    
    def __enter__(self):
        self.client = MongoClient(
            self.connection_string,
            maxPoolSize=10,
            retryWrites=True,
            serverSelectionTimeoutMS=5000
        )
        self.db = self.client[self.database_name]
        return self.db
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            self.client.close()


def create_collection(name: str) -> None:
    with MongoConnection() as db:
        db.create_collection(name)
        

def replace_data(collection: str, data: list[dict]) -> None:
    with MongoConnection() as db:
        if collection not in db.list_collection_names():
            create_collection(collection)
        
        if collection.split('_')[-1] == 'A':
            for alert in data:
                alert['id'] = alert['id'].replace('/', ':')

        db[collection].delete_many({})
        db[collection].insert_many(data)


def prune_underscore_id(doc: dict) -> dict:
    try:
        del doc['_id']
        return doc
    except Exception as e:
        raise Exception(f'Error while pruning mongo document: {e}')


def get_rt_vehicle_data(trip_id:str):
    carrier_code, trip_id = trip_id.split(':', maxsplit=1)

    if carrier_code not in settings.ALLOWED_CARRIERS:
        raise ValueError('Carrier code not in allowed carriers!')
    
    collection_name = f'{carrier_code}_RT_V'
    
    with MongoConnection() as db:
        key = {
            'WTP': 'vehicle.trip.trip_id',
            'WKD': 'trip_update.trip.trip_id'
        }.get(carrier_code)
        
        doc = db[collection_name].find_one({key: trip_id})

        if not doc:
            raise ValueError(f"There is no realtime data for vehicle with trip id '{trip_id}'!")
        
        doc = prune_underscore_id(doc) if doc else None
        return carrier_code, doc


def get_wtp_alerts() -> list[dict]:
    with MongoConnection() as db:
        alerts = db['WTP_RT_A'].find()
        alerts = [prune_underscore_id(alert) for alert in alerts]
        return alerts


def get_wtp_alert(alert_id: str) -> dict:    
    with MongoConnection() as db:
        alert = db['WTP_RT_A'].find_one({'id': alert_id})
        alert = prune_underscore_id(alert)
        return alert
