from memory.config import get_mongo_db

def fetch_pr_metadata(pr_number):
    db = get_mongo_db()
    return db["pr_metadata"].find_one({"pr_number": pr_number})