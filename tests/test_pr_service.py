import hashlib
import hmac
import sys
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock

from dotenv import load_dotenv

sys.path.append(str(Path(__file__).resolve().parents[1]))
load_dotenv()

from service.constants import GITHUB_WEBHOOK_SECRET
from service.pr_service import verify_signature,route_event,handle_pull_request,handle_pull_request_review,handle_issue_comment,session_id_for,record_text,trigger_review_agent,post_pr_comment, post_pr_inline_comment, format_inline_comment_body, get_changed_lines_by_file, is_valid_inline_comment_location
from agents.review_agent import InlineReviewComment, PullRequestReview

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

def test_trigger_review_agent_still_records_when_github_post_fails()-> None:
    fake_review_pull_request = Mock(
        return_value=PullRequestReview(summary="AI review text", comments=[])
    )
    fake_record_text = Mock()
    fake_post_pr_comment = Mock(side_effect=RuntimeError("github down"))
    fake_build_pr_context = Mock(return_value={"repo_full_name": "baron", "pr_number": 9})
    fake_plan_pr_workflow = Mock(return_value={"steps": ["review"]})

    with patch("agents.review_agent.review_pull_request", fake_review_pull_request):
        with patch("service.agent_service.build_pr_context", fake_build_pr_context):
            with patch("agents.orchestrator_agent.plan_pr_workflow", fake_plan_pr_workflow):
                with patch("service.pr_service.record_text", fake_record_text):
                    with patch("service.pr_service.post_pr_comment", fake_post_pr_comment):
                        trigger_review_agent("baron", 9)
    fake_review_pull_request.assert_called_once_with("baron", 9)
    fake_build_pr_context.assert_called_once_with("baron", 9)
    fake_plan_pr_workflow.assert_called_once_with({"repo_full_name": "baron", "pr_number": 9})
    fake_record_text.assert_called_with(
        "gh:baron#9",
        "response",
        "AI review text",
    )
    fake_post_pr_comment.assert_called_once_with("baron",9,"AI review text")


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
    expected_inline_comment_body = """`clear` is synchronous. Add a short comment.

```suggestion
// clear is sampled on the rising clock edge
```"""

    fake_review_pull_request = Mock(
        return_value=PullRequestReview(
            summary="Quartz found one suggestion.",
            comments=[
                InlineReviewComment(
                    path="examples/hdl/counter.sv",
                    line=14,
                    body="`clear` is synchronous. Add a short comment.",
                    replacement_code="// clear is sampled on the rising clock edge",
                )
            ],
        )
    )
    fake_record_text = Mock()
    fake_post_pr_comment = Mock()
    fake_post_pr_inline_comment = Mock()
    pr_context = {
        "repo_full_name": "baron",
        "pr_number": 9,
        "metadata": {"head_sha": "abc123"},
    }
    fake_build_pr_context = Mock(return_value=pr_context)
    fake_plan_pr_workflow = Mock(return_value={"steps": ["review"]})

    with patch("agents.review_agent.review_pull_request", fake_review_pull_request):
        with patch("service.agent_service.build_pr_context", fake_build_pr_context):
            with patch("agents.orchestrator_agent.plan_pr_workflow", fake_plan_pr_workflow):
                with patch("service.pr_service.record_text", fake_record_text):
                    with patch("service.pr_service.post_pr_comment", fake_post_pr_comment):
                        with patch(
                            "service.pr_service.post_pr_inline_comment",
                            fake_post_pr_inline_comment,
                        ):
                            trigger_review_agent("baron", 9)

    fake_review_pull_request.assert_called_once_with("baron", 9)
    fake_build_pr_context.assert_called_once_with("baron", 9)
    fake_plan_pr_workflow.assert_called_once_with(pr_context)
    fake_record_text.assert_called_once_with(
        "gh:baron#9",
        "response",
        "Quartz found one suggestion.",
    )
    fake_post_pr_comment.assert_called_once_with("baron", 9, "Quartz found one suggestion.")
    fake_post_pr_inline_comment.assert_called_once_with(
        "baron",
        9,
        "abc123",
        "examples/hdl/counter.sv",
        14,
        expected_inline_comment_body,
    )


