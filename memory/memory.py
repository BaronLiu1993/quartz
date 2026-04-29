from pydantic import BaseModel
from pymongo import MongoClient
from typing import Literal

def get_mongo_memory_read_client():
    client = MongoClient("mongodb://localhost:27017", readPreference="secondary")
    db = client["memory"]
    return db["conversations"]

class RawConveresationModel(BaseModel):
    user_id: str
    session_id: str
    stage: str
    type: str
    raw_conversation: str

def insert_raw_conversation_memory(request: RawConveresationModel):
    try:
        client = get_mongo_memory_read_client()
        client.insert_one(request)
    except Exception as e:
        raise Exception(f"Failed to insert raw conversation memory: {str(e)}")