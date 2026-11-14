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


    
    















































































class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


Impact = Literal["critical", "high", "medium", "low"]


class Basis(Strict):
    """Saboot: ye points kahan se aaye."""
    source: str                          # file name ya "system rule"
    page: Optional[int] = None
    quote: Optional[str] = Field(default=None, description="Exact quote, under 15 words")


class ScoreItem(Strict):
    item: str                            # e.g. "Photos not found"
    points: int = Field(ge=0)            # risk points
    reason: str                          # 1 sentence: kyun
    basis: Basis


class Finding(Strict):
    title: str
    severity: Literal["low", "medium", "high"]
    description: str
    basis: List[Basis] = Field(min_length=1)


class MissingItem(Strict):
    item: str
    impact: Impact                       # code set karega
    expected_source: str


class GreenFlag(Strict):
    flag: str
    basis: str                           # numbers jo reconcile hue


class ClaimAnalysis(Strict):
    risk_score: int = Field(ge=0, le=100)    # 100 = zyada risk
    status: Literal["Low", "Medium", "High", "Incomplete", "No documents"]
    summary: str                             # LLM likhega
    human_review_required: bool              # koi default nahi
    human_review_reasons: List[str]
    score_breakdown: List[ScoreItem] = Field(min_length=1)
    findings: List[Finding] = []
    missing_information: List[MissingItem] = []
    green_flags: List[GreenFlag] = []
    limitations: List[str] = []

    @model_validator(mode="after")
    def check_rules(self):
        if self.risk_score != min(100, sum(i.points for i in self.score_breakdown)):
            raise ValueError("risk_score does not match score_breakdown")
        needs_review = (
            bool(self.missing_information)
            or any(f.severity == "high" for f in self.findings)
            or self.status in ("Incomplete", "High", "No documents")
        )
        if needs_review and not self.human_review_required:
            raise ValueError("human_review_required must be true")
        if self.human_review_required and not self.human_review_reasons:
            raise ValueError("human_review_reasons required")
        if self.status == "Low" and (self.missing_information or self.findings):
            raise ValueError("status cannot be Low with missing items or findings")
        return self

























































class State(TypedDict):
      messages: Annotated[List[BaseMessage], add_messages]
      decision: str
      RefindTopic: str
      TextDATA: Optional[TextAnalysis]
      ImageDATA: str
      Dataprocess: str
      Finaloutput: Optional[ClaimAnalysis]