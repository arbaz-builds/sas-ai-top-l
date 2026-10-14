from langchain_core.messages import HumanMessage, SystemMessage

from agent_state import State
from LLM import resision_LLM
from system_prompt import Final_prompt


def final_score(state: State):
    DATA = state.get("Dataprocess") or "No combined analysis available."

    Final_DATA = [
        SystemMessage(content=Final_prompt),
        HumanMessage(content=f"This is the combined analysis:\n{DATA}"),
    ]

    output = resision_LLM.invoke(Final_DATA)
    return {"Finaloutput": output.content}
