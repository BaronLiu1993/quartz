import sys
from pathlib import Path
from unittest.mock import Mock, patch
sys.path.append(str(Path(__file__).resolve().parents[1]))

from memory.embeddings import cosine_similarity, rank_chunks_by_similarity, fetch_embedding_chunks,search_chunks_by_embedding,embed_query_text, search_relevant_chunks

def test_cosine_similarity_returns_one_for_same_vector()->None:
    result = cosine_similarity([1.0,0.0],[1.0,0.0])
    assert result == 1.0

def test_cosine_similarity_returns_zero_for_different_direction()->None:
    result = cosine_similarity([0.0,1.0], [1.0,0.0])
    assert result == 0.0

def test_cosine_similarity_returns_zero_for_empty_vector()->None:
    result = cosine_similarity([], [1.0,0.0])
    assert result == 0.0

def test_rank_chunks_by_similarity_returns_best_chunks_first()->None:
    chunks = [
        {"chunk_id": "clock", "embedding":[0.0,1.0], "text": "clock info"},
        {"chunk_id": "reset", "embedding":[1.0,0.0], "text": "reset info"}
    ]

    result = rank_chunks_by_similarity([1.0,0.0], chunks)

    assert result[0]["chunk_id"] == "reset"
    assert result[1]["chunk_id"] == "clock"
    assert result[0]["score"] == 1.0

def test_fetch_embedding_chunks_reads_chunks_collection() -> None:
    expected_chunks = [
        {"chunk_id": "reset", "embedding": [1.0,0.0], "text": "reset info"}
    ]

    fake_collection = Mock()
    fake_collection.find.return_value = expected_chunks

    fake_db = {"chunks": fake_collection}

    with patch("memory.embeddings.get_mongo_db", return_value = fake_db):
        result = fetch_embedding_chunks()
    
    assert result == expected_chunks
    fake_collection.find.assert_called_once_with({})


def test_search_chunks_by_embedding_fetches_and_ranks_chunks() -> None:
    chunks = [
        {"chunk_id": "clock", "embedding": [0.0, 1.0], "text": "clock info"},
        {"chunk_id": "reset", "embedding": [1.0, 0.0], "text": "reset info"},
    ]

    with patch("memory.embeddings.fetch_embedding_chunks", return_value=chunks):
        result = search_chunks_by_embedding([1.0, 0.0], limit=1)

    assert len(result) == 1
    assert result[0]["chunk_id"] == "reset"

def test_embed_query_text_uses_gemini_client() -> None:
    fake_client = Mock()

    with patch("memory.embeddings.get_gemini_client", return_value=fake_client):
        with patch("memory.embeddings.embed_chunk_text", return_value=[0.1, 0.2]):
            result = embed_query_text("reset behavior")

    assert result == [0.1, 0.2]

def test_search_relevant_chunks_embeds_query_and_searches() -> None:
    with patch("memory.embeddings.embed_query_text", return_value=[1.0, 0.0]) as fake_embed:
        with patch("memory.embeddings.search_chunks_by_embedding", return_value=[{"chunk_id": "reset"}]) as fake_search:
            result = search_relevant_chunks("reset behavior", limit=3)

    assert result == [{"chunk_id": "reset"}]
    fake_embed.assert_called_once_with("reset behavior")
    fake_search.assert_called_once_with([1.0, 0.0], 3)