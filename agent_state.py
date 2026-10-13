from typing import TypedDict, Literal, Annotated, List
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field



class State(TypedDict):
      messages: Annotated[List[BaseMessage], add_messages]
      TextDATA: str
      ImageDATA: str
      Dataprocess: str
      Finaloutput: str 