def test_trigger_review_agent_skips_inline_comment_outside_changed_lines() -> None:
    fake_review_pull_request = Mock(
        return_value=PullRequestReview(
            summary="Quartz found one concern.",
            comments=[
                InlineReviewComment(
                    path="examples/hdl/counter.sv",
                    line=50,
                    body="This line is not part of the PR diff.",
                )
            ],
        )
    )
    fake_record_text = Mock()
    fake_post_pr_comment = Mock()
    fake_post_pr_inline_comment = Mock()
    pr_context = {
        "repo_full_name": "baron",
        "pr_number": 9,
        "metadata": {"head_sha": "abc123"},
        "code_entries": [
            {
                "raw_conversation": """\
diff --git a/examples/hdl/counter.sv b/examples/hdl/counter.sv
--- a/examples/hdl/counter.sv
+++ b/examples/hdl/counter.sv
@@ -3,13 +3,16 @@ module counter #(
) (
    input  logic             clk,
    input  logic             reset_n,
+    input  logic             clear,
    input  logic             enable,
    output logic [WIDTH-1:0] count
);

    always_ff @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            count <= '0;
+        end else if (clear) begin
+            count <= '0;
        end else if (enable) begin
            count <= count + 1'b1;
        end
    end
"""
            }
        ],
    }
    fake_build_pr_context = Mock(return_value=pr_context)
    fake_plan_pr_workflow = Mock(return_value={"steps": ["review"]})

    with patch("agents.review_agent.review_pull_request", fake_review_pull_request):
        with patch("service.agent_service.build_pr_context", fake_build_pr_context):
            with patch("agents.orchestrator_agent.plan_pr_workflow", fake_plan_pr_workflow):
                with patch("service.pr_service.record_text", fake_record_text):
                    with patch("service.pr_service.post_pr_comment", fake_post_pr_comment):
                        with patch(
                            "service.pr_service.post_pr_inline_comment",
                            fake_post_pr_inline_comment,
                        ):
                            trigger_review_agent("baron", 9)

    fake_post_pr_comment.assert_called_once_with("baron", 9, "Quartz found one concern.")
    fake_post_pr_inline_comment.assert_not_called()

def test_post_pr_comment_posts_comment_to_github()-> None:
    fake_response = Mock()
    fake_response.json.return_value = {"id": 123}

    fake_client = Mock()
    fake_client.post.return_value = fake_response

    fake_context = MagicMock()
    fake_context.__enter__.return_value = fake_client
    fake_context.__exit__.return_value = None

    with patch("service.pr_service.httpx.Client", return_value=fake_context):
        result = post_pr_comment("octo/demo", 7, "AI review text")
    
    assert result == {"id": 123}
    fake_client.post.assert_called_once_with(
    "https://api.github.com/repos/octo/demo/issues/7/comments",json={"body": "AI review text"},
    )
    fake_response.raise_for_status.assert_called_once()

def test_trigger_review_agent_does_not_record_or_post_when_review_generation_fails()->None:
    fake_review_pull_request = Mock(side_effect=RuntimeError("openai down"))
    fake_record_text = Mock()
    fake_post_pr_comment = Mock()
    fake_build_pr_context = Mock(return_value={"repo_full_name": "baron", "pr_number": 9})
    fake_plan_pr_workflow = Mock(return_value={"steps": ["review"]})

    with patch("agents.review_agent.review_pull_request", fake_review_pull_request):
        with patch("service.agent_service.build_pr_context", fake_build_pr_context):
            with patch("agents.orchestrator_agent.plan_pr_workflow", fake_plan_pr_workflow):
                with patch("service.pr_service.record_text", fake_record_text):
                    with patch("service.pr_service.post_pr_comment", fake_post_pr_comment):
                        trigger_review_agent("baron", 9)

    fake_review_pull_request.assert_called_once_with("baron", 9)
    fake_build_pr_context.assert_called_once_with("baron", 9)
    fake_plan_pr_workflow.assert_called_once_with({"repo_full_name": "baron", "pr_number": 9})
    fake_record_text.assert_not_called()
    fake_post_pr_comment.assert_not_called()

