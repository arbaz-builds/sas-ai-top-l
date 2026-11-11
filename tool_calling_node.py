
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from models import resision_LLM
from prompts import ToolCalling_Prompt
from state import State
from tools import tools


def _loop_messages(messages):
    """Only this run's tool loop: tool calls and their results, after the user's last message."""
    last_human = max((i for i, m in enumerate(messages) if isinstance(m, HumanMessage)), default=-1)
    return [
        m for m in messages[last_human + 1:]
        if isinstance(m, ToolMessage) or (isinstance(m, AIMessage) and m.tool_calls)
    ]


def Tool_node_LLM(state: State):
    DATA = (
        [SystemMessage(content=ToolCalling_Prompt), HumanMessage(content=state["RefindTopic"])]
        + _loop_messages(state["messages"])
    )
    TOOL_LLM = resision_LLM.bind_tools(tools)
    output = TOOL_LLM.invoke(DATA)
    return {"messages": [output]}