import os

from dotenv import load_dotenv
from langchain_nvidia_ai_endpoints import ChatNVIDIA, NVIDIAEmbeddings

load_dotenv()  # keys live in .env (NVIDIA_API_KEY), never in the code

client_Embedding = NVIDIAEmbeddings(
    model="nvidia/llama-nemotron-embed-vl-1b-v2",
    api_key=os.getenv("NVIDIA_API_KEY"),
    truncate="END",
)


def LLM_bind_Tool():
    # imported here, not at the top, to avoid a circular import (tool -> mmrag.rag -> LLM)
    from tool import tools

    llm = ChatNVIDIA(
        model=os.getenv("CHAT_MODEL", "meta/llama-3.3-70b-instruct"),
        api_key=os.getenv("NVIDIA_API_KEY"),
    )
    return llm.bind_tools(tools)
