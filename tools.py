import logging
from pathlib import Path

from langchain_core.tools import tool
from rag.ingestion import get_store, image_path


logger = logging.getLogger(__name__)

MAX_IMAGES = 6


@tool(response_format="content_and_artifact")
def rag_tool(query: str, claim_id: str = "") -> tuple[str, dict]:
    """
    Search the indexed insurance claim documents, including text and images.

    Args:
        query: The information to search for in the claim documents.
        claim_id: The ID of the claim whose documents should be searched.

    Returns:
        A tuple containing:
        1. Relevant document content.
        2. An artifact containing paths to matching original images.
    """

    query = query.strip()
    claim_id = claim_id.strip()

    # A claim ID is required to select the correct Pinecone namespace.
    if not claim_id:
        return (
            "Error: claim_id is required to search claim documents.",
            {"images": []},
        )

    if not query:
        return (
            "Error: search query cannot be empty.",
            {"images": []},
        )

    # Search only the specified claim's vector-store namespace.
    try:
        store = get_store(claim_id)
        hits = store.similarity_search(query, k=4)

    except Exception:
        logger.exception("Failed to search claim documents.")

        return (
            "Error: claim document search failed. Check the server logs.",
            {"images": []},
        )

    # Find matching pages so we can also retrieve related text or images
    # from the same document page.
    pages = {
        (
            document.metadata.get("source"),
            document.metadata.get("page"),
            document.metadata.get("type"),
        )
        for document in hits
        if document.metadata.get("source") is not None
        and document.metadata.get("page") is not None
        and document.metadata.get("type") in {"text", "image"}
    }

    # Retrieve the complementary content type from each matching page.
    for source, page, kind in sorted(
        pages,
        key=lambda item: (
            str(item[0]),
            str(item[1]),
            str(item[2]),
        ),
    ):
        other_type = "image" if kind == "text" else "text"

        try:
            related_hits = store.similarity_search(
                query,
                k=2,
                filter={
                    "source": {"$eq": source},
                    "page": {"$eq": page},
                    "type": {"$eq": other_type},
                },
            )

            hits.extend(related_hits)

        except Exception:
            logger.warning(
                "Could not retrieve related content from a matching page.",
                exc_info=True,
            )

    lines = []
    images = []

    seen_documents = set()
    seen_image_keys = set()

    # Process retrieved documents and resolve original image paths.
    for document in hits:
        metadata = document.metadata or {}
        content = document.page_content or ""

        source = str(metadata.get("source", "Unknown document"))
        page = metadata.get("page")
        kind = metadata.get("type", "text")

        # Deduplicate without accidentally removing identical text
        # that appears in different documents or on different pages.
        document_key = (
            source,
            str(page),
            kind,
            content,
        )

        if document_key in seen_documents:
            continue

        seen_documents.add(document_key)

        location = source

        if page is not None:
            location += f", page {page}"

        if kind == "image":
            image_key = metadata.get("image_key")
            image_available = (
                image_key is not None
                and image_key in seen_image_keys
            )

            # Restore the original image from the claim's image storage.
            if image_key and not image_available:
                if len(images) < MAX_IMAGES:
                    try:
                        path = image_path(
                            claim_id,
                            str(image_key),
                        )

                        if path and Path(path).is_file():
                            images.append(
                                {
                                    "path": str(path),
                                    "source": source,
                                    "page": page,
                                }
                            )

                            seen_image_keys.add(image_key)
                            image_available = True

                    except Exception:
                        logger.warning(
                            "Could not load a retrieved original image.",
                            exc_info=True,
                        )

            if image_available:
                lines.append(
                    f"[{location} | image] "
                    "Original image attached for image analysis."
                )
            else:
                lines.append(
                    f"[{location} | image] "
                    "A matching image was found, but its original "
                    "file could not be loaded."
                )

        else:
            lines.append(
                f"[{location} | text] {content}"
            )

    # Build the text content returned to the agent.
    result = "\n\n".join(lines)

    if not result:
        result = "No relevant document content found."

    # LangChain receives text as the tool content and image paths
    # as the artifact. Your downstream code must consume that artifact.
    artifact = {
        "images": images,
    }

    return result, artifact


# Register the tools available to the LangGraph agent.
# Add the real insurance API tool here once its endpoint,
# authentication and response schema are defined.
tools = [
    rag_tool,
]