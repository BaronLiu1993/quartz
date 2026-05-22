from fastapi import FastAPI
from app.routers.embedding_router import router as embedding_router

app= FastAPI(
    title="Hardware Assistant API",
    description="API for chunking hardware documents and creating embeddings.",
    version="1.0.0"
)

@app.get("/")
def root():
    return {
        "message": "Hardware Assistant API is running"
    }


app.include_router(embedding_router)