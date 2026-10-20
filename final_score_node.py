from langchain_core.messages import HumanMessage, SystemMessage

from state import State, ClaimAnalysis
from models import resision_LLM
from prompts import Final_Prompt

def final_score(state: State):
DATA = state.get("Dataprocess") or "No combined analysis available."

Final_DATA = [
    SystemMessage(content=Final_Prompt),
    HumanMessage(content=f"This is the combined analysis:\n{DATA}"),
]

Structure_LLM = resision_LLM.with_structured_output(ClaimAnalysis)
output = Structure_LLM.invoke(Final_DATA)

return {"Finaloutput": output}