import os
from pymongo import MongoClient


def get_mongo_collection(my_collection):
    uri     = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
    db_name = os.environ.get("DB_NAME", "test_db")
    client  = MongoClient(uri)
    return client[db_name][my_collection]
