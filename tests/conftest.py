import io
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mmrag import config  # noqa: E402
from mmrag.rag import MultimodalRAG  # noqa: E402
from mmrag.store import VectorStore  # noqa: E402
from tests.fake_client import FakeClient  # noqa: E402


@pytest.fixture
def rag(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "IMAGE_DIR", tmp_path / "images")
    monkeypatch.setattr(config, "UPLOAD_DIR", tmp_path / "uploads")
    return MultimodalRAG(client=FakeClient(), store=VectorStore(tmp_path / "index"))


def make_png(w=400, h=300) -> bytes:
    img = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(img)
    for i, height in enumerate([80, 120, 200, 150]):
        d.rectangle([40 + i * 80, h - 20 - height, 100 + i * 80, h - 20], fill=(30 + i * 50, 90, 200))
    d.text((10, 10), "Revenue by quarter", fill="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
