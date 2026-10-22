import logging

from langchain_core.tools import tool
from rag.ingestion import retrieve

logger = logging.getLogger(__name__)


@tool
def rag_tool(query: str, claim_id: str) -> str:
    """
    Search indexed insurance claim documents using a simple query.

    Args:
        query: Question or information to search for.
        claim_id: User ID used as the Pinecone namespace.
    """
    query = query.strip()
    claim_id = claim_id.strip()

    if not query:
        return "Error: search query cannot be empty."

    if not claim_id:
        return "Error: claim_id is required."

    try:
        # Search existing documents using the retrieve function.
        documents = retrieve(
            query=query,
            user_id=claim_id,
            k=4,
        )

        if not documents:
            return "No relevant claim documents found."

        results = []

        for i, document in enumerate(documents, start=1):
            content = document.page_content.strip()
            metadata = document.metadata or {}
            source = metadata.get("source", "Unknown document")

            if content:
                results.append(
                    f"Result {i}\n"
                    f"Source: {source}\n"
                    f"Content: {content}"
                )

        if not results:
            return "No relevant document content found."

        return "\n\n".join(results)

    except Exception:
        logger.exception("Claim document search failed.")
        return (
            "Error: claim document search failed. "
            "Check the server logs."
        )


# Tools available to the LangGraph agent.
tools = [
    rag_tool,
]