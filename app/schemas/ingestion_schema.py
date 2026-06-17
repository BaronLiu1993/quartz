from pydantic import BaseModel

class GitHubCodeBaseIngestionRequest(BaseModel):
    repo_full_name: str
    ref:str = "main"
    save_to_db: bool = True
