from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings

from api import Navidia_api






client_Embedding = NVIDIAEmbeddings(
  model="nvidia/llama-nemotron-embed-vl-1b-v2",
  api_key= Navidia_api,
  truncate="NONE",
)
