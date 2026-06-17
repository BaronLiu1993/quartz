import logging
import os

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from router.pr_router import router as pr_router
from app.routers.embedding_router import router as embedding_router
from app.routers.ingestion_router import router as ingestion_router


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

app = FastAPI(title="hardware Code Assistant")
app.include_router(pr_router, prefix="/api/v1")
app.include_router(embedding_router, prefix = "/api/v1")
app.include_router(ingestion_router, prefix = "/api/v1")

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
