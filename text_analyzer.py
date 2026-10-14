from langchain_core.messages import HumanMessage, SystemMessage,ToolMessage

from agent_state import State
from LLM import resision_LLM
from system_prompt import TextAnalyzer_Prompt







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

    output = resision_LLM.invoke([SystemMessage(content=TextAnalyzer_Prompt), HumanMessage(content=data)])
    return {"TextDATA": output.content}
