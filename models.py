import config
import os
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_openai import ChatOpenAI


LLM= ChatOpenAI(
          model="openai/gpt-oss-120b",
          api_key=config.open_API,
          base_url = "https://api.groq.com/openai/v1"
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