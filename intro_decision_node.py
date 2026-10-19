from state import State, IntroDecision
from langchain_core.messages import SystemMessage
from prompts import IntroDecision_Prompt
from models import resision_LLM 
from tools import tools 


def IntroDecision_LLM(state: State):
    DATA = [SystemMessage(content=IntroDecision_Prompt)] + state["messages"]
    Structure_LLM = resision_LLM.with_structured_output(IntroDecision)
    output = Structure_LLM.invoke(DATA)
    return {
        "messages": [AIMessage(content=output.reply)],
        "decision": output.decision,
        "RefindTopic": output.RefindTopic or "",
    }