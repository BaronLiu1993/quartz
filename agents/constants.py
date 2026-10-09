import os

from dotenv import load_dotenv

load_dotenv()

MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "1200"))
REVIEW_MODEL_NAME = os.getenv("OPENAI_REVIEW_MODEL", "gpt-4.1-mini")
