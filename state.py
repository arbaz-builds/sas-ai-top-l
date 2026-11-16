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


    
    







































class Basis(BaseModel):
    source: str
    page: Optional[int] = None
    quote: Optional[str] = Field(default=None, description="Max 15 words")


class MismatchItem(BaseModel):
    field: str
    found: str = Field(description="Form/bill mein kya likha hai")
    expected: str = Field(description="Sahi kya hona chahiye ya kisse mismatch hai")
    impact: Literal["critical", "high", "medium", "low"]
    reason: str
    basis: Basis


class MissingItem(BaseModel):
    item: str
    impact: Literal["critical", "high", "medium", "low"]
    action: str = Field(description="Shop ko kya karna hai")
    basis: Basis


class RepairClaimAnalysis(BaseModel):
    # 0-29: High Reject | 30-69: Medium | 70-100: Low (All Good)
    approval_score: int = Field(ge=0, le=100)
    rejection_risk: Literal["High", "Medium", "Low", "No documents"]
    score_reasoning: str = Field(description="Kyun ye score aaya aur kya-kya sahi hai")
    human_review_required: bool
    human_review_reasons: List[str] = []

    available_info: List[str] = Field(description="Jo info/docs mile hain (short points)")
    verified_correct: List[str] = Field(description="Jo details bilkul sahi aur match hain")
    missing_info: List[MissingItem] = []
    wrong_or_mismatched: List[MismatchItem] = []

    @model_validator(mode="after")
    def check_rules(self):
        # 1. Auto-sync rejection_risk with approval_score
        if self.rejection_risk != "No documents":
            if self.approval_score <= 29 and self.rejection_risk != "High":
                raise ValueError("Score 0-29 must have rejection_risk='High'")
            elif 30 <= self.approval_score <= 69 and self.rejection_risk != "Medium":
                raise ValueError("Score 30-69 must have rejection_risk='Medium'")
            elif self.approval_score >= 70 and self.rejection_risk != "Low":
                raise ValueError("Score 70-100 must have rejection_risk='Low'")

        # 2. Human review rules
        needs_review = (
            bool(self.missing_info)
            or bool(self.wrong_or_mismatched)
            or self.approval_score < 70
            or self.rejection_risk == "No documents"
        )
        if needs_review and not self.human_review_required:
            raise ValueError("human_review_required must be True")
        if self.human_review_required and not self.human_review_reasons:
            raise ValueError("human_review_reasons required")
        return self

































    












































class State(TypedDict):
      messages: Annotated[List[BaseMessage], add_messages]
      decision: str
      RefindTopic: str
      TextDATA: Optional[TextAnalysis]
      ImageDATA: str
      Dataprocess: str
      Finaloutput: Optional[ClaimAnalysis]