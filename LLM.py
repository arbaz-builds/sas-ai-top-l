import os

from dotenv import load_dotenv
from langchain_nvidia_ai_endpoints import ChatNVIDIA, NVIDIAEmbeddings

load_dotenv()  # keys live in .env (NVIDIA_API_KEY), never in the code

client_Embedding = NVIDIAEmbeddings(
    model="nvidia/llama-nemotron-embed-vl-1b-v2",
    api_key=os.getenv("NVIDIA_API_KEY"),
    truncate="END",
)

resision_LLM = NVIDIAEmbeddings(
    model="",
    api_key=os.getenv("NVIDIA_API_KEY"),
)


vision_LLM = NVIDIAEmbeddings(
    model="",
    api_key=os.getenv("NVIDIA_API_KEY"),
)




