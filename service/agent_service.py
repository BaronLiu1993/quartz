from memory.config import get_mongo_db

def fetch_pr_metadata(repo_full_name:str ,pr_number:str):
    db = get_mongo_db()
    return db["pr_metadata"].find_one(
        {"repo_full_name": repo_full_name, "pr_number": pr_number}
        )

def fetch_pr_conversations(session_id: str):
    db = get_mongo_db()
    return list(
        db["conversations"].find(
            {"session_id": session_id}
        )
    )

def build_pr_context(repo_full_name:str, pr_number:int):
    session_id = f"gh:{repo_full_name}#{pr_number}"

    metadata = fetch_pr_metadata(repo_full_name,pr_number)
    conversations = fetch_pr_conversations(session_id)

    response_entries = []
    code_entries = []

    for entry in conversations:
        if entry.get("type") == "response":
            response_entries.append(entry)
    
        if entry.get("type") == "code":
            code_entries.append(entry)
    
    return {
        "repo_full_name": repo_full_name,
        "pr_number": pr_number,
        "session_id": session_id,
        "metadata": metadata,
        "code_entries": code_entries,
        "response_entries": response_entries,
    }
    
            

