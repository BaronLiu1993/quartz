import base64
import httpx
from agents.execution_agent import is_verilog_target, is_vhdl_target
from unittest.mock import Mock, patch, MagicMock

def is_md_file(path:str):
    normalized_md = path.lower()
    return normalized_md.endswith(".md")

def is_txt_file(path:str):
    normalized_txt = path.lower()
    return normalized_txt.endswith(".txt")

def is_supported_repo_file(path:str)->bool:
    if is_vhdl_target(path) or is_verilog_target(path) or is_md_file(path) or is_txt_file(path):
        return True
    
    return False 

def is_supported_repo_files(paths: list[str])-> list[str]:
    support_files = []

    for path in paths:
        if is_supported_repo_file(path):
            support_files.append(path)

    return support_files

def fetch_github_file_text(repo_full_name: str, path: str, ref: str) -> str:
    """Fetch one GitHub file at a branch/tag/SHA and return decoded text."""
    url = f"https://api.github.com/repos/{repo_full_name}/contents/{path}"

    with httpx.Client(timeout=30.0) as client:
        response = client.get(url,params={"ref":ref})
        response.raise_for_status()
        data = response.json()
    
    if data.get("encoding") != "base64":
        raise ValueError("GitHub file content is not base64 encoded.")
    
    encoded_content = data.get("content") or ""
    encoded_content = encoded_content.replace("\n","")

    return base64.b64decode(encoded_content).decode("utf-8", errors="replace")

def fetch_github_repo_tree(repo_full_name: str, ref: str) -> list[str]:
    url = f"https://api.github.com/repos/{repo_full_name}/git/trees/{ref}"

    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, params={"recursive": "1"})
        response.raise_for_status()
        data = response.json()

    paths = []

    for item in data.get("tree", []):
        if item.get("type") == "blob":
            paths.append(item.get("path"))

    return paths

def fetch_supported_repo_paths(repo_full_name: str, ref: str):
    paths = fetch_github_repo_tree(repo_full_name, ref)
    return is_supported_repo_files(paths)

    





