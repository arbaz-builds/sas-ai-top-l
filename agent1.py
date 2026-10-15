from agent_state import State, IntroDecision
from langchain_core.messages import SystemMessage
from system_prompt import Agent1_Prompt
from LLM import resision_LLM 
from tool import tools 


def IntroDecision_LLM(state: State):
    DATA = [SystemMessage(content=Agent1_Prompt)] + state["messages"]
    Structure_LLM = resision_LLM.Structure_output(IntroDecision)
    output = Structure_LLM.invoke(DATA)
    return {"messages": [output]}
