import os

from dotenv import load_dotenv

load_dotenv()

# Chat memory: Postgres if DATABASE_URL is set, otherwise memory in RAM (local development only)
DATABASE_URL = os.getenv("DATABASE_URL", "")

REQUIRED = ["NVIDIA_API_KEY", "PINECONE_API_KEY", "PINECONE_INDEX"]


def validate():
    missing = [k for k in REQUIRED if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"Missing environment variables: {', '.join(missing)}. Add them to .env (see .env.example).")
