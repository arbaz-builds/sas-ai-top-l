from langchain_core.tools import tool

from rag.ingestion import get_store

MAX_IMAGES = 6


@tool(response_format="content_and_artifact")
def rag_tool(query: str, claim_id: str = ""):
    """Search the indexed insurance claim documents (text and images) and return the most relevant passages.
    Pass claim_id when the claim is known, so only that claim's documents are searched.
    Images that match are attached for the image analyzer."""
    store = get_store()
    claim = {"claim_id": {"$eq": claim_id}} if claim_id else {}

    hits = store.similarity_search(query, k=4, filter=claim or None)
    if not hits:
        return "No relevant document content found.", {"images": []}

    # mixed documents: if a TEXT chunk matched, also bring the images from the same page (and the other way round)
    seen = {(d.metadata.get("source"), d.metadata.get("page"), d.metadata.get("type"), d.page_content) for d in hits}
    extra = []
    for src, page in {(d.metadata.get("source"), d.metadata.get("page")) for d in hits if d.metadata.get("page") is not None}:
        hit_types = {d.metadata.get("type") for d in hits if d.metadata.get("source") == src and d.metadata.get("page") == page}
        if hit_types == {"text", "image"}:
            continue
        other = "image" if "text" in hit_types else "text"
        flt = {**claim, "source": {"$eq": src}, "page": {"$eq": page}, "type": {"$eq": other}}
        for d in store.similarity_search(query, k=2, filter=flt):
            key = (d.metadata.get("source"), d.metadata.get("page"), d.metadata.get("type"), d.page_content)
            if key not in seen:
                seen.add(key)
                extra.append(d)

    passages, images, paths = [], [], set()
    for d in hits + extra:
        m = d.metadata
        where = f"{m.get('source', '?')}" + (f" page {m['page']}" if m.get("page") is not None else "")
        passages.append(f"[{where} | {'image description' if m.get('type') == 'image' else 'text'}] {d.page_content}")
        p = m.get("image_path")
        if m.get("type") == "image" and p and p not in paths and len(images) < MAX_IMAGES:
            paths.add(p)
            images.append({"path": p, "source": m.get("source"), "page": m.get("page")})
    return "\n\n".join(passages), {"images": images}


# TODO: API tool (insurance company data) - needs the real API endpoint, not written yet.
tools = [rag_tool]
