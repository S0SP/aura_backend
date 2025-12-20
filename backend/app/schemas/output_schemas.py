"""
AURA Pydantic Schemas - Output Generation
Request and response models for output endpoints
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class VerdictInfo(BaseModel):
    """Verdict information."""
    result: str  # TRUE, FALSE, MISLEADING, UNVERIFIABLE
    confidence: float
    confidence_level: str  # low, medium, high, definitive


class QuickClassificationResult(BaseModel):
    """Quick classification result."""
    model: str
    verdict: str
    confidence: float
    time_ms: int


class DebateSummaryOutput(BaseModel):
    """Debate summary for output."""
    session_id: str
    rounds_completed: int
    final_scores: Dict[str, float]
    winner: str
    debate_duration_seconds: int


class ReasoningOutput(BaseModel):
    """Reasoning details."""
    summary: str
    detailed: str
    key_points: List[str]


class EvidenceSource(BaseModel):
    """Evidence source details."""
    source: str
    title: Optional[str] = None
    url: Optional[str] = None
    relevance: str
    quote: Optional[str] = None


class EvidenceOutput(BaseModel):
    """Evidence summary."""
    primary_sources: List[EvidenceSource]
    supporting_sources: List[EvidenceSource]
    total_sources: int


class MetadataOutput(BaseModel):
    """Verification metadata."""
    processing_time_seconds: float
    created_at: str
    completed_at: str
    share_url: str


class VerdictResponse(BaseModel):
    """Complete verdict response."""
    verification_id: str
    claim: str
    claim_language: str
    verdict: VerdictInfo
    quick_classification: QuickClassificationResult
    debate_summary: DebateSummaryOutput
    reasoning: ReasoningOutput
    evidence: EvidenceOutput
    metadata: MetadataOutput


class CitizenResponse(BaseModel):
    """Citizen-friendly response."""
    verification_id: str
    verdict_emoji: str  # ✅ ❌ ⚠️ ❓
    verdict_text: str
    summary: str
    explanation: str
    recommendations: List[str]
    share_url: str
    language: str


class Citation(BaseModel):
    """Citation for journalist response."""
    source: str
    title: str
    url: str
    accessed_date: str


class JournalistResponse(BaseModel):
    """Journalist-friendly response."""
    verification_id: str
    headline: str
    verdict: str
    summary: str
    methodology: str
    evidence_summary: str
    citations: List[Citation]
    expert_quotes: List[str]
    full_report_markdown: str


class GovernmentResponse(BaseModel):
    """Government CAP format response."""
    verification_id: str
    cap_identifier: str
    sender: str
    sent: str
    status: str
    msg_type: str
    scope: str
    category: str
    event: str
    urgency: str
    severity: str
    certainty: str
    headline: str
    description: str
    instruction: str
    web_link: str


class AudioGenerationRequest(BaseModel):
    """Request for audio generation."""
    verification_id: str
    language: str = "en"
    voice_id: Optional[str] = None
    response_type: str = "citizen"  # citizen, journalist, full


class ShareResponse(BaseModel):
    """Response for share link generation."""
    verification_id: str
    share_url: str
    embed_code: str
    qr_code_url: str
    expires_at: Optional[str] = None
