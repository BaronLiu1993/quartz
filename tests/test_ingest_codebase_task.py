from unittest.mock import patch

from async_queue.ingest_codebase import ingest_github_codebase_task


def test_ingest_github_codebase_task_calls_ingestion_service() -> None:
    expected_result = {
        "repo_full_name": "octo/demo",
        "ref": "main",
        "files_ingested": 2,
    }

    with patch(
        "async_queue.ingest_codebase.ingest_github_codebase_with_default_client",
        return_value=expected_result,
    ) as fake_ingest:
        result = ingest_github_codebase_task.run(
            "octo/demo",
            "main",
            save_to_db=False,
        )

    fake_ingest.assert_called_once_with(
        "octo/demo",
        "main",
        save_to_db=False,
    )
    assert result == expected_result