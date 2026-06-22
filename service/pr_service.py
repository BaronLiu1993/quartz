from __future__ import annotations
import hashlib
import hmac
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional
import httpx
import re

from memory.conversation_memory import (
    PRMetadataModel,
    RawConveresationModel,
    insert_raw_conversation_memory,
    upsert_pr_metadata,
)
from .constants import (
    GITHUB_WEBHOOK_SECRET,
    GITHUB_API,
    LOCAL_USER_ID,
    HTTP_TIMEOUT,
    DIFF_BYTE_LIMIT,
    STAGE,
    GITHUB_HEADERS,
)

logger = logging.getLogger(__name__)

def verify_signature(body: bytes, signature_header: Optional[str]) -> bool:
    logger.debug("Verifying GitHub webhook signature")
    if not signature_header or not signature_header.startswith("sha256="):
        logger.warning("Invalid signature header format")
        return False
    expected = "sha256=" + hmac.new(
        GITHUB_WEBHOOK_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    is_valid = hmac.compare_digest(expected, signature_header)
    logger.info(f"Signature verification: {'valid' if is_valid else 'invalid'}")
    return is_valid

def fetch_pr_diff(owner: str, repo: str, number: int) -> tuple[str, bool]:
    logger.info(f"Fetching PR diff | owner={owner} | repo={repo} | number={number}")
    headers = {**GITHUB_HEADERS, "Accept": "application/vnd.github.v3.diff"}
    try:
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            response = client.get(
                f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{number}",
                headers=headers,
            )
            response.raise_for_status()
            data = response.content

        truncated = len(data) > DIFF_BYTE_LIMIT
        if truncated:
            logger.warning(f"PR diff truncated | original_size={len(data)} | limit={DIFF_BYTE_LIMIT}")
            data = data[:DIFF_BYTE_LIMIT]
        logger.info(f"Successfully fetched PR diff | size={len(data)} | truncated={truncated}")
        return data.decode("utf-8", errors="replace"), truncated
    except Exception as e:
        logger.error(f"Failed to fetch PR diff | error={str(e)}", exc_info=True)
        raise


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

def post_pr_comment(repo_full_name:str, pr_number:int, body:str) -> dict[str,Any]:
    with httpx.Client(timeout=HTTP_TIMEOUT,headers =GITHUB_HEADERS) as client:
        response = client.post(
            f"{GITHUB_API}/repos/{repo_full_name}/issues/{pr_number}/comments",json={"body": body}
        )
        response.raise_for_status()
        return response.json()

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

def trigger_review_agent(repo_full_name: str, pr_number: int):
    from agents.review_agent import review_pull_request
    from service.agent_service import build_pr_context
    from agents.orchestrator_agent import plan_pr_workflow

    pr_context = build_pr_context(repo_full_name, pr_number)
    workflow_plan = plan_pr_workflow(pr_context)
    steps = workflow_plan["steps"]

    decision = workflow_plan.get("decision")
    if decision is not None and decision.reason:
        record_text(
            session_id_for(repo_full_name, pr_number),
            "response",
            f"Orchestrator decision: {decision.reason}",
        )

    if "execution" in steps:
        from agents.execution_agent import execute_changed_files

        metadata = pr_context.get("metadata") or {}
        files_changed = metadata.get("files_changed") or []
        execution_result = execute_changed_files(files_changed)
        record_text(
            session_id_for(repo_full_name, pr_number),
            "response",
            f"Execution result: {execution_result}",
        )

    if "review" not in steps:
        logger.info("Orchestrator skipped review | repo=%s pr=%s", repo_full_name, pr_number)
        return
    
    try:
        review = review_pull_request(repo_full_name, pr_number)
    except Exception:
        logger.exception("Failed to generate PR review")
        return

    session = session_id_for(repo_full_name, pr_number)
    record_text(session, "response", review.summary)

    try:
        post_pr_comment(repo_full_name, pr_number, review.summary)
    except Exception:
        logger.exception("Failed to post PR summary comment")
    
    #SHA is Git's name for the unique fingerprint of one commit
    latest_pr_commit_sha = (pr_context.get("metadata") or {}).get("head_sha")

    if latest_pr_commit_sha is None:
        logger.warning(
            "Skipping inline PR comments because the latest PR commit SHA is unavailable"
        )
        return

    for comment in review.comments:
        formatted_comment_body = format_inline_comment_body(comment.body,comment.replacement_code)
        try:
            post_pr_inline_comment(
                repo_full_name,
                pr_number,
                latest_pr_commit_sha,
                comment.path,
                comment.line,
                formatted_comment_body,
            )
        except Exception:
            logger.exception("Failed to post inline PR review comment")

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
    trigger_review_agent(repo_full_name,number )

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
    logger.info(f"Routing GitHub event | event={event}")
    try:
        if event == "pull_request":
            logger.debug(f"Handling pull_request event | action={payload.get('action')}")
            handle_pull_request(payload)
        elif event == "pull_request_review":
            logger.debug(f"Handling pull_request_review event, action={payload.get('action')}")
            handle_pull_request_review(payload)
        elif event == "issue_comment":
            logger.debug(f"Handling issue_comment event, action={payload.get('action')}")
            handle_issue_comment(payload)
        else:
            logger.warning(f"Unknown event type, event={event}")
            pass
    except Exception as e:
        logger.error(f"Failed to route event, event={event}, error={str(e)}", exc_info=True)
        raise

def post_pr_inline_comment(repo_full_name:str, pr_number:int, commit_id:str, path:str, line:int, body:str)-> dict[str,Any]:
    with httpx.Client(timeout=HTTP_TIMEOUT, headers= GITHUB_HEADERS) as client:
        response = client.post(
            f"{GITHUB_API}/repos/{repo_full_name}/pulls/{pr_number}/comments",
            json={
                "body": body,
                "commit_id": commit_id,
                "path": path,
                "line": line,
                "side":"RIGHT",
            }
        )
        response.raise_for_status()
        return response.json()

def format_inline_comment_body(body:str, replacement_code:str | None,)->str:
    if not replacement_code:
        return body
    
    return f"""{body}

```suggestion
{replacement_code.rstrip()}
```"""
#suggestion is wrote here, since github sees that special suggestion block and displays the code as an applyable suggestion

def get_changed_lines_by_file(diff_text: str) -> dict[str, set[int]]:
    changed_lines: dict[str, set[int]] = {}
    current_path: str | None = None
    new_line_number: int | None = None

    for diff_line in diff_text.splitlines():
        # Reset the file state when the diff begins another file.
        if diff_line.startswith("diff --git "):
            current_path = None
            new_line_number = None
            continue

        # Record the path of the new version of the changed file.
        if diff_line.startswith("+++ b/"):
            current_path = diff_line.removeprefix("+++ b/")
            changed_lines.setdefault(current_path, set())
            continue

        # Skip file metadata because it is not a line of code.
        if diff_line.startswith("+++ /dev/null") or diff_line.startswith("--- "):
            continue

        # Read the new-file starting line from a hunk header such as @@ -3,13 +3,16 @@.
        if diff_line.startswith("@@"):
            match = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", diff_line)

            # Only update the counter when the hunk header has the expected format.
            if match:
                new_line_number = int(match.group(1))
            continue

        # Ignore lines until both a target file and its new-file line number are known.
        if current_path is None or new_line_number is None:
            continue

        # Added lines are valid locations for an inline PR comment.
        if diff_line.startswith("+"):
            changed_lines[current_path].add(new_line_number)
            new_line_number += 1
        # Deleted lines and the no-newline marker do not exist in the new file.
        elif diff_line.startswith("-") or diff_line.startswith("\\"):
            continue
        else:
            # Unchanged context still occupies a line in the new file.
            new_line_number += 1

    return changed_lines

def is_valid_inline_comment_location(
    path: str,
    line: int,
    changed_lines: dict[str, set[int]],
) -> bool:
    return line in changed_lines.get(path, set())