"""Tiny persistent vector store (cosine similarity, numpy). Swap for Pinecone/Qdrant if you outgrow it."""
import json
import threading
from pathlib import Path

import numpy as np


class VectorStore:
    def __init__(self, directory: Path):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self._vec_path = self.dir / "vectors.npy"
        self._meta_path = self.dir / "records.json"
        self._lock = threading.Lock()
        self.vectors = np.zeros((0, 0), dtype=np.float32)
        self.records: list[dict] = []
        self._load()

    # ---- persistence -------------------------------------------------------------
    def _load(self):
        if self._vec_path.exists() and self._meta_path.exists():
            self.vectors = np.load(self._vec_path)
            self.records = json.loads(self._meta_path.read_text(encoding="utf-8"))

    def _save(self):
        np.save(self._vec_path, self.vectors)
        self._meta_path.write_text(json.dumps(self.records, ensure_ascii=False), encoding="utf-8")

    # ---- writes ------------------------------------------------------------------
    @staticmethod
    def _normalize(m: np.ndarray) -> np.ndarray:
        m = np.asarray(m, dtype=np.float32)
        norms = np.linalg.norm(m, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return m / norms

    def add(self, vectors, records: list[dict]):
        if len(records) == 0:
            return
        v = self._normalize(np.asarray(vectors, dtype=np.float32))
        with self._lock:
            self.vectors = v if self.vectors.size == 0 else np.vstack([self.vectors, v])
            self.records.extend(records)
            self._save()

    def delete_source(self, source: str) -> int:
        with self._lock:
            keep = [i for i, r in enumerate(self.records) if r["source"] != source]
            removed = len(self.records) - len(keep)
            if removed:
                self.vectors = self.vectors[keep] if keep else np.zeros((0, 0), dtype=np.float32)
                self.records = [self.records[i] for i in keep]
                self._save()
            return removed

    # ---- reads -------------------------------------------------------------------
    def search(self, query_vec, k: int):
        with self._lock:
            if not self.records:
                return []
            q = self._normalize(np.asarray(query_vec, dtype=np.float32).reshape(1, -1))[0]
            scores = self.vectors @ q
            idx = np.argsort(-scores)[:k]
            return [(self.records[i], float(scores[i])) for i in idx]

    def by_page(self, source: str, page):
        with self._lock:
            return [r for r in self.records if r["source"] == source and r.get("page") == page]

    def sources(self) -> dict:
        with self._lock:
            out: dict[str, dict] = {}
            for r in self.records:
                s = out.setdefault(r["source"], {"text_chunks": 0, "image_chunks": 0})
                s["image_chunks" if r["type"] == "image" else "text_chunks"] += 1
            return out
