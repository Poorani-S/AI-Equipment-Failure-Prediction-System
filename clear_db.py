import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = (
    os.getenv("MONGODB_URI")
    or os.getenv("MONGO_URI")
    or os.getenv("MONGODB_ATLAS_URI")
    or "mongodb://localhost:27017"
)
DB_NAME = os.getenv("MONGODB_DB_NAME", "equipment_failure_db")

def clear_testing_data():
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        
        # Collections to clear
        collections = ["equipment", "predictions", "alerts"]
        
        print(f"Connecting to database: {DB_NAME}")
        
        for coll_name in collections:
            result = db[coll_name].delete_many({})
            print(f"Cleared collection '{coll_name}': Removed {result.deleted_count} documents.")
            
        print("Successfully removed all testing data.")
        client.close()
    except Exception as e:
        print(f"Error while clearing database: {e}")

if __name__ == "__main__":
    clear_testing_data()
