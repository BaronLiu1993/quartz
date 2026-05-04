import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://root:example@localhost:27017/quartz?authSource=admin")
DB_NAME = "memory"

def get_mongo_client():
    """Get a new MongoDB client instance."""
    return MongoClient(MONGO_URI)


def get_mongo_db():
    """Get the memory database connection."""
    client = get_mongo_client()
    return client[DB_NAME]
