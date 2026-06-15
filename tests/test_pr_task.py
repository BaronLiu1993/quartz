import sys
from pathlib import Path
from unittest.mock import Mock, patch

from dotenv import load_dotenv

sys.path.append(str(Path(__file__).resolve().parents[1]))
load_dotenv()

from async_queue.pr_task import process_pr_event


def test_process_pr_event_returns_success_when_route_event_succeeds() -> None:
    fake_route_event = Mock(return_value=None)

    with patch("async_queue.pr_task.route_event", fake_route_event):
        result = process_pr_event.run("pull_request", {"action": "opened"})

    assert result == {"status": "success", "result": None}
    fake_route_event.assert_called_once_with("pull_request", {"action": "opened"})


def test_process_pr_event_returns_failed_when_route_event_raises() -> None:
    fake_route_event = Mock(side_effect=RuntimeError("boom"))

    with patch("async_queue.pr_task.route_event", fake_route_event):
        result = process_pr_event.run("pull_request", {"action": "opened"})

    assert result == {"status": "failed", "error": "boom"}
    fake_route_event.assert_called_once_with("pull_request", {"action": "opened"})