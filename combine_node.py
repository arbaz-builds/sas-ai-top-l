from langchain_core.messages import HumanMessage, SystemMessage

from state import State
from models import resision_LLM
from prompts import Combine_Prompt
import logging


logger = logging.getLogger(__name__)



def combine_agent(state: State):
    text_data = state.get("TextDATA") or "No text data."
    image_data = state.get("ImageDATA") or "No image data."

    DATA = [
        SystemMessage(content=Combine_Prompt),
        HumanMessage(
            content=f"This is the Text data:\n{text_data}\n\nThis is the Image data (may be empty):\n{image_data}"
        ),
    ]

    try:
        output = revision_llm.invoke(DATA)
    except Exception as e:
        logger.warning(f"combination node fallback: {e}")
        output = openrouter_model.invoke(DATA)

    return {"Dataprocess": output.content}