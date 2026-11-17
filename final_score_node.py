from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from state import State, RepairClaimAnalysis
from models import resision_LLM
from prompts import FINAL_REVIEW_PROMPT

def final_score(state: State):
 try:
    DATA = state.get("Dataprocess") or "No combined analysis available."

    Final_DATA = [
    SystemMessage(content=FINAL_REVIEW_PROMPT),
    HumanMessage(content=f"This is the combined         analysis:\n{DATA}"),
  ]

    Structure_LLM = resision_LLM.with_structured_output(RepairClaimAnalysis)
    output = Structure_LLM.invoke(Final_DATA)
 expect :
    Structure_LLM = resision_LLM.with_structured_output(RepairClaimAnalysis)
    output = Structure_LLM.invoke(Final_DATA)
 

    
 return {
      "Finaloutput": output,
      "messages": [
        AIMessage(
            content=output.model_dump_json(),
            additional_kwargs={"message_type": "claim_analysis"}
        )
    ]
}