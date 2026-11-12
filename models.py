import config
import os
from langchain_nvidia_ai_endpoints import ChatNVIDIA , NVIDIAEmbeddings
from langchain_openai import ChatOpenAI





resision_LLM = ChatOpenAI(
    model="openai/gpt-oss-120b",
    api_key=config.OPEN_API_KEY,
    base_url="https://api.groq.com/openai/v1",
    max_tokens=6000,
    reasoning_effort="medium",
)



 Low_Reasoning_LLM= ChatOpenAI(
    model="openai/gpt-oss-120b",
    api_key=config.OPEN_API_KEY,
    base_url="https://api.groq.com/openai/v1",
    max_tokens=6000,
    reasoning_effort="low",
)

















RAG_LLM = ChatNVIDIA(
    model="meta/llama-3.1-70b-instruct",
    api_key=config.NVIDIA_API_KEY,
)













# NVIDIA Embedding Model
client_Embedding = NVIDIAEmbeddings(
    model="nvidia/llama-nemotron-embed-vl-1b-v2",
    api_key=config.NVIDIA_API_KEY,
    truncate="END",
)



# Vision LLM
vision_LLM = ChatNVIDIA(
    model="meta/llama-3.2-90b-vision-instruct",
    api_key=config.NVIDIA_API_KEY,
)






os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_API_KEY"] = config.LANGSMITH_API_KEY
os.environ["LANGSMITH_PROJECT"] = "NVIDIA-Multimodal-AI"