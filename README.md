# Multimodal RAG

A RAG system that understands **text documents**, **image documents** and **mixed documents** (text + images in the same file).

## How it works

```
                    ┌────────── text ──────────► chunks ─────────────┐
 PDF / DOCX / TXT / │                                                ├─► embeddings ─► vector store
 PNG / JPG ...  ──► loader                                           │
                    └─► images / scanned pages / charts              │
                          └─► Vision-Language Model (transcript + description) ─┘

 question ─► embed ─► top-k (text + image chunks together)
          ─► page expansion (same-page text + image neighbours)
          ─► VLM answers from the context (+ best original image attached) ─► answer + sources
```

* **Text docs** – chunked and embedded.
* **Image docs** – the VLM transcribes all visible text (OCR) and describes charts / diagrams / photos; that
  description is embedded, and the original image is stored so it can be shown to the VLM again at answer time.
* **Mixed docs** – PDF pages are split into text + embedded images; scanned pages and chart-heavy vector pages
  are rendered to an image. Every chunk keeps `(source, page)`, and at query time *page expansion* pulls the
  other modality from the same page, so a question about a paragraph also sees the chart beside it (and vice versa).
* DOCX: text, tables and embedded images are indexed (page numbers are not available in DOCX).

Supported: `.pdf .docx .txt .md .csv .json .log .png .jpg .jpeg .webp .bmp .gif .tif .tiff`

## Run

```bash
pip install -r requirements.txt
cp .env.example .env        # add NVIDIA_API_KEY (https://build.nvidia.com)
uvicorn main:app --reload
```

| Endpoint | Purpose |
|---|---|
| `POST /ingest` | multipart upload, field `files` (one or many) |
| `POST /query` | `{"question": "...", "k": 6}` → answer + sources (file, page, type, score) |
| `GET /documents` | indexed files with text/image chunk counts |
| `DELETE /documents/{name}` | remove a file from the index |
| `GET /health` | status |

```bash
curl -F "files=@report.pdf" -F "files=@chart.png" localhost:8000/ingest
curl -X POST localhost:8000/query -H "content-type: application/json" \
     -d '{"question": "What does the revenue chart show for Q3?"}'
```

## Config (env vars, see `mmrag/config.py`)

* `EMBED_MODEL` (default `nvidia/nv-embedqa-e5-v5`), `VLM_MODEL` (default `meta/llama-3.2-11b-vision-instruct`)
* `MAX_ANSWER_IMAGES` – Llama-3.2-vision NIMs accept **one** image per request, so the default is `1`.
* `MAX_IMAGE_BYTES` – hosted NVIDIA endpoints limit inline base64 images (~180 KB); images are auto-compressed to fit.
  Raise it if you self-host the NIM.
* `VECTOR_PAGE_DRAWINGS` – pages with this many vector shapes are also rendered as an image (catches vector charts and tables).

## Tests

```bash
pytest -q     # offline: uses a fake client, no API key needed
```

## Notes / limits

* The vector store is a small numpy + JSON store (`data/index`) – fine up to tens of thousands of chunks.
  Swap `VectorStore` for Pinecone / Qdrant if you need more.
* Image understanding quality depends on the VLM. For scanned documents with dense small print, use a bigger
  `VLM_MODEL` (e.g. `meta/llama-3.2-90b-vision-instruct`) and raise `MAX_IMAGE_BYTES` when self-hosting.
