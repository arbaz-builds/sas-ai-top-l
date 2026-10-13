"""Multimodal RAG pipeline.

Index time : file -> text items + image items -> (image -> VLM transcript/description) -> chunks -> embeddings -> store
Query time : question -> embeddings -> top-k chunks (text AND image chunks share one index)
             -> page expansion (pull same-page text/image neighbours so mixed pages stay together)
             -> VLM answers from the context (+ the best matching original image attached).
"""
import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader, TextLoader  # noqa: F401

from . import config
from .clients import NvidiaClient
from .ingest import chunk_text, load_file
from .store import VectorStore

log = logging.getLogger("mmrag")


def _h(data: bytes | str, n: int = 12) -> str:
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha1(data).hexdigest()[:n]


class MultimodalRAG:
    def __init__(self, client=None, store: VectorStore | None = None):
        self.client = client or NvidiaClient()
        self.store = store or VectorStore(config.DATA_DIR / "index")
        config.IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ ingest
    def ingest(self, path: str | Path, source: str | None = None) -> dict:
        path = Path(path)
        source = source or path.name
        items = load_file(path, source)

        image_items = [it for it in items if it.type == "image"]

        def describe(it):
            try:
                return self.client.describe_image(it.image)
            except Exception as e:  # keep ingesting the rest of the document
                log.warning("image description failed (%s p.%s): %s", source, it.page, e)
                return None

        with ThreadPoolExecutor(max_workers=max(1, config.DESCRIBE_WORKERS)) as ex:
            descriptions = list(ex.map(describe, image_items))
        desc_by_id = {id(it): d for it, d in zip(image_items, descriptions)}

        # re-ingesting the same file replaces the old version (must happen BEFORE new images are written,
        # otherwise identical images would be deleted again)
        self._delete_files_and_records(source)

        records: list[dict] = []
        failed_images = 0
        for it in items:
            if it.type == "text":
                for chunk in chunk_text(it.text):
                    records.append(self._record(source, it.page, "text", chunk))
            else:
                desc = desc_by_id.get(id(it))
                if not desc:
                    failed_images += 1
                    continue
                img_path = config.IMAGE_DIR / f"{_h(source, 8)}_{_h(it.image)}.jpg"
                img_path.write_bytes(it.image)
                for chunk in chunk_text(desc):
                    records.append(self._record(source, it.page, "image", chunk, str(img_path)))

        for n, r in enumerate(records):
            r["id"] = f"{source}#{n}"

        if records:
            texts = [self._embed_text(r) for r in records]
            vectors = self.client.embed(texts, input_type="passage")
            self.store.add(vectors, records)

        return {
            "source": source,
            "text_chunks": sum(r["type"] == "text" for r in records),
            "image_chunks": sum(r["type"] == "image" for r in records),
            "images_found": len(image_items),
            "images_failed": failed_images,
        }

    @staticmethod
    def _record(source, page, type_, text, image_path=None) -> dict:
        return {"source": source, "page": page, "type": type_, "text": text, "image_path": image_path}

    @staticmethod
    def _embed_text(r: dict) -> str:
        where = f"{r['source']}" + (f", page {r['page']}" if r["page"] is not None else "")
        kind = "image content" if r["type"] == "image" else "text"
        return f"[{where} | {kind}]\n{r['text']}"

    # ------------------------------------------------------------------ query
    def query(self, question: str, k: int | None = None) -> dict:
        k = k or config.TOP_K
        qv = self.client.embed([question], input_type="query")[0]
        hits = self.store.search(qv, k)
        if not hits:
            return {"answer": "No documents are indexed yet. Upload a file first.", "sources": []}

        selected: list[tuple[dict, float | None]] = []
        seen: set[str] = set()
        for rec, score in hits:
            if rec["id"] not in seen:
                seen.add(rec["id"])
                selected.append((rec, score))

        # Page expansion: if a page matched, also bring the other modality from that page
        # (e.g. the chart description next to the paragraph that matched).
        by_page: dict[tuple, set] = {}
        for rec, _ in selected:
            if rec["page"] is not None:
                by_page.setdefault((rec["source"], rec["page"]), set()).add(rec["type"])
        for (src, pg), hit_types in by_page.items():
            extra = [r for r in self.store.by_page(src, pg) if r["id"] not in seen]
            extra.sort(key=lambda r: r["type"] in hit_types)   # unseen modality first
            for r in extra[: config.PAGE_EXPANSION]:
                seen.add(r["id"])
                selected.append((r, None))

        blocks, sources = [], []
        for n, (rec, score) in enumerate(selected, start=1):
            where = rec["source"] + (f", page {rec['page']}" if rec["page"] is not None else "")
            label = "image transcript/description" if rec["type"] == "image" else "text"
            blocks.append(f"[{n}] ({where}, {label})\n{rec['text']}")
            sources.append({
                "n": n, "source": rec["source"], "page": rec["page"], "type": rec["type"],
                "score": None if score is None else round(score, 4),
                "snippet": rec["text"][:200],
            })

        images, note = [], ""
        for n, (rec, _) in enumerate(selected, start=1):
            if len(images) >= config.MAX_ANSWER_IMAGES:
                break
            if rec["type"] == "image" and rec.get("image_path") and Path(rec["image_path"]).exists():
                images.append(Path(rec["image_path"]).read_bytes())
                note += f"The attached image is the original image for context block [{n}].\n"

        answer = self.client.answer(question, "\n\n".join(blocks), images, note)
        return {"answer": answer, "sources": sources}

    # ------------------------------------------------------------------ manage
    def _delete_files_and_records(self, source: str) -> int:
        paths = {r["image_path"] for r in self.store.records if r["source"] == source and r.get("image_path")}
        removed = self.store.delete_source(source)
        for p in paths:
            Path(p).unlink(missing_ok=True)
        return removed

    def delete(self, source: str) -> int:
        return self._delete_files_and_records(source)

    def documents(self) -> dict:
        return self.store.sources()
