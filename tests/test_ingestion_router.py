from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

def test_queue_github_codebase_ingestion_queues_task() -> None:
    fake_task_result = Mock()
    fake_task_result.id = "task-123"

    with patch("app.routers.ingestion_router.ingest_github_codebase_task") as fake_task:
        fake_task.delay.return_value = fake_task_result

        response = client.post(
            "/api/v1/ingestion/github-codebase",
            json={
                "repo_full_name": "octo/demo",
                "ref": "main",
                "save_to_db": False,
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "status": "queued",
        "task_id": "task-123",
        "repo_full_name": "octo/demo",
        "ref": "main",
        "save_to_db": False,
    }

    fake_task.delay.assert_called_once_with(
        "octo/demo",
        "main",
        save_to_db=False,
    )

def test_queue_github_codebase_ingestion_uses_defaults() -> None:
    fake_task_result = Mock()
    fake_task_result.id = "task-456"

    with patch("app.routers.ingestion_router.ingest_github_codebase_task") as fake_task:
        fake_task.delay.return_value = fake_task_result

        response = client.post(
            "/api/v1/ingestion/github-codebase",
            json={
                "repo_full_name": "octo/demo",
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "status": "queued",
        "task_id": "task-456",
        "repo_full_name": "octo/demo",
        "ref": "main",
        "save_to_db": True,
    }

    fake_task.delay.assert_called_once_with(
        "octo/demo",
        "main",
        save_to_db=True,
    )

def test_queue_github_codebase_ingestion_requires_repo_full_name() -> None:
    response = client.post(
        "/api/v1/ingestion/github-codebase",
        json={
            "ref": "main",
            "save_to_db": True,
        },
    )

    assert response.status_code == 422