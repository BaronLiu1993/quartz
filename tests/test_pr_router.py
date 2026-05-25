import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_github_webhook_rejects_missing_signature() -> None:
    response = client.post("/api/v1/webhooks/github",
        headers={"X-GitHub-Event": "pull_request","X-GitHub-Delivery": "test-delivery-1",},
        json={"action": "opened"},
)
    
    assert response.status_code == 401
    assert response.json() == {"detail": "invalid signature"}