from agent_state import State
from langchain_core.messages import SystemMessage
from system_prompt import Agent1_Prompt
from LLM import resision_LLM 
from tool import tools 


def Tool_node(state: State):
    DATA = [SystemMessage(content=Agent1_Prompt)] + state["messages"]
    TOOL_LLM = resision_LLM.bind_tools(tools)
    output = TOOL_LLM.invoke(DATA)
    return {"messages": [output]}