from __future__ import annotations
import json
import logging
from typing import Dict, Optional
from fastapi import APIRouter, Header, HTTPException, Request
from memory.conversation_memory import claim_delivery
from service.pr_service import verify_signature
from async_queue.pr_task import process_pr_event

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/webhooks/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(default=None),
    x_github_event: str = Header(...),
    x_github_delivery: str = Header(...),
) -> Dict[str, str]:
    logger.info("Webhook received | event=%s delivery_id=%s", x_github_event, x_github_delivery)
    body = await request.body() 
    if not verify_signature(body, x_hub_signature_256):
        logger.warning("Invalid webhook signature | delivery_id=%s", x_github_delivery)
        raise HTTPException(status_code=401, detail="invalid signature")
    
    if not claim_delivery(x_github_delivery):
        logger.error("Duplicate delivery id | delivery_id=%s", x_github_delivery)
        raise HTTPException(status_code=500, detail="duplicate delivery id")
    
    payload = json.loads(body)
    process_pr_event.delay(x_github_event, payload)
    logger.info("Webhook queued | event=%s delivery_id=%s", x_github_event, x_github_delivery)
    return {"status": "queued"}
