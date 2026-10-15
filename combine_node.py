from langchain_core.messages import HumanMessage, SystemMessage

from state import State
from models import resision_LLM
from prompts import Combine_Prompt


def combine_agent(state: State):
    text_data = state.get("TextDATA") or "No text data."
    image_data = state.get("ImageDATA") or "No image data."

    DATA = [
        SystemMessage(content=Combine_Prompt),
        HumanMessage(content=f"This is the Text data:\n{text_data}\n\nThis is the Image data (may be empty):\n{image_data}"),
    ]

    output = resision_LLM.invoke(DATA)
    return {"Dataprocess": output.content}
