from langchain_core.tools import tool

from rag.ingestion import get_store

MAX_IMAGES = 6


@tool(response_format="content_and_artifact")
def rag_tool(query: str, claim_id: str = ""):
    """Search the indexed insurance claim documents (text and images) and return the most relevant passages.
    Pass claim_id when the claim is known, so only that claim's documents are searched.
    The original images that match are attached for the image analyzer."""
    store = get_store()
    claim = {"claim_id": {"$eq": claim_id}} if claim_id else {}
    hits = store.similarity_search(query, k=4, filter=claim or None)

    # mixed pages: a text hit also brings the images of its page, an image hit brings the text of its page
    pages = {(d.metadata["source"], d.metadata["page"], d.metadata["type"]) for d in hits if "page" in d.metadata}
    for source, page, kind in pages:
        other = "image" if kind == "text" else "text"
        hits += store.similarity_search(
            query, k=2, filter={**claim, "source": {"$eq": source}, "page": {"$eq": page}, "type": {"$eq": other}})

    seen, lines, images = set(), [], []
    for d in hits:
        m = d.metadata
        if d.page_content in seen:
            continue
        seen.add(d.page_content)
        where = m["source"] + (f" page {m['page']}" if "page" in m else "")
        if m["type"] == "image":
            lines.append(f"[{where} | image] (original image attached for the image analysis)")
            images.append({"path": m["image_path"], "source": m["source"], "page": m.get("page")})
        else:
            lines.append(f"[{where} | text] {d.page_content}")
    return "\n\n".join(lines) or "No relevant document content found.", {"images": images[:MAX_IMAGES]}


# TODO: API tool (insurance company data) - needs the real API endpoint, not written yet.
tools = [rag_tool]
