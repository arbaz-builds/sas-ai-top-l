import os
from dotenv import load_dotenv

load_dotenv()

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX")
DATABASE_URL = os.getenv("DATABASE_URL")
IMAGE_DIR = os.getenv("IMAGE_DIR", "images")
LANGSMITH_API_KEY= os.getenv("langsmith")


