import logging
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel
from pymongo.errors import DuplicateKeyError

from memory.config import get_mongo_db

logger = logging.getLogger(__name__)

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
    try:
        db = get_mongo_db()
        db["conversations"].insert_one(request.model_dump())
    except DuplicateKeyError:
        logger.info(
            "Duplicate conversation memory, skipping | user_id=%s session_id=%s stage=%s type=%s",
            request.user_id,
            request.session_id,
            request.stage,
            request.type,
        )

def upsert_pr_metadata(record: PRMetadataModel) -> None:
    db = get_mongo_db()
    try:
        db["pr_metadata"].create_index(
        [("repo_full_name", 1), ("pr_number", 1)], unique=True
        )
        db["pr_metadata"].update_one(
            {"repo_full_name": record.repo_full_name, "pr_number": record.pr_number},
            {"$set": record.model_dump()},
            upsert=True,
        )
    except DuplicateKeyError:
        logger.info(
            "Duplicate PR metadata, skipping | repo=%s pr_number=%s",
            record.repo_full_name,
            record.pr_number,
        )


def claim_delivery(delivery_id: str) -> bool:
    db = get_mongo_db()
    db["webhook_deliveries"].create_index("delivery_id", unique=True)
    print("inserting delivery" + delivery_id)
    try:
        db["webhook_deliveries"].insert_one(
            {"delivery_id": delivery_id, "received_at": datetime.now(timezone.utc)}
        )
        return True
    except DuplicateKeyError:   
        logger.info("Duplicate delivery ID received, skipping: %s", delivery_id)
        return False


