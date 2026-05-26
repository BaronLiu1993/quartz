import sys
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.append(str(Path(__file__).resolve().parents[1]))

from service.agent_service import fetch_pr_metadata,fetch_pr_conversations, build_pr_context

def test_fetch_pr_metadata_queries_by_repo_and_pr_number() -> None:
    expected_metadata = {
        "repo_full_name": "baron",
        "pr_number": 9,
        "title":"baron love jere"
    }

    fake_collection = Mock()
    fake_collection.find_one.return_value = expected_metadata

    fake_db = {"pr_metadata": fake_collection,}

    with patch("service.agent_service.get_mongo_db", return_value=fake_db):
        result = fetch_pr_metadata("baron", 9)

    assert result == expected_metadata
    fake_collection.find_one.assert_called_once_with({"repo_full_name": "baron", "pr_number": 9})

def test_fetch_pr_conversations_queries_by_session_id() -> None:
    expected_conversations = [
        {
            "session_id": "gh:baron#9",
            "type": "code",
            "raw_conversation": "diff text",
        },
        {
            "session_id": "gh:baron#9",
            "type": "response",
            "raw_conversation": "Looks good",
        },
    ]

    fake_collection = Mock()
    fake_collection.find.return_value = expected_conversations

    fake_db = {"conversations": fake_collection}

    with patch("service.agent_service.get_mongo_db", return_value=fake_db):
        result = fetch_pr_conversations("gh:baron#9")

    assert result == expected_conversations
    fake_collection.find.assert_called_once_with(
        {"session_id": "gh:baron#9"}
    )

def test_build_pr_context_combines_metadata_and_conversations() -> None:
    metadata = {
        "repo_full_name": "baron",
        "pr_number": 9,
        "title": "baron love jere",
    }

    conversations = [
        {
            "session_id": "gh:baron#9",
            "type": "code",
            "raw_conversation": "diff text",
        },
        {
            "session_id": "gh:baron#9",
            "type": "response",
            "raw_conversation": "Looks good",
        },
        {
            "session_id": "gh:baron#9",
            "type": "other",
            "raw_conversation": "ignore me for now",
        },
    ]

    with patch("service.agent_service.fetch_pr_metadata", return_value=metadata):
        with patch("service.agent_service.fetch_pr_conversations", return_value=conversations):
            result = build_pr_context("baron", 9)

    assert result["repo_full_name"] == "baron"
    assert result["pr_number"] == 9
    assert result["session_id"] == "gh:baron#9"
    assert result["metadata"] == metadata
    assert result["code_entries"] == [conversations[0]]
    assert result["response_entries"] == [conversations[1]]