from langchain_core.tools import tool

from rag.ingestion import get_store, image_path

MAX_IMAGES = 6

@tool(response_format="content_and_artifact")
def rag_tool(query: str, claim_id: str = ""):
"""Search the indexed insurance claim documents (text and images).

Requires a claim_id so that searches are restricted to the
corresponding claim namespace. Matching original images are
attached as artifacts for the image analyzer.
"""

# A claim ID is required for every search.
if not claim_id:
    return (
        "Error: claim_id is required to search claim documents.",
        {"images": []},
    )

# Search only within this claim's Pinecone namespace.
store = get_store(claim_id)

hits = store.similarity_search(query, k=4)

# Find related text/image chunks from the same document pages.
pages = {
    (d.metadata["source"], d.metadata["page"], d.metadata["type"])
    for d in hits
    if "page" in d.metadata and "type" in d.metadata
}

for source, page, kind in pages:
    other = "image" if kind == "text" else "text"

    related_hits = store.similarity_search(
        query,
        k=2,
        filter={
            "source": {"$eq": source},
            "page": {"$eq": page},
            "type": {"$eq": other},
        },
    )

    hits.extend(related_hits)

seen = set()
lines = []
images = []
seen_images = set()

for document in hits:
    metadata = document.metadata
    content = document.page_content

    # Avoid duplicate text chunks.
    if content in seen:
        continue

    seen.add(content)

    source = metadata.get("source", "Unknown document")
    page = metadata.get("page")
    kind = metadata.get("type", "text")

    where = source
    if page is not None:
        where += f" page {page}"

    if kind == "image":
        lines.append(
            f"[{where} | image] "
            "(Original image attached for image analysis.)"
        )

        # Retrieve the original image using the stored image_key.
        image_key = metadata.get("image_key")

        if image_key and image_key not in seen_images:
            seen_images.add(image_key)

            try:
                path = image_path(claim_id, image_key)

                if path and path.is_file():
                    images.append(
                        {
                            "path": str(path),
                            "source": source,
                            "page": page,
                        }
                    )
            except Exception:
                # Keep text results available if image retrieval fails.
                pass

    else:
        lines.append(f"[{where} | text] {content}")

result = "\n\n".join(lines)

if not result:
    result = "No relevant document content found."

# Return a maximum of six original images for image analysis.
return result, {"images": images[:MAX_IMAGES]}

TODO: Add the insurance company API tool when a real API endpoint

and authentication method are available.

tools = [rag_tool]