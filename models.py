import config
from langchain_nvidia_ai_endpoints import ChatNVIDIA, NVIDIAEmbeddings

# NVIDIA Embedding Model
client_Embedding = NVIDIAEmbeddings(
    model="nvidia/llama-nemotron-embed-vl-1b-v2",
    api_key=config.NVIDIA_API_KEY,
    truncate="END",
)

# LLM for reasoning / revision
resision_LLM = ChatNVIDIA(
    model="z-ai/glm-5.3",
    api_key=config.NVIDIA_API_KEY,
)

# Vision LLM
vision_LLM = ChatNVIDIA(
    model="meta/llama-3.2-90b-vision-instruct",
    api_key=config.NVIDIA_API_KEY,
)