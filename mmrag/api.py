import shutil
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from . import config
from .ingest import SUPPORTED
from .rag import MultimodalRAG

app = FastAPI(title="Multimodal RAG", version="0.1.0")
_rag: MultimodalRAG | None = None


def get_rag() -> MultimodalRAG:
    global _rag
    if _rag is None:                    # lazy so /health works even before the API key is set
        try:
            _rag = MultimodalRAG()
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))
    return _rag


class QueryRequest(BaseModel):
    question: str = Field(min_length=1)
    k: int | None = Field(default=None, ge=1, le=30)


@app.get("/health")
def health():
    return {"status": "ok", "supported_types": sorted(SUPPORTED)}


@app.post("/ingest")
def ingest(files: list[UploadFile] = File(...)):
    rag = get_rag()
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for f in files:
        name = Path(f.filename or "upload").name
        dest = config.UPLOAD_DIR / name
        with dest.open("wb") as out:
            shutil.copyfileobj(f.file, out)
        try:
            results.append(rag.ingest(dest, source=name))
        except ValueError as e:
            results.append({"source": name, "error": str(e)})
        except Exception as e:
            results.append({"source": name, "error": f"ingest failed: {e}"})
    return {"results": results}


@app.post("/query")
def query(req: QueryRequest):
    return get_rag().query(req.question, req.k)


@app.get("/documents")
def documents():
    return get_rag().documents()


@app.delete("/documents/{name}")
def delete_document(name: str):
    removed = get_rag().delete(name)
    if not removed:
        raise HTTPException(status_code=404, detail=f"'{name}' not found")
    return {"deleted": name, "chunks_removed": removed}
