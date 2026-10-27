import logging

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from rag.ingestion import retrieve

logger = logging.getLogger(__name__)


@tool
def rag_tool(query: str, config: RunnableConfig) -> str:
    """
    Search the uploaded insurance claim documents of the current chat.

    Args:
        query: Question or information to search for.
    """
    query = query.strip()

    if not query:
        return "Error: search query cannot be empty."

    # The chat's thread_id is also the Pinecone namespace.
    # It comes from the graph config, not from the LLM.
    thread_id = (config.get("configurable") or {}).get("thread_id")

    if not thread_id:
        return "Error: thread_id is missing in the config."

    try:
        documents = retrieve(
            query=query,
            user_id=thread_id,
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