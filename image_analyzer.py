import base64
import io

from langchain_core.messages import HumanMessage
from PIL import Image

from agent_state import State
from LLM import LLM_Vision

ImageAnalyzer_Prompt = """You are the Image Analyzer of an insurance claim review system. You look at ONE image that belongs to a claim (bill, discharge summary, ID, policy paper, photo of damage, etc.).

Answer in this structure:
1. TYPE: what kind of image or document this is.
2. TEXT: all readable text exactly as written (names, policy number, dates, amounts, hospital or vendor, stamps, signatures). Write "unreadable" for parts you cannot read. Never guess numbers.
3. CONTENT: for photos, describe what is visible (what is damaged, where, how severe).
4. ANOMALIES: anything that looks edited or inconsistent (mixed fonts or sizes, misaligned text, blurred or pasted-looking areas around numbers, totals that do not add up, unrealistic lighting or textures). These are possible signs only, not proof, so say how sure you are (low / medium / high).
5. If nothing looks wrong, write "none seen".

Do not invent anything that is not visible."""

MAX_IMAGES = 6
MAX_BYTES = 120000  # hosted NVIDIA endpoints limit inline base64 images (~180 KB)


def _images_in(messages):
    urls = []
    for m in messages:
        if isinstance(m, HumanMessage) and isinstance(m.content, list):
            for part in m.content:
                if isinstance(part, dict) and part.get("type") == "image_url":
                    u = part["image_url"]
                    urls.append(u["url"] if isinstance(u, dict) else u)
    return urls


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
    urls = _images_in(state["messages"])
    if not urls:
        return {"ImageDATA": "No images to analyze."}

    llm = LLM_Vision()
    results = []
    for n, url in enumerate(urls[:MAX_IMAGES], start=1):
        # instructions go in the same message as the image (Llama-3.2-vision does not like a system prompt with images)
        msg = HumanMessage(content=[
            {"type": "text", "text": f"{ImageAnalyzer_Prompt}\n\nThis is image {n} of {len(urls)}."},
            {"type": "image_url", "image_url": {"url": _shrink(url)}},
        ])
        try:
            out = llm.invoke([msg]).content
        except Exception as e:
            out = f"Could not analyze this image: {e}"
        results.append(f"## Image {n}\n{out}")

    if len(urls) > MAX_IMAGES:
        results.append(f"(Only the first {MAX_IMAGES} of {len(urls)} images were analyzed.)")
    return {"ImageDATA": "\n\n".join(results)}
