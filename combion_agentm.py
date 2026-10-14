from agent_state import State
from langchain_core.messages import SystemMessage
from system_prompt import Agent1_Prompt
from LLM import resision_LLM 
from tool import tools 


def agent1(state: State):
    DATA = [SystemMessage(content=Agent1_Prompt)], HumanMessage(content = "this is Text data"/ state["TextDate"]/n "this is image data maybe emtry"/n State["Image date"])]
    

    TOOL_LLM = resision_LLM(DATA)
    return {"messages": [output]}