import base64
import os

import httpx
from dotenv import load_dotenv

from agents.execution_agent import is_verilog_target, is_vhdl_target
from app.services.embedding_service import (
    get_gemini_client,
    process_document,
    save_chunks_to_mongodb,
)

load_dotenv()


def get_github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "quartz-ingestion",
    }

    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    return headers


def is_md_file(path: str) -> bool:
    normalized_md = path.lower()
    return normalized_md.endswith(".md")


def is_txt_file(path: str) -> bool:
    normalized_txt = path.lower()
    return normalized_txt.endswith(".txt")


def is_supported_repo_file(path: str) -> bool:
    if is_vhdl_target(path) or is_verilog_target(path) or is_md_file(path) or is_txt_file(path):
        return True

    return False


def get_supported_repo_files(paths: list[str]) -> list[str]:
    supported_files = []

    for path in paths:
        if is_supported_repo_file(path):
            supported_files.append(path)

    return supported_files


def fetch_github_file_text(repo_full_name: str, path: str, ref: str) -> str:
    """Fetch one GitHub file at a branch/tag/SHA and return decoded text."""
    url = f"https://api.github.com/repos/{repo_full_name}/contents/{path}"

    with httpx.Client(timeout=30.0, headers=get_github_headers()) as client:
        response = client.get(url, params={"ref": ref})
        response.raise_for_status()
        data = response.json()

    if data.get("encoding") != "base64":
        raise ValueError("GitHub file content is not base64 encoded.")

    encoded_content = data.get("content") or ""
    encoded_content = encoded_content.replace("\n", "")

    return base64.b64decode(encoded_content).decode("utf-8", errors="replace")


def fetch_github_repo_tree(repo_full_name: str, ref: str) -> list[str]:
    url = f"https://api.github.com/repos/{repo_full_name}/git/trees/{ref}"

    with httpx.Client(timeout=30.0, headers=GITHUB_HEADERS) as client:
        response = client.get(url, params={"recursive": "1"})
        response.raise_for_status()
        data = response.json()

    paths = []

    for item in data.get("tree", []):
        if item.get("type") == "blob":
            paths.append(item.get("path"))

    return paths


def fetch_supported_repo_paths(repo_full_name: str, ref: str) -> list[str]:
    paths = fetch_github_repo_tree(repo_full_name, ref)
    return get_supported_repo_files(paths)


def fetch_supported_repo_file_texts(repo_full_name: str, ref: str) -> list[dict]:
    paths = fetch_supported_repo_paths(repo_full_name, ref)

    files_texts = []

    for path in paths:
        text = fetch_github_file_text(repo_full_name, path, ref)
        type_of_file = infer_file_type(path)
        files_texts.append(
            {
                "path": path,
                "file_type": type_of_file,
                "text": text,
            }
        )

    return files_texts


def infer_file_type(path: str) -> str:
    return path.rsplit(".", 1)[-1].lower()


def process_repo_file_texts(client, file_texts: list[dict]) -> list:
    all_chunks = []

    for file_text in file_texts:
        chunks = process_document(
            client=client,
            source=file_text["path"],
            text=file_text["text"],
            file_type=file_text["file_type"],
            topic="codebase",
        )
        all_chunks.extend(chunks)
    return all_chunks


def ingest_github_codebase(client, repo_full_name: str, ref: str, save_to_db: bool = True) -> dict:
    file_texts = fetch_supported_repo_file_texts(repo_full_name, ref)
    chunks = process_repo_file_texts(client, file_texts)

    if save_to_db:
        save_chunks_to_mongodb(chunks)

    return {
        "repo_full_name": repo_full_name,
        "ref": ref,
        "files_ingested": len(file_texts),
        "chunks_created": len(chunks),
        "chunks": chunks,
        "saved_to_db": save_to_db,
    }


def ingest_github_codebase_with_default_client(repo_full_name: str, ref: str, save_to_db: bool = True) -> dict:
    client = get_gemini_client()
    return ingest_github_codebase(
        client,
        repo_full_name,
        ref,
        save_to_db=save_to_db,
    )

