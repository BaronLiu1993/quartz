from __future__ import annotations
import hashlib
import hmac
import os
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from memory import (
    PRMetadataModel,
    RawConveresationModel,
    insert_raw_conversation_memory,
    upsert_pr_metadata,
)

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_WEBHOOK_SECRET = os.environ["GITHUB_WEBHOOK_SECRET"]
LOCAL_USER_ID = os.environ.get("LOCAL_USER_ID", "local")

GITHUB_API = "https://api.github.com"
HTTP_TIMEOUT = 30.0
DIFF_BYTE_LIMIT = 1_000_000  
STAGE = "pr_ingest"

GITHUB_HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "quartz-webhook",
}

def verify_signature(body: bytes, signature_header: Optional[str]) -> bool:
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(
        GITHUB_WEBHOOK_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)

def fetch_pr_diff(owner: str, repo: str, number: int) -> tuple[str, bool]:
    """Return (diff_text, truncated). Truncates at DIFF_BYTE_LIMIT bytes."""
    headers = {**GITHUB_HEADERS, "Accept": "application/vnd.github.v3.diff"}
    with httpx.Client(timeout=HTTP_TIMEOUT) as client:
        response = client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{number}",
            headers=headers,
        )
        response.raise_for_status()
        data = response.content

    truncated = len(data) > DIFF_BYTE_LIMIT
    if truncated:
        data = data[:DIFF_BYTE_LIMIT]
    return data.decode("utf-8", errors="replace"), truncated


def fetch_pr_files(owner: str, repo: str, number: int) -> list[str]:
    filenames: list[str] = []
    with httpx.Client(timeout=HTTP_TIMEOUT, headers=GITHUB_HEADERS) as client:
        page = 1
        while True:
            response = client.get(
                f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{number}/files",
                params={"per_page": 100, "page": page},
            )
            response.raise_for_status()
            batch = response.json()
            if not batch:
                break
            filenames.extend(item["filename"] for item in batch)
            if len(batch) < 100:
                break
            page += 1
    return filenames

def session_id_for(repo_full_name: str, pr_number: int) -> str:
    return f"gh:{repo_full_name}#{pr_number}"

def record_text(session_id: str, type_: str, text: str) -> None:
    insert_raw_conversation_memory(
        RawConveresationModel(
            user_id=LOCAL_USER_ID,
            session_id=session_id,
            stage=STAGE,
            type=type_,
            raw_conversation=text,
        )
    )

def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))

def save_pr_metadata(
    pr: dict[str, Any],
    repo_full_name: str,
    files: list[str],
    event: str,
    diff_truncated: bool,
) -> None:
    upsert_pr_metadata(
        PRMetadataModel(
            repo_full_name=repo_full_name,
            pr_number=pr["number"],
            title=pr["title"],
            body=pr.get("body"),
            author_login=pr["user"]["login"],
            state=pr["state"],
            draft=pr.get("draft", False),
            base_sha=pr["base"]["sha"],
            base_ref=pr["base"]["ref"],
            head_sha=pr["head"]["sha"],
            head_ref=pr["head"]["ref"],
            files_changed=files,
            additions=pr.get("additions", 0),
            deletions=pr.get("deletions", 0),
            labels=[label["name"] for label in pr.get("labels", [])],
            latest_event=event,
            latest_event_at=datetime.now(timezone.utc),
            created_at=_parse_iso(pr["created_at"]),
            updated_at=_parse_iso(pr["updated_at"]),
            merged=pr.get("merged", False),
            merged_at=_parse_iso(pr.get("merged_at")),
            diff_truncated=diff_truncated,
        )
    )

def handle_pull_request(payload: dict[str, Any]) -> None:
    action = payload.get("action")
    if action not in {"opened", "synchronize", "reopened", "closed"}:
        return

    pr = payload["pull_request"]
    repo_full_name = payload["repository"]["full_name"]
    owner, repo = repo_full_name.split("/", 1)
    number = pr["number"]
    session = session_id_for(repo_full_name, number)

    diff_text, truncated = fetch_pr_diff(owner, repo, number)
    files = fetch_pr_files(owner, repo, number)

    record_text(session, "code", diff_text)
    save_pr_metadata(pr, repo_full_name, files, f"pull_request.{action}", truncated)

def handle_pull_request_review(payload: dict[str, Any]) -> None:
    if payload.get("action") != "submitted":
        return

    review = payload["review"]
    pr = payload["pull_request"]
    repo_full_name = payload["repository"]["full_name"]
    session = session_id_for(repo_full_name, pr["number"])

    review_text = f"[{review.get('state', 'commented')}] {review.get('body') or ''}"
    record_text(session, "response", review_text)


def handle_issue_comment(payload: dict[str, Any]) -> None:
    if payload.get("action") != "created":
        return
    if not payload.get("issue", {}).get("pull_request"):
        return

    repo_full_name = payload["repository"]["full_name"]
    session = session_id_for(repo_full_name, payload["issue"]["number"])
    record_text(session, "response", payload["comment"].get("body") or "")


def route_event(event: str, payload: dict[str, Any]) -> None:
    if event == "pull_request":
        handle_pull_request(payload)
    elif event == "pull_request_review":
        handle_pull_request_review(payload)
    elif event == "issue_comment":
        handle_issue_comment(payload)
    else:
        pass