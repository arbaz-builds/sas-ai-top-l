import os

from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_pinecone import PineconeVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

from models import client_Embedding

load_dotenv()
PINECONE_INDEX = os.getenv("PINECONE_INDEX")  # PINECONE_API_KEY is read from .env automatically


def RAG(data):
    if data.lower().endswith(".pdf"):
        loader = PyPDFLoader(data)

    elif data.lower().endswith(".docx"):
        loader = Docx2txtLoader(data)

    else:
        print("Unsupported file type")
        return

    documents = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150
    )

    chunks = splitter.split_documents(documents)
    docs = PineconeVectorStore.from_documents(
        chunks,
        embedding=client_Embedding,
        index_name=PINECONE_INDEX,
    )

    return docs


def get_store():
    return PineconeVectorStore(index_name=PINECONE_INDEX, embedding=client_Embedding)
