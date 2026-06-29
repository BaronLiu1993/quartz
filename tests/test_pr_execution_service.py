from pathlib import Path
from unittest.mock import patch

from service.pr_execution_service import execute_pull_request_files


def test_execute_pull_request_files_fetches_writes_and_lints_hdl_targets() -> None:
    seen_file = {}
    github_headers = {"Authorization": "Bearer app-token"}

    def fake_execute_target(local_target: str) -> dict:
        local_path = Path(local_target)
        seen_file["path"] = local_path
        seen_file["text"] = local_path.read_text(encoding="utf-8")
        return {"target": local_target, "passed": True}

    with patch(
        "service.pr_execution_service.fetch_github_file_text",
        return_value="module counter; endmodule\n",
    ) as fake_fetch_file_text:
        with patch(
            "service.pr_execution_service.execute_target",
            side_effect=fake_execute_target,
        ) as fake_execute_target_call:
            result = execute_pull_request_files(
                "octo/demo",
                "commit-123",
                ["rtl/counter.sv", "README.md"],
                github_headers,
            )

    fake_fetch_file_text.assert_called_once_with(
        "octo/demo",
        "rtl/counter.sv",
        "commit-123",
        github_headers,
    )
    fake_execute_target_call.assert_called_once()
    assert seen_file["path"].name == "counter.sv"
    assert seen_file["text"] == "module counter; endmodule\n"
    assert seen_file["path"].exists() is False
    assert result == {
        "targets": ["rtl/counter.sv"],
        "results": [{"target": "rtl/counter.sv", "passed": True}],
        "passed": True,
    }


def test_execute_pull_request_files_skips_download_and_lint_when_no_hdl_targets() -> None:
    with patch("service.pr_execution_service.fetch_github_file_text") as fake_fetch_file_text:
        with patch("service.pr_execution_service.execute_target") as fake_execute_target:
            result = execute_pull_request_files(
                "octo/demo",
                "commit-123",
                ["README.md", "docs/reset.md"],
            )

    fake_fetch_file_text.assert_not_called()
    fake_execute_target.assert_not_called()
    assert result["targets"] == []
    assert result["results"] == []
    assert result["passed"] is None
