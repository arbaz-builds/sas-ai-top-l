import os
import config 
from langchain_nvidia_ai_endpoints import ChatNVIDIA, NVIDIAEmbeddings



client_Embedding = NVIDIAEmbeddings(
    model="nvidia/llama-nemotron-embed-vl-1b-v2",
    api_key=config.NVIDIA_API_KEY,
    truncate="END",
)

resision_LLM = ChatNVIDIA(
    model="z-ai/glm-5.3",
    api_key=config.NVIDIA_API_KEY,
)


vision_LLM =ChatNVIDIA(
    model="meta/llama-3.2-90b-vision-instruct",
    api_key=config.NVIDIA_API_KEY,
)




