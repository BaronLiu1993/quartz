from pydantic import BaseModel
from pymongo import MongoClient

def get_mongo_read_client():
    client = MongoClient("mongodb://localhost:27017", readPreference="secondary")
    db = client["memory"]
    return db["conversations"]

class RawConveresationModel(BaseModel):
    user_id: str
    session_id: str
    raw_conversation: str

def insert_raw_conversation_memory(request: RawConveresationModel):
    try:
        client = get_mongo_read_client()
        client.insert_one({
            "user_id": request.user_id,
            "session_id": request.session_id,
            "raw_conversation": request.raw_conversation
        })
    except Exception as e:
        raise Exception(f"Failed to insert raw conversation memory: {str(e)}")