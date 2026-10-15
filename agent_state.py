from typing import TypedDict, Literal, Annotated, List
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field




class IntroDecision(BaseModel):
    reply: str = Field(
        description="A short, friendly message to the user. If decision is "
                     "'unclear', introduce this agent as a blog-writing "
                     "assistant and ask what topic they'd like a blog about. "
                     "If decision is 'blog_request', briefly confirm the "
                     "topic understood and that writing is starting."
    )
    decision: Literal["blog_request", "unclear"] = Field(
        description="'blog_request' if the user (across this conversation) "
                     "has given enough detail to start writing a blog. "
                     "'unclear' if the message is casual chat, a greeting, "
                     "or still missing key details like topic."
    )
    RefindTopic: Optional[str] = Field(
        default=None,
        description="A clean, polished topic description built from the "
                     "full conversation, ready to pass to the planning "
                     "stage. Only filled when decision is 'blog_request'; "
                     "left as None otherwise."
    )



class State(TypedDict):
      messages: Annotated[List[BaseMessage], add_messages]
      TextDATA: str
      ImageDATA: str
      Dataprocess: str
      Finaloutput: str 