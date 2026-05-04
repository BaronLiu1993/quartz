import os

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_WEBHOOK_SECRET = os.environ["GITHUB_WEBHOOK_SECRET"]
GITHUB_API = "https://api.github.com"
LOCAL_USER_ID = os.environ.get("LOCAL_USER_ID", "local")
HTTP_TIMEOUT = 30.0
DIFF_BYTE_LIMIT = 1_000_000
STAGE = "pr_ingest"
GITHUB_HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "quartz-webhook",
}
