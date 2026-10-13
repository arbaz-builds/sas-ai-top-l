from langchain_core.tools import tool

from mmrag.rag import get_store


@tool
def rag_tool(query: str) -> str:
    """Search the uploaded insurance claim documents (text and images) and return the most relevant passages."""
    docs = get_store().similarity_search(query, k=4)
    if not docs:
        return "No relevant document content found."
    return "\n\n".join(
        f"[{d.metadata.get('source', '?')} page {d.metadata.get('page', '?')}] {d.page_content}" for d in docs
    )


# TODO: API tool (insurance company data) - needs the real API endpoint, not written yet.
tools = [rag_tool]