def test_trigger_review_agent_skips_review_when_orchestrator_excludes_review() -> None:
    fake_review_pull_request = Mock()
    fake_record_text = Mock()
    fake_post_pr_comment = Mock()
    fake_build_pr_context = Mock(return_value={"repo_full_name": "baron", "pr_number": 9})
    fake_plan_pr_workflow = Mock(return_value={"steps": []})

    with patch("agents.review_agent.review_pull_request", fake_review_pull_request):
        with patch("service.agent_service.build_pr_context", fake_build_pr_context):
            with patch("agents.orchestrator_agent.plan_pr_workflow", fake_plan_pr_workflow):
                with patch("service.pr_service.record_text", fake_record_text):
                    with patch("service.pr_service.post_pr_comment", fake_post_pr_comment):
                        trigger_review_agent("baron", 9)

    fake_build_pr_context.assert_called_once_with("baron", 9)
    fake_plan_pr_workflow.assert_called_once_with(
        {"repo_full_name": "baron", "pr_number": 9}
    )
    fake_review_pull_request.assert_not_called()
    fake_record_text.assert_not_called()
    fake_post_pr_comment.assert_not_called()

def test_trigger_review_agent_runs_execution_when_orchestrator_includes_execution() -> None:
    fake_review_pull_request = Mock(
        return_value=PullRequestReview(summary="AI review text", comments=[])
    )
    fake_execute_changed_files = Mock(return_value={
        "targets": ["rtl/counter.sv"],
        "results": [],
        "passed": True,
    })
    fake_record_text = Mock()
    fake_post_pr_comment = Mock()

    pr_context = {
        "repo_full_name": "baron",
        "pr_number": 9,
        "metadata": {
        "files_changed": ["rtl/counter.sv"],
        },
    }

    fake_build_pr_context = Mock(return_value=pr_context)
    fake_plan_pr_workflow = Mock(return_value={"steps": ["execution", "review"]})

    with patch("agents.review_agent.review_pull_request", fake_review_pull_request):
        with patch("agents.execution_agent.execute_changed_files", fake_execute_changed_files):
            with patch("service.agent_service.build_pr_context", fake_build_pr_context):
                with patch("agents.orchestrator_agent.plan_pr_workflow", fake_plan_pr_workflow):
                    with patch("service.pr_service.record_text", fake_record_text):
                        with patch("service.pr_service.post_pr_comment", fake_post_pr_comment):
                            trigger_review_agent("baron", 9)

    fake_execute_changed_files.assert_called_once_with(["rtl/counter.sv"])
    fake_review_pull_request.assert_called_once_with("baron", 9)
    fake_record_text.assert_any_call("gh:baron#9", "response", "AI review text")
    fake_post_pr_comment.assert_called_once_with("baron", 9, "AI review text")

def test_trigger_review_agent_records_execution_result_when_execution_runs() -> None:
    fake_review_pull_request = Mock(
        return_value=PullRequestReview(summary="AI review text", comments=[])
    )

    execution_result = {
        "targets": ["rtl/counter.sv"],
        "passed": True,
    }
    fake_execute_changed_files = Mock(return_value=execution_result)

    fake_record_text = Mock()
    fake_post_pr_comment = Mock()

    pr_context = {
        "repo_full_name": "baron",
        "pr_number": 9,
        "metadata": {
            "files_changed": ["rtl/counter.sv"],
        },
    }

    fake_build_pr_context = Mock(return_value=pr_context)
    fake_plan_pr_workflow = Mock(return_value={"steps": ["execution", "review"]})

    with patch("agents.review_agent.review_pull_request", fake_review_pull_request):
        with patch("agents.execution_agent.execute_changed_files", fake_execute_changed_files):
            with patch("service.agent_service.build_pr_context", fake_build_pr_context):
                with patch("agents.orchestrator_agent.plan_pr_workflow", fake_plan_pr_workflow):
                    with patch("service.pr_service.record_text", fake_record_text):
                        with patch("service.pr_service.post_pr_comment", fake_post_pr_comment):
                            trigger_review_agent("baron", 9)

    fake_execute_changed_files.assert_called_once_with(["rtl/counter.sv"])

    assert fake_record_text.call_count == 2

    fake_record_text.assert_any_call(
        "gh:baron#9",
        "response",
        f"Execution result: {execution_result}",
    )

    fake_record_text.assert_any_call(
        "gh:baron#9",
        "response",
        "AI review text",
    )

