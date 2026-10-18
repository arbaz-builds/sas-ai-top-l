import hashlib
from pathlib import Path

import pymupdf
import docx

from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_pinecone import PineconeVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

import config
from models import client_Embedding
from rag.image_utils import shrink_jpeg, to_data_url


IMAGE_DIR = Path(config.IMAGE_DIR)
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
IMAGE_MARK = "image-file:"
MAX_IMAGES = 40

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=150,
)


class _Embedder(Embeddings):
    """Embed text and image chunks using the same NVIDIA model."""

    def embed_documents(self, texts):
        inputs = [
            to_data_url(Path(text[len(IMAGE_MARK):]).read_bytes())
            if text.startswith(IMAGE_MARK) else text
            for text in texts
        ]

        vectors = []
        for start in range(0, len(inputs), 16):
            vectors.extend(
                client_Embedding.embed_documents(inputs[start:start + 16])
            )
        return vectors

    def embed_query(self, text):
        return client_Embedding.embed_query(text)


embedding = _Embedder()


def _metadata(source, kind, claim_id=None, page=None, image_path=None):
    metadata = {"source": source, "type": kind}

    if claim_id is not None:
        metadata["claim_id"] = str(claim_id)
    if page is not None:
        metadata["page"] = page
    if image_path:
        metadata["image_path"] = str(image_path)

    return metadata


def _pdf_images(path):
    images, seen = [], set()

    with pymupdf.open(path) as pdf:
        for page_no, page in enumerate(pdf, start=1):
            found = False

            for info in page.get_images(full=True):
                xref = info[0]
                if xref in seen:
                    continue
                seen.add(xref)

                try:
                    pix = pymupdf.Pixmap(pdf, xref)
                    if pix.n - pix.alpha >= 4:
                        pix = pymupdf.Pixmap(pymupdf.csRGB, pix)

                    jpeg = shrink_jpeg(pix.tobytes("png"))
                    if jpeg:
                        images.append((page_no, jpeg))
                        found = True
                except Exception:
                    continue

            text = page.get_text("text").strip()

            try:
                has_charts = len(page.get_drawings()) >= 25
            except Exception:
                has_charts = False

            if (len(text) < 40 and not found) or has_charts:
                jpeg = shrink_jpeg(
                    page.get_pixmap(dpi=150).tobytes("png"),
                    min_side=0,
                )
                if jpeg:
                    images.append((page_no, jpeg))

    return images


def _docx_images(path):
    images = []

    for rel in docx.Document(str(path)).part.rels.values():
        if rel.is_external or "/image" not in rel.reltype:
            continue

        try:
            jpeg = shrink_jpeg(rel.target_part.blob)
            if jpeg:
                images.append((None, jpeg))
        except Exception:
            continue

    return images


def RAG(data, claim_id=None):
    """Index a PDF, DOCX, or image in Pinecone."""

    if not config.PINECONE_INDEX:
        raise ValueError("PINECONE_INDEX is not configured")

    path = Path(data)
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    source = path.name
    ext = path.suffix.lower()
    images = []

    if ext == ".pdf":
        loader = PyPDFLoader(str(path))
        images = _pdf_images(path)

    elif ext == ".docx":
        loader = Docx2txtLoader(str(path))
        images = _docx_images(path)

    elif ext in IMAGE_EXT:
        loader = None
        jpeg = shrink_jpeg(path.read_bytes(), min_side=0)
        images = [(None, jpeg)] if jpeg else []

    else:
        raise ValueError(f"Unsupported file type: {ext}")

    chunks = []

    if loader:
        for doc in loader.load():
            page = doc.metadata.get("page")
            doc.metadata = _metadata(
                source,
                "text",
                claim_id,
                page + 1 if isinstance(page, int) else None,
            )
            chunks.extend(splitter.split_documents([doc]))

    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    owner = hashlib.sha1(
        f"{claim_id}|{source}".encode()
    ).hexdigest()[:8]

    for page, jpeg in images[:MAX_IMAGES]:
        image_path = IMAGE_DIR / (
            f"{owner}_{hashlib.sha1(jpeg).hexdigest()[:12]}.jpg"
        )
        image_path.write_bytes(jpeg)

        chunks.append(
            Document(
                page_content=f"{IMAGE_MARK}{image_path}",
                metadata=_metadata(
                    source, "image", claim_id, page, image_path
                ),
            )
        )

    if not chunks:
        return None

    ids = [
        hashlib.sha1(
            f"{claim_id}|{source}|{chunk.metadata['type']}|"
            f"{chunk.metadata.get('page')}|{i}".encode()
        ).hexdigest()
        for i, chunk in enumerate(chunks)
    ]

    return PineconeVectorStore.from_documents(
        documents=chunks,
        embedding=embedding,
        index_name=config.PINECONE_INDEX,
        ids=ids,
    )


def get_store():
    if not config.PINECONE_INDEX:
        raise ValueError("PINECONE_INDEX is not configured")

    return PineconeVectorStore(
        index_name=config.PINECONE_INDEX,
        embedding=embedding,
    )