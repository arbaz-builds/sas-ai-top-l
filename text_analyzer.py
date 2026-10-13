from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from agent_state import State
from LLM import LLM_Plain

TextAnalyzer_Prompt = """You are the Text Analyzer of an insurance claim review system.
You get the claimant's messages and the text returned by the tools (document passages, insurance company records).

Do this:
1. FACTS: extract the key facts as "field: value" (claimant name, policy number, dates, amounts, hospital/vendor, diagnosis or damage description, etc.). Only use what is written in the text.
2. ISSUES: list inconsistencies or suspicious points inside the text (conflicting dates, amounts or names, missing details, strange wording).
3. EVIDENCE: for every fact and every issue, give where it comes from (the source file and page shown in the text, or the claimant's message).
4. If something is not in the text, write "not found". Never guess and never invent.

Keep it short and structured."""

MAX_CHARS = 30000


def _text_of(content):
    # message content can be a list (text + image parts); keep only the text, never image data
    if isinstance(content, str):
        return content
    return "\n".join(p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text")


def text_analyzer(state: State):
    parts = []
    for m in state["messages"]:
        if isinstance(m, ToolMessage):
            parts.append("[tool result]\n" + _text_of(m.content))
        elif isinstance(m, HumanMessage):
            parts.append("[claimant message]\n" + _text_of(m.content))

    data = "\n\n".join(p for p in parts if p.strip())[:MAX_CHARS]
    if not data.strip():
        return {"TextDATA": "No text data to analyze."}

    output = LLM_Plain().invoke([SystemMessage(content=TextAnalyzer_Prompt), HumanMessage(content=data)])
    return {"TextDATA": output.content}
