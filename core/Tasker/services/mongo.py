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

        db[collection].delete_many({})
        db[collection].insert_many(data)
