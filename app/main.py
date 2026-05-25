import logging
import os

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from app.routers.embedding_router import router as embedding_router
from router.pr_router import router as pr_router


app= FastAPI(
    title="Hardware Assistant API",
    description="API for chunking hardware documents and creating embeddings.",
    version="1.0.0"
)


app.include_router(pr_router, prefix = "/api/v1" )
app.include_router(embedding_router, prefix= "/api/v1")