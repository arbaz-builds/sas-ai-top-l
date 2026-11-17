import config
import os
from langchain_nvidia_ai_endpoints import ChatNVIDIA , NVIDIAEmbeddings
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI




#---- ALLM main LLM Model -----



resision_LLM = ChatOpenAI(
    model="openai/gpt-oss-120b",
    api_key=config.OPEN_API_KEY,
    base_url="https://api.groq.com/openai/v1",
    max_tokens=6000,
    reasoning_effort="medium",
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





#----- langsmith Tracker --------
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_API_KEY"] = config.LANGSMITH_API_KEY
os.environ["LANGSMITH_PROJECT"] = "NVIDIA-Multimodal-AI"


#---- ALL Back UP LLM ----



#Low_Reasoning_LLM= ChatOpenAI(
    #model="openai/gpt-oss-120b",
    #api_key=config.Groq_API_KEY,
    #base_url="https://api.groq.com/openai/v1",
   # max_tokens=6000,
    #reasoning_effort="medium",
#)






# Gemini model
Gemini_Model = ChatGoogleGenerativeAI(
    model="gemini-3.8-flash",
    google_api_key= config.GEMINI_API_KEY
)





















