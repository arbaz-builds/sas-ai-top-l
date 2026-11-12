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

class StrictBaseModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True
    )


# -----------------------------
# SOURCE / EVIDENCE
# -----------------------------

class Evidence(StrictBaseModel):
    source_id: str = Field(
        description="Unique source/document identifier"
    )

    document_name: Optional[str] = None

    page_number: Optional[int] = Field(
        default=None,
        ge=1
    )

    quote: str = Field(
        min_length=1,
        description="Exact supporting text from source"
    )


# -----------------------------
# EXTRACTED FACTS
# -----------------------------

class ClaimFact(StrictBaseModel):
    fact_id: str

    category: Literal[
        "POLICYHOLDER",
        "POLICY",
        "CLAIM",
        "INCIDENT",
        "VEHICLE",
        "THIRD_PARTY",
        "DAMAGE",
        "REPAIR_ESTIMATE",
        "FINANCIAL",
        "OTHER"
    ]

    field_name: str

    value: str

    confidence: float = Field(
        ge=0,
        le=1
    )

    evidence: list[Evidence] = Field(
        min_length=1
    )


# -----------------------------
# DOCUMENT INVENTORY
# -----------------------------

class DocumentRecord(StrictBaseModel):
    document_type: str

    status: Literal[
        "DECLARED_SUBMITTED",
        "CONTENT_AVAILABLE",
        "DECLARED_SUBMITTED_NOT_VERIFIED",
        "NOT_DECLARED",
        "UNREADABLE",
        "IRRELEVANT"
    ]

    source_ids: list[str] = Field(
        default_factory=list
    )

    notes: Optional[str] = None


# -----------------------------
# ISSUE DETECTION
# -----------------------------

class ClaimIssue(StrictBaseModel):
    issue_id: str

    category: Literal[
        "DATA_CONFLICT",
        "MISSING_INFORMATION",
        "DUPLICATE_DOCUMENT",
        "FINANCIAL_INCONSISTENCY",
        "DATE_INCONSISTENCY",
        "IDENTITY_INCONSISTENCY",
        "DOCUMENT_QUALITY",
        "OTHER"
    ]

    severity: Literal[
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL"
    ]

    description: str

    affected_fields: list[str] = Field(
        default_factory=list
    )

    evidence: list[Evidence] = Field(
        default_factory=list
    )

    recommended_action: Optional[str] = None


# -----------------------------
# MISSING INFORMATION
# -----------------------------

class MissingInformation(StrictBaseModel):
    field_name: str

    reason: str

    status: Literal[
        "NOT_FOUND",
        "DECLARED_BUT_NOT_AVAILABLE",
        "UNREADABLE",
        "INCOMPLETE"
    ]

    importance: Literal[
        "LOW",
        "MEDIUM",
        "HIGH"
    ]

    related_document_type: Optional[str] = None


# -----------------------------
# FINANCIAL VALIDATION
# -----------------------------

class FinancialCheck(StrictBaseModel):
    calculation_name: str

    expected_value: Optional[float] = None

    extracted_value: Optional[float] = None

    difference: Optional[float] = None

    status: Literal[
        "PASS",
        "FAIL",
        "NOT_CHECKED",
        "INSUFFICIENT_DATA"
    ]

    explanation: str


# -----------------------------
# CROSS DOCUMENT VERIFICATION
# -----------------------------

class CrossDocumentVerification(StrictBaseModel):
    status: Literal[
        "MATCH",
        "MISMATCH",
        "PARTIALLY_VERIFIED",
        "NOT_VERIFIED"
    ]

    independent_documents_compared: int = Field(
        ge=0
    )

    matched_fields: list[str] = Field(
        default_factory=list
    )

    mismatched_fields: list[str] = Field(
        default_factory=list
    )

    explanation: str

    @model_validator(mode="after")
    def validate_verification(self):
        if (
            self.independent_documents_compared < 2
            and self.status in ["MATCH", "MISMATCH"]
        ):
            raise ValueError(
                "MATCH/MISMATCH requires at least two independent documents"
            )

        return self


# -----------------------------
# SUMMARY
# -----------------------------

class ClaimSummary(StrictBaseModel):
    total_facts: int = Field(ge=0)

    total_issues: int = Field(ge=0)

    high_severity_issues: int = Field(ge=0)

    critical_issues: int = Field(ge=0)

    missing_fields: int = Field(ge=0)

    documents_found: int = Field(ge=0)

    documents_declared: int = Field(ge=0)

    financial_checks_passed: int = Field(ge=0)

    financial_checks_failed: int = Field(ge=0)


# -----------------------------
# FINAL CLAIM ANALYSIS
# -----------------------------

class TEXTAnalysis(StrictBaseModel):
    schema_version: str = "1.0"

    analysis_status: Literal[
        "SUCCESS",
        "PARTIAL",
        "FAILED"
    ]

    facts: list[ClaimFact]

    documents: list[DocumentRecord]

    issues: list[ClaimIssue]

    missing_information: list[MissingInformation]

    financial_checks: list[FinancialCheck]

    cross_document_verification: CrossDocumentVerification

    overall_summary: ClaimSummary

    @model_validator(mode="after")
    def validate_summary_counts(self):

        summary = self.overall_summary

        if summary.total_facts != len(self.facts):
            raise ValueError("total_facts count mismatch")

        if summary.total_issues != len(self.issues):
            raise ValueError("total_issues count mismatch")

        if summary.missing_fields != len(self.missing_information):
            raise ValueError("missing_fields count mismatch")

        high_count = sum(
            issue.severity == "HIGH"
            for issue in self.issues
        )

        critical_count = sum(
            issue.severity == "CRITICAL"
            for issue in self.issues
        )

        if summary.high_severity_issues != high_count:
            raise ValueError("high_severity_issues count mismatch")

        if summary.critical_issues != critical_count:
            raise ValueError("critical_issues count mismatch")

        return self






























































































class State(TypedDict):
      messages: Annotated[List[BaseMessage], add_messages]
      decision: str
      RefindTopic: str
      TextDATA: Optional[TEXTAnalysis]
      ImageDATA: str
      Dataprocess: str
      Finaloutput: Optional[ClaimAnalysis]