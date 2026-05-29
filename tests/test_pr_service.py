import hashlib
import hmac
import sys
from pathlib import Path
from unittest.mock import patch, Mock

from dotenv import load_dotenv

sys.path.append(str(Path(__file__).resolve().parents[1]))
load_dotenv()

from service.constants import GITHUB_WEBHOOK_SECRET
from service.pr_service import verify_signature,route_event,handle_pull_request,handle_pull_request_review,handle_issue_comment,session_id_for,record_text,trigger_review_agent

def test_verify_signature_rejects_missing_signature()-> None:
    body = b'{"action":"opened"}'

    result = verify_signature(body, None)

    assert result == False

def test_verify_signature_rejects_bad_signature()-> None:
    body = b'{"action":"opened"}'

    result= verify_signature(body, "sha256=bad")

    assert result == False

def test_verify_signature_accept_valid_signature()-> None:
    body = b'{"action":"opened"}'
    signature = "sha256=" + hmac.new(GITHUB_WEBHOOK_SECRET.encode(),body, hashlib.sha256,).hexdigest()

    result = verify_signature(body,signature)

    assert result == True

def test_route_event_routes_pull_request() -> None:
    payload = {"action": "opened"}
    mock_handle_pull_request = Mock()

    with patch("service.pr_service.handle_pull_request", mock_handle_pull_request):
        route_event("pull_request", payload)
    
    mock_handle_pull_request.assert_called_once_with(payload)

def test_route_event_routes_pull_request_review()-> None:
    payload = {"action": "submitted"}
    mock_handle_pull_request_review = Mock()

    with patch("service.pr_service.handle_pull_request_review", mock_handle_pull_request_review):
        route_event("pull_request_review", payload)
    
    mock_handle_pull_request_review.assert_called_once_with(payload)

def test_route_event_routes_issue_comment() -> None:
    payload = {"action": "created"}
    fake_handle_issue_comment = Mock()

    with patch("service.pr_service.handle_issue_comment", fake_handle_issue_comment):
        route_event("issue_comment", payload)

    fake_handle_issue_comment.assert_called_once_with(payload)

def test_route_event_ignores_unknown_event() -> None:
    payload = {"action": "whatever"}

    fake_handle_pull_request = Mock()
    fake_handle_pull_request_review = Mock()
    fake_handle_issue_comment = Mock()

    with patch("service.pr_service.handle_pull_request", fake_handle_pull_request):
        with patch("service.pr_service.handle_pull_request_review",fake_handle_pull_request_review,):
            with patch("service.pr_service.handle_issue_comment", fake_handle_issue_comment):
                route_event("unknown_event", payload)

    fake_handle_pull_request.assert_not_called()
    fake_handle_pull_request_review.assert_not_called()
    fake_handle_issue_comment.assert_not_called()

def test_handle_pull_request_ignores_unsupported_action() -> None:
    payload = {"action": "edited"}

    fake_fetch_pr_diff = Mock()
    fake_fetch_pr_files = Mock()
    fake_record_text = Mock()
    fake_save_pr_metadata = Mock()
    fake_trigger_review_agent = Mock()

    with patch("service.pr_service.fetch_pr_diff", fake_fetch_pr_diff):
        with patch("service.pr_service.fetch_pr_files", fake_fetch_pr_files):
            with patch("service.pr_service.record_text", fake_record_text):
                with patch("service.pr_service.save_pr_metadata", fake_save_pr_metadata):
                    with patch("service.pr_service.trigger_review_agent", fake_trigger_review_agent):
                        handle_pull_request(payload)

    fake_fetch_pr_diff.assert_not_called()
    fake_fetch_pr_files.assert_not_called()
    fake_record_text.assert_not_called()
    fake_save_pr_metadata.assert_not_called()
    fake_trigger_review_agent.assert_not_called()

