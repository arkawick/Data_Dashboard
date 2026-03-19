from pymongo import MongoClient

def get_mongo_collection(my_collection):
    client = MongoClient('mongodb://localhost:27017/')
    db = client['test_db'] #test_db   my_database
    collection = db[my_collection]
    return collection
