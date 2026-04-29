"""HTTP layer for the GitHub PR webhook.

Verifies signature, dedupes via X-GitHub-Delivery, then queues the work
on FastAPI BackgroundTasks so we return inside GitHub's 10s timeout.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request

from memory import claim_delivery
from service.pr_service import route_event, verify_signature


router = APIRouter()


@router.post("/webhooks/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str = Header(...),
    x_github_delivery: str = Header(...),
) -> dict[str, str]:
    body = await request.body() 

    if not verify_signature(body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="invalid signature")

    if not claim_delivery(x_github_delivery):
        return {"status": "duplicate"}

    payload = json.loads(body)
    background_tasks.add_task(route_event, x_github_event, payload)
    return {"status": "queued"}
