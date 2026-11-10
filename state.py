from typing import TypedDict, Literal, Annotated, List, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field




class IntroDecision(BaseModel):
    reply: str = Field(
        description="A short, friendly message to the user, in the user's language. "
                    "If decision is 'unclear': answer a greeting or a general question briefly and say what this "
                    "assistant can do (analyze claim documents and images, cross-check them, give a review score "
                    "with reasons). If the user asked for an analysis but details are missing, ask for ALL missing "
                    "details in one message (which claim, which documents or images, what to check). "
                    "If decision is 'analyze_claim': one short sentence saying what was understood and that the "
                    "analysis is starting. Never give analysis results here."
    )
    decision: Literal["analyze_claim", "unclear"] = Field(
        description="'analyze_claim' if the user (across this conversation) has clearly asked for a claim analysis "
                    "AND has given enough detail to start it (which claim, which documents or images, what to check). "
                    "'unclear' if the message is casual chat, a greeting, a general question, or an analysis "
                    "request that still misses key details."
    )
    RefindTopic: Optional[str] = Field(
        default=None,
        description="A clean 1-3 sentence description of what to analyze (claim reference, the documents or images, "
                    "what to focus on), built from the full conversation, ready to pass to the next stage. "
                    "Only filled when decision is 'analyze_claim'; None otherwise."
    )







class Evidence(BaseModel):
    source: str
    location: Optional[str] = None
    excerpt: Optional[str] = None
    reason: str


class Finding(BaseModel):
    title: str
    category: Literal[
        "amount_mismatch",
        "date_mismatch",
        "calculation_error",
        "duplicate_invoice",
        "document_inconsistency",
        "possible_alteration",
        "image_concern",
        "other",
    ]
    severity: Literal["low", "medium", "high"]
    description: str
    evidence: List[Evidence] = Field(min_length=1)
    requires_human_verification: bool = True


class MissingItem(BaseModel):
    item: str
    assessment: Literal["likely_oversight", "needs_verification", "not_a_concern"]
    reason: str


class ClaimAnalysis(BaseModel):
    review_score: int = Field(ge=0, le=100)
    status: Literal["Low", "Medium", "High", "No documents"]
    summary: str
    findings: List[Finding] = Field(default_factory=list, max_length=4)
    missing_information: List[MissingItem] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    human_review_required: bool = False


















class State(TypedDict):
      messages: Annotated[List[BaseMessage], add_messages]
      decision: str
      RefindTopic: str
      TextDATA: str
      ImageDATA: str
      Dataprocess: str
      Finaloutput: Optional[ClaimAnalysis]