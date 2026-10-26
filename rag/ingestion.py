import uuid
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_pinecone import PineconeVectorStore

from models import client_Embedding, vision_LLM
import config

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000, chunk_overlap=150
)


def load_file(file_path):
    path = Path(file_path)
    if path.suffix.lower() == ".pdf":
        return PyPDFLoader(str(path)).load()
    if path.suffix.lower() in IMAGE_EXT:
        return [Document(page_content=f"IMAGE_PATH:{path.resolve()}")]
    return TextLoader(str(path), encoding="utf-8").load()


def ingest(file_path, user_id, source_name=None):
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(file_path)

    user_id = str(user_id).strip()
    if not user_id:
        raise ValueError("user_id required")

    doc_id = str(uuid.uuid4())
    docs = load_file(path)
    chunks = []

    for doc in docs:
        if doc.page_content.startswith("IMAGE_PATH:"):
            url = image_data(str(path))
            from langchain_core.messages import HumanMessage
            msg = HumanMessage(content=[
                {"type": "text", "text": "Describe this image and transcribe visible text."},
                {"type": "image_url", "image_url": {"url": url}},
            ])
            text = vision_LLM.invoke([msg]).content
            doc.page_content = f"Image description: {text}"

        chunks.extend(splitter.split_documents([doc]))

    for i, chunk in enumerate(chunks):
        chunk.metadata.update({
            "user_id": user_id,
            "doc_id": doc_id,
            "chunk_id": str(uuid.uuid4()),
            "source": source_name or path.name,
        })

    store = PineconeVectorStore(
        index_name=config.PINECONE_INDEX,
        embedding=client_Embedding,
        namespace=user_id,
    )
    store.add_documents(chunks)

    return {"doc_id": doc_id, "chunks": len(chunks)}

    return store.similarity_search(query, k=k)