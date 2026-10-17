import hashlib
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_pinecone import PineconeVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

from models import client_Embedding
from rag.image_utils import shrink_jpeg, to_data_url

load_dotenv()

PINECONE_INDEX = os.getenv("PINECONE_INDEX")  # PINECONE_API_KEY is read from .env automatically
IMAGE_DIR = Path(os.getenv("IMAGE_DIR", "data/images"))  # original images are kept here (later: S3)
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
IMAGE_MARK = "image-file:"    # an image chunk's text is "image-file:<path>"
MAX_IMAGES_PER_DOC = 40
SCANNED_PAGE_MIN_CHARS = 40   # page with less text and no image = scanned page -> render it
VECTOR_PAGE_DRAWINGS = 25     # page with this many vector shapes = chart -> render it


class _Embedder(Embeddings):
    """Text chunks are embedded as text. An image chunk is embedded as the IMAGE itself
    (llama-nemotron-embed-vl reads images), so no vision model is needed to index images."""

    def embed_documents(self, texts):
        inputs = [to_data_url(Path(t[len(IMAGE_MARK):]).read_bytes()) if t.startswith(IMAGE_MARK) else t for t in texts]
        vectors = []
        for i in range(0, len(inputs), 16):          # small batches: images are big
            vectors += client_Embedding.embed_documents(inputs[i:i + 16])
        return vectors

    def embed_query(self, text):
        return client_Embedding.embed_query(text)


def _pdf_images(path):
    """[(page_number, jpeg_bytes)]: embedded images, plus scanned / chart-heavy pages rendered as an image."""
    import pymupdf

    out, seen = [], set()
    doc = pymupdf.open(path)
    try:
        for pno, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            found = 0
            for info in page.get_images(full=True):
                xref = info[0]
                if xref in seen:
                    continue
                seen.add(xref)
                try:
                    pix = pymupdf.Pixmap(doc, xref)
                    if pix.n - pix.alpha >= 4:  # CMYK -> RGB
                        pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
                    jpeg = shrink_jpeg(pix.tobytes("png"))
                except Exception:
                    jpeg = None
                if jpeg:
                    found += 1
                    out.append((pno, jpeg))
            try:
                drawings = len(page.get_drawings())
            except Exception:
                drawings = 0
            if (len(text) < SCANNED_PAGE_MIN_CHARS and found == 0) or drawings >= VECTOR_PAGE_DRAWINGS:
                jpeg = shrink_jpeg(page.get_pixmap(dpi=150).tobytes("png"), min_side=0)
                if jpeg:
                    out.append((pno, jpeg))
    finally:
        doc.close()
    return out


def _docx_images(path):
    import docx

    out = []
    for rel in docx.Document(str(path)).part.rels.values():
        if not rel.is_external and "/image" in rel.reltype:
            jpeg = shrink_jpeg(rel.target_part.blob)
            if jpeg:
                out.append((None, jpeg))
    return out


def _meta(source, page, kind, claim_id, image_path=None):
    # Pinecone metadata cannot hold None, so empty values are simply left out
    m = {"source": source, "type": kind}
    if page is not None:
        m["page"] = page
    if claim_id:
        m["claim_id"] = str(claim_id)
    if image_path:
        m["image_path"] = image_path
    return m


def RAG(data, claim_id=None):
    """Index a file for one claim: text chunks, and every image (original saved, image embedded directly)."""
    path = Path(data)
    ext = path.suffix.lower()
    source = path.name

    if ext == ".pdf":
        loader, images = PyPDFLoader(str(path)), _pdf_images(path)
    elif ext == ".docx":
        loader, images = Docx2txtLoader(str(path)), _docx_images(path)
    elif ext in IMAGE_EXT:
        jpeg = shrink_jpeg(path.read_bytes(), min_side=0)
        loader, images = None, ([(None, jpeg)] if jpeg else [])
    else:
        print("Unsupported file type")
        return

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150
    )

    chunks = []
    for doc in (loader.load() if loader else []):
        page = doc.metadata.get("page")                    # PyPDF pages start at 0, people count from 1
        doc.metadata = _meta(source, page + 1 if isinstance(page, int) else None, "text", claim_id)
        chunks.extend(splitter.split_documents([doc]))

    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    owner = hashlib.sha1(f"{claim_id}|{source}".encode()).hexdigest()[:8]
    for page, jpeg in images[:MAX_IMAGES_PER_DOC]:
        img_path = IMAGE_DIR / f"{owner}_{hashlib.sha1(jpeg).hexdigest()[:12]}.jpg"
        img_path.write_bytes(jpeg)
        chunks.append(Document(page_content=IMAGE_MARK + str(img_path),
                               metadata=_meta(source, page, "image", claim_id, str(img_path))))

    if not chunks:
        return

    # same file + same claim -> same ids, so indexing a file twice overwrites instead of duplicating
    ids = [hashlib.sha1(f"{claim_id}|{source}|{c.metadata['type']}|{c.metadata.get('page')}|{n}".encode()).hexdigest()
           for n, c in enumerate(chunks)]
    return PineconeVectorStore.from_documents(chunks, embedding=_Embedder(), index_name=PINECONE_INDEX, ids=ids)


def get_store():
    return PineconeVectorStore(index_name=PINECONE_INDEX, embedding=client_Embedding)
