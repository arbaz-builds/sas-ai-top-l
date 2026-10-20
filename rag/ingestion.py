import uuid
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_pinecone import PineconeVectorStore

from models import client_Embedding
import config


def load_file(file_path):
    path = Path(file_path)
    if path.suffix.lower() == ".pdf":
        return PyPDFLoader(str(path)).load()
    return TextLoader(str(path), encoding="utf-8").load()


def ingest(file_path, user_id):
    user_id = str(user_id).strip()
    if not user_id:
        raise ValueError("user_id is required")

    docs = load_file(file_path)
    doc_id = str(uuid.uuid4())

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
    )
    chunks = splitter.split_documents(docs)

    for chunk in chunks:
        chunk.metadata.update({
            "user_id": user_id,
            "doc_id": doc_id,
            "chunk_id": str(uuid.uuid4()),
            "source": Path(file_path).name,
        })

    store = PineconeVectorStore(
        index_name=config.PINECONE_INDEX,
        embedding=client_Embedding,
        namespace=user_id,
    )
    store.add_documents(chunks)

    return {"user_id": user_id, "doc_id": doc_id,
            "chunks": len(chunks)}


def retrieve(query, user_id, k=4):
    store = PineconeVectorStore(
        index_name=config.PINECONE_INDEX,
        embedding=client_Embedding,
        namespace=str(user_id),
    )
    return store.similarity_search(query, k=k)