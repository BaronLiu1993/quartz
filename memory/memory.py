from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "memory"

def get_mongo_memory_db():
    return MongoClient(MONGO_URI)[DB_NAME]

class RawConveresationModel(BaseModel):
    user_id: str
    session_id: str
    stage: str
    type: str
    raw_conversation: str

class PRMetadataModel(BaseModel):
    repo_full_name: str
    pr_number: int
    title: str
    body: Optional[str]
    author_login: str
    state: str
    draft: bool
    base_sha: str
    base_ref: str
    head_sha: str
    head_ref: str
    files_changed: list[str]
    additions: int
    deletions: int
    labels: list[str]
    latest_event: str
    latest_event_at: datetime
    created_at: datetime
    updated_at: datetime
    merged: bool
    merged_at: Optional[datetime]
    diff_truncated: bool = False


def insert_raw_conversation_memory(request: RawConveresationModel) -> None:
    db = get_mongo_memory_db()
    db["conversations"].insert_one(request.model_dump())


def upsert_pr_metadata(record: PRMetadataModel) -> None:
    db = get_mongo_memory_db()
    db["pr_metadata"].create_index(
        [("repo_full_name", 1), ("pr_number", 1)], unique=True
    )
    db["pr_metadata"].update_one(
        {"repo_full_name": record.repo_full_name, "pr_number": record.pr_number},
        {"$set": record.model_dump()},
        upsert=True,
    )


def claim_delivery(delivery_id: str) -> bool:
    """Return True if this delivery_id is new, False if it has been seen before.

    GitHub redelivers webhooks on 5xx and on user retry; this gives us idempotency.
    """
    db = get_mongo_memory_db()
    db["webhook_deliveries"].create_index("delivery_id", unique=True)
    try:
        db["webhook_deliveries"].insert_one(
            {"delivery_id": delivery_id, "received_at": datetime.now(timezone.utc)}
        )
        return True
    except DuplicateKeyError:
        return False
