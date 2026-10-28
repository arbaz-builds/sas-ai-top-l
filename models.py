import config
import os
from langchain_nvidia_ai_endpoints import ChatNVIDIA, NVIDIAEmbeddings

# NVIDIA Embedding Model
client_Embedding = NVIDIAEmbeddings(
    model="nvidia/llama-nemotron-embed-vl-1b-v2",
    api_key=config.NVIDIA_API_KEY,
    truncate="END",
)

# LLM for reasoning / revision
resision_LLM = ChatNVIDIA(
    model="nvidia/nemotron-3.5-super-vl-120b-a12b",
    api_key=config.NVIDIA_API_KEY,
)

# Vision LLM
vision_LLM = ChatNVIDIA(
    model="meta/llama-3.2-90b-vision-instruct",
    api_key=config.NVIDIA_API_KEY,
)






os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_API_KEY"] = config.LANGSMITH_API_KEY
os.environ["LANGSMITH_PROJECT"] = "NVIDIA-Multimodal-AI"