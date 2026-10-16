import base64
import io
import os

from langchain_core.messages import HumanMessage, ToolMessage
from PIL import Image

from models import vision_LLM
from prompts import ImageAnalyzer_Prompt
from rag.image_utils import image_data
from state import State

MAX_IMAGES = 6
MAX_BYTES = 120000  # hosted NVIDIA endpoints limit inline base64 images (~180 KB)


def _collect_images(messages):
    """[(where it comes from, data URL)]: images the user sent + the original images rag_tool found (ToolMessage.artifact)."""
    found, seen = [], set()
    for m in messages:
        if isinstance(m, HumanMessage) and isinstance(m.content, list):
            for part in m.content:
                if isinstance(part, dict) and part.get("type") == "image_url":
                    u = part["image_url"]
                    url = u["url"] if isinstance(u, dict) else u
                    if url not in seen:
                        seen.add(url)
                        found.append(("sent by the user", url))
        elif isinstance(m, ToolMessage) and isinstance(getattr(m, "artifact", None), dict):
            for img in m.artifact.get("images", []):
                p = img.get("path")
                if not p or p in seen or not os.path.exists(p):
                    continue
                seen.add(p)
                where = str(img.get("source") or "document") + (f", page {img['page']}" if img.get("page") is not None else "")
                found.append((where, image_data(p)))
    return found


def _shrink(url):
    # make a big data-URL image small enough for the API; other URLs pass through unchanged
    if not url.startswith("data:image"):
        return url
    raw = base64.b64decode(url.split(",", 1)[1])
    if len(raw) <= MAX_BYTES:
        return url
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    img.thumbnail((1600, 1600))
    quality = 85
    while True:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        if buf.tell() <= MAX_BYTES or min(img.size) <= 64:
            break
        if quality > 55:
            quality -= 10
        else:
            img = img.resize((int(img.width * 0.85), int(img.height * 0.85)))
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def image_analyzer(state: State):
    images = _collect_images(state["messages"])
    if not images:
        return {"ImageDATA": "No images to analyze."}

    llm = vision_LLM
    results = []
    for n, (where, url) in enumerate(images[:MAX_IMAGES], start=1):
        # instructions go in the same message as the image (Llama-3.2-vision does not like a system prompt with images)
        msg = HumanMessage(content=[
            {"type": "text", "text": f"{ImageAnalyzer_Prompt}\n\nThis is image {n} of {len(images)} ({where})."},
            {"type": "image_url", "image_url": {"url": _shrink(url)}},
        ])
        try:
            out = llm.invoke([msg]).content
        except Exception as e:
            out = f"Could not analyze this image: {e}"
        results.append(f"## Image {n} ({where})\n{out}")

    if len(images) > MAX_IMAGES:
        results.append(f"(Only the first {MAX_IMAGES} of {len(images)} images were analyzed.)")
    return {"ImageDATA": "\n\n".join(results)}
