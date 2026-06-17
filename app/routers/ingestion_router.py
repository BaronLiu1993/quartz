from fastapi import APIRouter

from app.schemas.ingestion_schema import GitHubCodeBaseIngestionRequest
from async_queue.ingest_codebase import ingest_github_codebase_task

router = APIRouter(
    prefix = "/ingestion",
    tags =["ingestion"],
)

@router.post("/github-codebase")
def queue_github_codebase_ingestion(request: GitHubCodeBaseIngestionRequest):
    task = ingest_github_codebase_task.delay(
        request.repo_full_name,
        request.ref,
        save_to_db = request.save_to_db,
    )

    return {
        "status":"queued",
        "task_id": task.id,
        "repo_full_name": request.repo_full_name,
        "ref": request.ref,
        "save_to_db":request.save_to_db,
    }

