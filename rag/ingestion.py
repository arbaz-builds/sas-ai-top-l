import hashlib
import logging
import os
from pathlib import Path

import pymupdf
import docx

from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.messages import HumanMessage
from langchain_pinecone import PineconeVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

import config
from models import client_Embedding
from rag import image_store
from rag.common import check_claim_id
from rag.image_utils import shrink_jpeg, to_data_url

logger = logging.getLogger("verriffy.rag")

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
MAX_FILE_BYTES = 15 * 1024 * 1024   # per uploaded file
MAX_PDF_PAGES = 150                 # per PDF
MAX_IMAGES = 40                     # images indexed per document
MAX_OCR_PAGES = 10                  # scanned pages transcribed per document
MIN_TEXT_CHARS = 40                 # a page with less text than this counts as scanned
OCR_ENABLED = os.getenv("OCR_SCANNED_PAGES", "1") == "1"

OCR_NOTE = ("[Text read from a scanned image by an AI model. It may contain mistakes: "
            "check amounts, dates and names against the original image.]")
OCR_PROMPT = ("Transcribe all the text visible in this document image exactly as written. Keep every name, "
              "number, date, amount and table row. Output only the transcription. "
              "If there is no readable text, output nothing.")

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=150,
)


class _Embedder(Embeddings):
    """Embeds text chunks and image chunks with the same NVIDIA model.
    An image chunk's text is the key "image:<id>"; its jpeg bytes are held in memory only for this one
    ingestion, so no file path is ever read from document text."""

    def __init__(self, images=None):
        self.images = images or {}

    def embed_documents(self, texts):
        inputs = [to_data_url(self.images[t]) if t in self.images else t for t in texts]

        vectors = []
        for start in range(0, len(inputs), 16):
            vectors.extend(client_Embedding.embed_documents(inputs[start:start + 16]))
        return vectors

    def embed_query(self, text):
        return client_Embedding.embed_query(text)


def _metadata(doc_id, source, kind, claim_id, page=None, image_key=None, ocr=False):
    metadata = {"doc_id": doc_id, "source": source, "type": kind, "claim_id": claim_id}

    if page is not None:
        metadata["page"] = page
    if image_key:
        metadata["image_key"] = image_key
    if ocr:
        metadata["ocr"] = True

    return metadata


def _pdf_images(path):
    images, seen = [], set()

    with pymupdf.open(path) as pdf:
        if pdf.page_count > MAX_PDF_PAGES:
            raise ValueError(f"PDF has too many pages (max {MAX_PDF_PAGES})")

        for page_no, page in enumerate(pdf, start=1):
            if len(images) >= MAX_IMAGES:
                break
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

            if (len(text) < MIN_TEXT_CHARS and not found) or has_charts:
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
        if len(images) >= MAX_IMAGES:
            break
        if rel.is_external or "/image" not in rel.reltype:
            continue

        try:
            jpeg = shrink_jpeg(rel.target_part.blob)
            if jpeg:
                images.append((None, jpeg))
        except Exception:
            continue

    return images


def _ocr(jpeg):
    """Read the text of a scanned page with the vision model. Never raises: returns "" on any failure."""
    try:
        from models import vision_LLM

        reply = vision_LLM.invoke([HumanMessage(content=[
            {"type": "text", "text": OCR_PROMPT},
            {"type": "image_url", "image_url": {"url": to_data_url(jpeg)}},
        ])])
        return reply.content.strip() if isinstance(reply.content, str) else ""
    except Exception:
        logger.warning("OCR of a scanned page failed", exc_info=True)
        return ""


def RAG(data, claim_id):
    """Index a PDF, DOCX, or image of one claim in Pinecone (one namespace per claim).
    Returns a small summary, or None if the file has nothing to index."""

    claim_id = check_claim_id(claim_id)

    if not config.PINECONE_INDEX:
        raise ValueError("PINECONE_INDEX is not configured")

    path = Path(data)
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    ext = path.suffix.lower()
    if ext not in {".pdf", ".docx"} | IMAGE_EXT:
        raise ValueError(f"Unsupported file type: {ext}")

    raw = path.read_bytes()
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError("File is too large (max 15 MB)")

    doc_id = hashlib.sha256(raw).hexdigest()[:16]   # same content -> same ids: re-uploading never duplicates
    source = path.name
    text_pages, images = [], []                      # text_pages: [(page or None, text)], images: [(page or None, jpeg)]

    if ext == ".pdf":
        images = _pdf_images(path)
        for doc in PyPDFLoader(str(path)).load():
            page = doc.metadata.get("page")
            text_pages.append((page + 1 if isinstance(page, int) else None, doc.page_content))

    elif ext == ".docx":
        images = _docx_images(path)
        for doc in Docx2txtLoader(str(path)).load():
            text_pages.append((None, doc.page_content))

    else:
        jpeg = shrink_jpeg(raw, min_side=0)
        images = [(None, jpeg)] if jpeg else []

    images = images[:MAX_IMAGES]
    chunks = []

    for page, text in text_pages:
        for piece in splitter.split_text(text):
            if piece.strip():
                chunks.append(Document(
                    page_content=piece,
                    metadata=_metadata(doc_id, source, "text", claim_id, page),
                ))

    # scanned pages (little or no text layer): read their text from the image so amounts and dates are searchable
    text_len = {}
    for page, text in text_pages:
        text_len[page] = text_len.get(page, 0) + len(text.strip())

    ocr_pages = 0
    if OCR_ENABLED:
        for page, jpeg in images:
            if ocr_pages >= MAX_OCR_PAGES:
                break
            if text_len.get(page, 0) >= MIN_TEXT_CHARS:
                continue
            text = _ocr(jpeg)
            if not text:
                continue
            ocr_pages += 1
            for piece in splitter.split_text(text):
                chunks.append(Document(
                    page_content=f"{OCR_NOTE}\n{piece}",
                    metadata=_metadata(doc_id, source, "text", claim_id, page, ocr=True),
                ))

    stored_images, image_inputs = {}, {}
    for n, (page, jpeg) in enumerate(images):
        key = f"{doc_id}-{n}"
        text = f"image:{key}"
        stored_images[key] = jpeg
        image_inputs[text] = jpeg
        chunks.append(Document(
            page_content=text,
            metadata=_metadata(doc_id, source, "image", claim_id, page, image_key=key),
        ))

    if not chunks:
        return None

    counts, ids = {}, []
    for chunk in chunks:
        kind = chunk.metadata["type"] + ("-ocr" if chunk.metadata.get("ocr") else "")
        counts[kind] = counts.get(kind, 0) + 1
        ids.append(f"{doc_id}-{kind}-{counts[kind]}")

    # images first: if saving the vectors fails afterwards, nothing points to a missing image
    image_store.save_images(claim_id, stored_images)

    store = PineconeVectorStore(
        index_name=config.PINECONE_INDEX,
        embedding=_Embedder(image_inputs),
        namespace=claim_id,
    )
    store.add_documents(chunks, ids=ids)

    return {
        "doc_id": doc_id,
        "claim_id": claim_id,
        "text_chunks": sum(1 for c in chunks if c.metadata["type"] == "text"),
        "image_chunks": len(stored_images),
        "ocr_pages": ocr_pages,
    }


def get_store(claim_id):
    """Search handle for ONE claim: the namespace is the claim, so no other claim's documents can be reached."""
    claim_id = check_claim_id(claim_id)

    if not config.PINECONE_INDEX:
        raise ValueError("PINECONE_INDEX is not configured")

    return PineconeVectorStore(
        index_name=config.PINECONE_INDEX,
        embedding=_Embedder(),
        namespace=claim_id,
    )