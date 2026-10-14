from agent_state import State
from langchain_core.messages import SystemMessage, HumanMessage 
from system_prompt import 
from LLM import resision_LLM 



def agent1(state: State):
    DATA = [SystemMessage(content=)], HumanMessage(content = "this is Text data"/ state["TextDate"]/n "this is image data maybe emtry"/n State["Image date"])]
    

    TOOL_LLM = resision_LLM(DATA)
    return {"messages": [output]}