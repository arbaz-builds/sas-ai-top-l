from langchain_core.messages import HumanMessage, SystemMessage

from agent_state import State
from LLM import resision_LLM
from system_prompt import  Final_prompt


def combine_agent(state: State):
    DATA = state.get("") or "No text data."

    Final_DATA = [
        SystemMessage(content=Final_prompt),
        HumanMessage(content=f"This is the Text data:\n{DATA}),
    ]

    output = resision_LLM.invoke(Final_DATA)
    return {"Finaloutput": output.content}