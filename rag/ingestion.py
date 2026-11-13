import re
import uuid
from pathlib import Path
from rag.image_utils import image_data

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_pinecone import PineconeVectorStore

from models import client_Embedding, vision_LLM
import config

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}

# Fix 1: bada chunk, overlap 0 (ek page = ek chunk)
splitter = RecursiveCharacterTextSplitter(
    chunk_size=2500, chunk_overlap=0
)

# Fix 2: header/footer ki lines jo index nahi karni
HEADER = [
    r"^N$",
    r"^Northstar Mutual Auto Insurance Co\.$",
    r"^Auto Claims Center$",
    r"^Home Office:.*",
    r"^NAIC No\..*",
    r"^AUTO PHYSICAL DAMAGE CLAIM$",
    r"^Claims hotline.*",
    r"^claims@.*",
    r"^Form AC-101.*",
]


def clean(text):
    lines = [l.strip() for l in text.splitlines()]
    return "\n".join(
        l for l in lines
        if l and not any(re.match(p, l) for p in HEADER)
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
    is_pdf = path.suffix.lower() == ".pdf"
    chunks = []

    for doc in docs:
        if doc.page_content.startswith("IMAGE_PATH:"):
            url = image_data(str(path))
            msg = HumanMessage(content=[
                {"type": "text", "text": "Describe this image and transcribe visible text."},
                {"type": "image_url", "image_url": {"url": url}},
            ])
            text = vision_LLM.invoke([msg]).content
            doc.page_content = f"Image description: {text}"
        elif is_pdf:
            doc.page_content = clean(doc.page_content)

        parts = splitter.split_documents([doc])

        # Fix 3: har chunk ke shuru mein "Page n:" (PyPDFLoader page 0 se ginta hai)
        if is_pdf:
            for p in parts:
                page_no = p.metadata.get("page", 0) + 1
                p.page_content = f"Page {page_no}:\n" + p.page_content

        chunks.extend(parts)

    for chunk in chunks:
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


def retrieve(query, user_id, k=4):
    store = PineconeVectorStore(
        index_name=config.PINECONE_INDEX,
        embedding=client_Embedding,
        namespace=str(user_id),
    )

    return store.similarity_search(query, k=k)