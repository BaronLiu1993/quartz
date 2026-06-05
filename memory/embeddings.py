import math
from memory.config import get_mongo_db
from app.services.embedding_service import embed_chunk_text, get_gemini_client


def cosine_similarity(left:list[float], right:list[float]) -> float:
    if not left or not right:
        return 0.0
    
    if len(left) != len(right):
        return 0.0

    dot_product = 0.0
    left_length = 0.0
    right_length = 0.0

    for index in range(len(left)):
        dot_product += left[index]* right[index]
        left_length += left[index]* left[index]
        right_length += right[index]*right[index]
    
    if left_length == 0.0 or right_length == 0.0:
        return 0.0
    
    return dot_product/ (math.sqrt(left_length)* math.sqrt(right_length))

def rank_chunks_by_similarity(query_embedding: list[float], chunks: list[dict], limit: int = 5)-> list[dict]:
    scored_chunks = []

    for chunk in chunks:
        chunk_embedding = chunk.get("embedding")

        if not chunk_embedding:
            continue
    
        score = cosine_similarity(query_embedding,chunk_embedding)
        chunk_with_score = dict(chunk)
        chunk_with_score["score"] = score 
        scored_chunks.append(chunk_with_score)

    scored_chunks.sort(key=lambda chunk: chunk["score"], reverse=True)
    
    return scored_chunks[:limit]

def fetch_embedding_chunks()->list[dict]:
    db = get_mongo_db()
    return list(db["chunks"].find({}))

def search_chunks_by_embedding(query_embedding: list[float], limit: int = 5)-> list[dict]:
    chunks = fetch_embedding_chunks()
    return rank_chunks_by_similarity(query_embedding,chunks,limit)

def embed_query_text(query:str)-> list[float]:
    client = get_gemini_client
    return embed_chunk_text(client, query)

def search_relevant_chunks(query:str, limit: int = 5)-> list[dict]:
    query_embedding = embed_query_text(query)
    return search_chunks_by_embedding(query_embedding, limit)
