import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# --- NVIDIA NIM (OpenAI-compatible) -------------------------------------------------
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nvidia/nv-embedqa-e5-v5")
VLM_MODEL = os.getenv("VLM_MODEL", "meta/llama-3.2-11b-vision-instruct")

# --- Storage ------------------------------------------------------------------------
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
IMAGE_DIR = DATA_DIR / "images"
UPLOAD_DIR = DATA_DIR / "uploads"

# --- Chunking / ingestion -----------------------------------------------------------
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "900"))          # characters
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "120"))
MIN_IMAGE_SIDE = int(os.getenv("MIN_IMAGE_SIDE", "120"))  # skip logos / icons smaller than this
MAX_IMAGE_SIDE = int(os.getenv("MAX_IMAGE_SIDE", "1568"))  # downscale big images before the VLM
SCANNED_PAGE_MIN_CHARS = int(os.getenv("SCANNED_PAGE_MIN_CHARS", "40"))
VECTOR_PAGE_DRAWINGS = int(os.getenv("VECTOR_PAGE_DRAWINGS", "25"))  # many vector drawings => chart, render page
PAGE_RENDER_DPI = int(os.getenv("PAGE_RENDER_DPI", "150"))
DESCRIBE_WORKERS = int(os.getenv("DESCRIBE_WORKERS", "4"))

# --- Retrieval / answering ----------------------------------------------------------
TOP_K = int(os.getenv("TOP_K", "6"))
PAGE_EXPANSION = int(os.getenv("PAGE_EXPANSION", "3"))    # extra same-page chunks pulled per hit page
# Llama-3.2-vision NIMs accept ONE image per request, so keep this at 1 unless your model supports more.
MAX_ANSWER_IMAGES = int(os.getenv("MAX_ANSWER_IMAGES", "1"))

# Hosted NVIDIA endpoints limit inline base64 images (~180 KB). Raw JPEG budget before base64 (x4/3).
MAX_IMAGE_BYTES = int(os.getenv("MAX_IMAGE_BYTES", "125000"))
