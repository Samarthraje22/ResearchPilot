from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ResearchQueryRequest(BaseModel):
    query: str = Field(..., description="Research question or topic to analyze")
    auto_ingest_arxiv: bool = Field(True, description="Whether to discover academic literature from arXiv REST API")
    sufficiency_threshold: float = Field(0.35, ge=0.1, le=0.9, description="Evidence sufficiency coverage threshold")
    selected_document_ids: Optional[List[str]] = Field(default=None, description="Optional list of selected user document IDs")


class DocumentMetadataSchema(BaseModel):
    id: str
    filename: str
    filepath: str
    pages: int
    size_bytes: int
    size_formatted: str
    upload_time: str
    selected: bool


class DocumentListResponse(BaseModel):
    documents: List[DocumentMetadataSchema]


class DocumentSelectRequest(BaseModel):
    selected_ids: List[str]


class SuggestedQuestionsResponse(BaseModel):
    document_id: str
    filename: str
    suggested_questions: List[str]


class RelatedPaperSchema(BaseModel):
    title: str
    authors: List[str]
    published_year: Optional[int] = None
    arxiv_id: str
    abstract: str
    relevance_score: int
    source_url: str
    reason_for_relevance: str


class RelatedPapersResponse(BaseModel):
    document_id: str
    document_title: str
    topic_profile: Dict[str, Any]
    related_papers: List[RelatedPaperSchema]


class EvidenceItem(BaseModel):
    source: str
    published_year: Optional[int] = None
    page: int
    section: str
    chunk_id: str
    content: str
    score: float
    citation_id: int


class ClaimVerificationItem(BaseModel):
    claim: str
    status: str  # 'SUPPORTED', 'PARTIALLY SUPPORTED', 'UNSUPPORTED'
    matched_citation_id: Optional[int] = None
    best_overlap: float


class VerificationReportSchema(BaseModel):
    total_claims: int
    supported_count: int
    partially_supported_count: int
    unsupported_count: int
    groundedness_score: float
    claims: List[ClaimVerificationItem]


class ResearchWorkflowResponse(BaseModel):
    topic: str
    execution_time_sec: float
    is_evidence_sufficient: bool
    sufficiency_details: Dict[str, Any]
    report: str
    verification_report: VerificationReportSchema
    evidence: List[EvidenceItem]
    sources: List[str]
    total_llm_calls: int
    llm_calls_by_stage: Dict[str, int]
    stage_latencies_sec: Dict[str, float]


class PDFUploadResponse(BaseModel):
    filename: str
    file_path: str
    chunks_created: int
    message: str


class APIErrorResponse(BaseModel):
    error: str
    detail: str


class ChatMessage(BaseModel):
    role: str = Field(..., description="Role: user or assistant")
    content: str = Field(..., description="Message content")


class FollowUpRequest(BaseModel):
    query: str = Field(..., description="Follow-up question")
    current_report: str = Field(default="", description="Existing research report text")
    evidence: Optional[List[Dict[str, Any]]] = Field(default=None, description="Retrieved evidence chunks")
    chat_history: Optional[List[ChatMessage]] = Field(default=[], description="Previous conversation turns")


class FollowUpResponse(BaseModel):
    answer: str
    citations_used: List[int]
    execution_time_sec: float