def test_handle_pull_request_processes_supported_action() -> None:
    payload = {
        "action": "opened",
        "repository": {"full_name": "octo/demo",},
        "pull_request": {
            "number": 7,
            "title": "Add counter",
            "body": "Adds a simple counter",
            "user": {"login": "alice"},
            "state": "open",
            "draft": False,
            "base": {
                "sha": "base-sha",
                "ref": "main",
            },
            "head": {
                "sha": "head-sha",
                "ref": "feature-counter",
            },
            "additions": 10,
            "deletions": 2,
            "labels": [{"name": "hdl"}],
            "created_at": "2026-05-25T12:00:00Z",
            "updated_at": "2026-05-25T12:10:00Z",
            "merged": False,
            "merged_at": None,
        },
    }

    fake_fetch_pr_diff = Mock(return_value=("diff text", False))
    fake_fetch_pr_files = Mock(return_value=["rtl/counter.sv"])
    fake_record_text = Mock()
    fake_save_pr_metadata = Mock()
    fake_trigger_review_agent = Mock()

    with patch("service.pr_service.fetch_pr_diff", fake_fetch_pr_diff):
        with patch("service.pr_service.fetch_pr_files", fake_fetch_pr_files):
            with patch("service.pr_service.record_text", fake_record_text):
                with patch("service.pr_service.save_pr_metadata", fake_save_pr_metadata):
                    with patch("service.pr_service.trigger_review_agent", fake_trigger_review_agent):
                        handle_pull_request(payload)

    fake_fetch_pr_diff.assert_called_once_with("octo", "demo", 7)
    fake_fetch_pr_files.assert_called_once_with("octo", "demo", 7)
    fake_trigger_review_agent.assert_called_once_with("octo/demo", 7)

    fake_record_text.assert_called_once_with(
        "gh:octo/demo#7",
        "code",
        "diff text",
    )

    fake_save_pr_metadata.assert_called_once_with(
        payload["pull_request"],
        "octo/demo",
        ["rtl/counter.sv"],
        "pull_request.opened",
        False,
    )

def test_handle_pull_request_review_ignores_non_submitted_action() -> None:
    payload = {"action": "edited"}

    fake_record_text = Mock()

    with patch("service.pr_service.record_text", fake_record_text):
        handle_pull_request_review(payload)

    fake_record_text.assert_not_called()

def test_handle_pull_request_review_records_submitted_review() -> None:
    payload = {
        "action": "submitted",
        "repository": {
            "full_name": "octo/demo",
        },
        "pull_request": {
            "number": 7,
        },
        "review": {
            "state": "approved",
            "body": "Looks good",
        },
    }

    fake_record_text = Mock()

    with patch("service.pr_service.record_text", fake_record_text):
        handle_pull_request_review(payload)

    fake_record_text.assert_called_once_with(
        "gh:octo/demo#7",
        "response",
        "[approved] Looks good",
    )

def test_handle_issue_comment_ignores_non_created_action() -> None:
    payload = {"action": "edited"}

    fake_record_text = Mock()

    with patch("service.pr_service.record_text", fake_record_text):
        handle_issue_comment(payload)

    fake_record_text.assert_not_called()

def test_handle_issue_comment_ignores_non_pr_comment() -> None:
    payload = {
        "action": "created",
        "issue": {},
        "repository": {
            "full_name": "octo/demo",
        },
        "comment": {
            "body": "hello",
        },
    }

    fake_record_text = Mock()

    with patch("service.pr_service.record_text", fake_record_text):
        handle_issue_comment(payload)

    fake_record_text.assert_not_called()

def test_handle_issue_comment_records_pr_comment() -> None:
    payload = {
        "action": "created",
        "repository": {
            "full_name": "octo/demo",
        },
        "issue": {
            "number": 7,
            "pull_request": {"url": "https://api.github.com/repos/octo/demo/pulls/7",},
        },
        "comment": {
            "body": "Can you check the reset behavior?",
        },
    }

    fake_record_text = Mock()

    with patch("service.pr_service.record_text", fake_record_text):
        handle_issue_comment(payload)

    fake_record_text.assert_called_once_with(
        "gh:octo/demo#7",
        "response",
        "Can you check the reset behavior?",
    )

def test_session_id_for_builds_github_pr_session_id()->None:
    result = session_id_for("baron", 8)
    assert result == "gh:baron#8"


def test_record_text_inserts_conversation_memory() -> None:
    fake_insert = Mock()

    with patch("service.pr_service.insert_raw_conversation_memory", fake_insert):
        record_text("gh:octo/demo#7", "code", "diff text")

    fake_insert.assert_called_once()

    inserted_model = fake_insert.call_args.args[0]

    assert inserted_model.session_id == "gh:octo/demo#7"
    assert inserted_model.type == "code"
    assert inserted_model.raw_conversation == "diff text"

def test_trigger_review_agent_calls_review_pull_request()-> None:
    fake_review_pull_request = Mock()

    with patch("agents.review_agent.review_pull_request", fake_review_pull_request):
        trigger_review_agent("baron", 9)

    fake_review_pull_request.assert_called_once_with("baron", 9)
