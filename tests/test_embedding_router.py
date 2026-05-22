import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from unittest.mock import patch
from app.services.embedding_service import DocumentChunk
from app.routers.embedding_router import normalize_file_type
from fastapi.testclient import TestClient
from app.main import app


def test_normalize_file_type() -> None:
    assert normalize_file_type("sv") == "sv"
    assert normalize_file_type(".SV") == "sv"
    assert normalize_file_type("baron.Sv") == "sv"

client = TestClient(app)

def test_root_route() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Hardware Assistant API is running"}

def test_process_document_rejects_unsupported_file()-> None:
    request_body = {
        "source": "bad_file",
        "text": "hello world",
        "file_type": "exe",
        "topic": "",
        "url": "",
        "section_title": "",
        "save_to_db": False,
        "return_embeddings": False,
    }

    response = client.post("/embeddings/process", json=request_body)

    assert response.status_code == 400


@patch("app.routers.embedding_router.process_document")
@patch("app.routers.embedding_router.get_gemini_client")
def test_process_document_success(
    mock_get_gemini_client,
    mock_process_document,
) -> None:
    fake_chunk = DocumentChunk(
        chunk_id="half_adder_chunk_0",
        source="half_adder",
        url="",
        topic="digital logic",
        file_type="sv",
        section_title="module half_adder",
        text="module half_adder(input a, input b, output sum, output carry); endmodule",
        embedding=[0.1, 0.2, 0.3],
    )

    mock_get_gemini_client.return_value = object()
    mock_process_document.return_value = [fake_chunk]

    request_body = {
        "source": "half_adder",
        "text": "module half_adder(input a, input b, output sum, output carry); endmodule",
        "file_type": "sv",
        "topic": "digital logic",
        "url": "",
        "section_title": "",
        "save_to_db": False,
        "return_embeddings": False,
    }

    response = client.post("/embeddings/process", json=request_body)

    assert response.status_code == 200

    body = response.json()
    assert body["message"] == "Document processed successfully"
    assert body["chunk_count"] == 1
    assert body["saved_to_db"] is False
    assert len(body["chunks"]) == 1

    first_chunk = body["chunks"][0]
    assert first_chunk["chunk_id"] == "half_adder_chunk_0"
    assert first_chunk["embedding_length"] == 3
    assert "embedding" not in first_chunk