def test_trigger_review_agent_records_orchestrator_decision_reason() -> None:
    fake_review_pull_request = Mock(
        return_value=PullRequestReview(summary="AI review text", comments=[])
    )
    fake_record_text = Mock()
    fake_post_pr_comment = Mock()

    pr_context = {
        "repo_full_name": "baron",
        "pr_number": 9,
        "metadata": {
            "files_changed": ["rtl/counter.sv"],
        },
    }

    fake_build_pr_context = Mock(return_value=pr_context)
    fake_plan_pr_workflow = Mock(
        return_value={
            "steps": ["review"],
            "decision": Mock(reason="Only review is needed."),
        }
    )

    with patch("agents.review_agent.review_pull_request", fake_review_pull_request):
        with patch("service.agent_service.build_pr_context", fake_build_pr_context):
            with patch("agents.orchestrator_agent.plan_pr_workflow", fake_plan_pr_workflow):
                with patch("service.pr_service.record_text", fake_record_text):
                    with patch("service.pr_service.post_pr_comment", fake_post_pr_comment):
                        trigger_review_agent("baron", 9)

    fake_record_text.assert_any_call(
        "gh:baron#9",
        "response",
        "Orchestrator decision: Only review is needed.",
    )

def test_post_pr_inline_comment_posts_inline_comment_to_github() -> None:
    comment_body = "`clear` is synchronous. Add a short comment explaining that."

    fake_response = Mock()
    fake_response.json.return_value = {"id": 456}

    fake_client = Mock()
    fake_client.post.return_value = fake_response

    fake_context = MagicMock()
    fake_context.__enter__.return_value = fake_client
    fake_context.__exit__.return_value = None

    with patch("service.pr_service.httpx.Client", return_value=fake_context):
        result = post_pr_inline_comment(
            "octo/demo",
            7,
            "abc123",
            "examples/hdl/counter.sv",
            14,
            comment_body,
        )

    assert result == {"id": 456}

    fake_client.post.assert_called_once_with(
        "https://api.github.com/repos/octo/demo/pulls/7/comments",
        json={
            "body": comment_body,
            "commit_id": "abc123",
            "path": "examples/hdl/counter.sv",
            "line": 14,
            "side": "RIGHT",
        },
    )

    fake_response.raise_for_status.assert_called_once()

def test_format_inline_comment_body_returns_normal_body_without_replacement() -> None:
    result = format_inline_comment_body(
        "Add a test for `clear`.",
        None,
    )

    assert result == "Add a test for `clear`."


def test_format_inline_comment_body_adds_github_suggestion_block() -> None:
    result = format_inline_comment_body(
        "Make the synchronous behavior explicit.",
        "// clear is sampled on the rising clock edge",
    )

    assert result == """Make the synchronous behavior explicit.

```suggestion
// clear is sampled on the rising clock edge
```"""

def test_get_changed_lines_by_file_returns_added_lines() -> None:
    diff_text = """\
diff --git a/examples/hdl/counter.sv b/examples/hdl/counter.sv
--- a/examples/hdl/counter.sv
+++ b/examples/hdl/counter.sv
@@ -3,13 +3,16 @@ module counter #(
) (
    input  logic             clk,
    input  logic             reset_n,
+    input  logic             clear,
    input  logic             enable,
    output logic [WIDTH-1:0] count
);

    always_ff @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            count <= '0;
+        end else if (clear) begin
+            count <= '0;
        end else if (enable) begin
            count <= count + 1'b1;
        end
    end
"""

    result = get_changed_lines_by_file(diff_text)

    assert result == {
        "examples/hdl/counter.sv": {6, 14, 15},
    }


def test_is_valid_inline_comment_location_requires_a_changed_line() -> None:
    changed_lines = {
        "examples/hdl/counter.sv": {6, 14, 15},
    }

    assert is_valid_inline_comment_location(
        "examples/hdl/counter.sv",
        14,
        changed_lines,
    ) is True

    assert is_valid_inline_comment_location(
        "examples/hdl/counter.sv",
        50,
        changed_lines,
    ) is False

    assert is_valid_inline_comment_location(
        "docs/readme.md",
        14,
        changed_lines,
    ) is False
