from typing import TypedDict, Literal, Annotated, List, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field,ConfigDict, model_validator




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
    source: str = Field(description="Original file name, or 'Not specified in analysis'.")
    location: Optional[str] = Field(default=None, description="Page, section or field if available, otherwise null.")
    excerpt: Optional[str] = Field(default=None, description="One continuous quote under 20 words, otherwise null.")
    reason: str = Field(description="One sentence on why this evidence supports the finding.")


class Finding(BaseModel):
    title: str = Field(description="Concise problem name.")
    category: Literal[
        "amount_mismatch",
        "date_mismatch",
        "calculation_error",
        "duplicate_invoice",
        "document_inconsistency",
        "possible_alteration",
        "other",
    ]
    severity: Literal["low", "medium", "high"]
    description: str = Field(description="One factual sentence describing the concern.")
    evidence: List[Evidence] = Field(min_length=1)
    requires_human_verification: bool = True


class MissingItem(BaseModel):
    item: str = Field(description="Missing document or information named by the analysis.")
    assessment: Literal["likely_oversight", "needs_verification", "not_a_concern"]
    reason: str = Field(description="One neutral sentence explaining the assessment.")


class ScoreBreakdown(BaseModel):
    base_points: int = 5
    findings_points: int = Field(ge=0)
    missing_points: int = Field(ge=0, le=15)


class ClaimAnalysis(BaseModel):
    review_score: int = Field(ge=0, le=100)
    status: Literal["Low", "Medium", "High", "No documents"]
    summary: str = Field(description="1-2 sentences explaining the main reasons for the score.")
    findings: List[Finding] = Field(default_factory=list, max_length=4)
    missing_information: List[MissingItem] = Field(default_factory=list)
    green_flags: List[str] = Field(
        default_factory=list,
        max_length=4,
        description="Checks the analysis explicitly states as matched or reconciled. Never inferred. Empty if none.",
    )
    limitations: List[str] = Field(default_factory=list)
    human_review_required: bool = False
    score_breakdown: Optional[ScoreBreakdown] = None  # filled in code by finalize(), not by the LLM











































# -----------------------------
# COMMON CONFIGURATION
# -----------------------------

class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Fact(Strict):
    field: str
    value: str
    source: str
    page: Optional[int]
    evidence: str


class Evidence(Strict):
    source: str
    page: Optional[int]
    quote: str


class Issue(Strict):
    description: str
    conflicting_values: List[str]
    severity: Literal["low", "medium", "high"]
    evidence: List[Evidence]
    reason: str


class MissingItem(Strict):
    field: str
    expected_source: str


class FinancialCheck(Strict):
    check: str
    result: Literal["reconciles", "fails", "not_verified"]
    details: str


class CrossDocument(Strict):
    status: Literal["MATCH", "MISMATCH", "PARTIALLY_VERIFIED", "NOT_VERIFIED"]
    details: List[str]


class TextAnalysis(Strict):
    facts: List[Fact]
    issues: List[Issue]
    missing_information: List[MissingItem]
    financial_checks: List[FinancialCheck]
    cross_document_verification: CrossDocument
    summary: str


    
    




























































































class State(TypedDict):
      messages: Annotated[List[BaseMessage], add_messages]
      decision: str
      RefindTopic: str
      TextDATA: Optional[TextAnalysis]
      ImageDATA: str
      Dataprocess: str
      Finaloutput: Optional[ClaimAnalysis]