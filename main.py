import logging
import os
from fastapi import FastAPI

from router.pr_router import router as pr_router


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

app = FastAPI(title="quartz")
app.include_router(pr_router, prefix="/api/v1")

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
