from agent_state import State
from langchain_core.messages import SystemMessage
from system_prompt import Agent1_Prompt
from LLM import LLM_bind_Tool
from tool import Tool


def agent1(state: State):
    DATA = [SystemMessage(content=Agent1_Prompt)] + state["messages"]
    TOOL_LLM = LLM_bind_Tool()
    output = TOOL_LLM.invoke(DATA)
    return {"messages": [output]}
