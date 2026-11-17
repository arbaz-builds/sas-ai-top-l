from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from state import State, RepairClaimAnalysis
from models import resision_LLM, Gemini_Model
from prompts import FINAL_REVIEW_PROMPT
 import logging

logger = logging.getLogger(__name__)


def final_score(state: State):
    data = state.get("Dataprocess")
    if not data:
        raise ValueError("final_score: 'Dataprocess' missing from state")

    messages = [
        SystemMessage(content=FINAL_REVIEW_PROMPT),
        HumanMessage(content=f"This is the combined analysis:\n{data}"),
    ]

    try:
        output = primary_llm.with_structured_output(RepairClaimAnalysis).invoke(messages)
    except Exception:
        logger.exception("Primary LLM failed, falling back to Gemini")
        output = gemini_model.with_structured_output(RepairClaimAnalysis).invoke(messages)

    return {
        "Finaloutput": output,
        "messages": [
            AIMessage(
                content=output.model_dump_json(),
                additional_kwargs={"message_type": "claim_analysis"},
            )
        ],
    }