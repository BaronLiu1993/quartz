from .config import app
from ingestion.codebase_ingestion import ingest_github_codebase_with_default_client


@app.task(name="ingestion.ingest_github_codebase")
def ingest_github_codebase_task(repo_full_name: str, ref: str, save_to_db: bool = True):
    return ingest_github_codebase_with_default_client(
        repo_full_name,
        ref,
        save_to_db=save_to_db,
    )
