from state import State
from langchain_core.messages import SystemMessage
from prompts import ToolCalling_Prompt
from models import resision_LLM 
from tools import tools 


def Tool_node_LLM(state: State):
    DATA = [SystemMessage(content=ToolCalling_Prompt)] + state["messages"]
    TOOL_LLM = resision_LLM.bind_tools(tools)
    output = TOOL_LLM.invoke(DATA)
    return {"messages": [output]}