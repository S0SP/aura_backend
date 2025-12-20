"""
AURA Pydantic Models - Verification
MongoDB document model for verification results
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class VerdictType(str, Enum):
    """Possible verdict types."""
    TRUE = "TRUE"
    FALSE = "FALSE"
    MISLEADING = "MISLEADING"
    PARTIALLY_TRUE = "PARTIALLY_TRUE"
    UNVERIFIABLE = "UNVERIFIABLE"


class VerificationStatus(str, Enum):
    """Verification processing status."""
    QUEUED = "queued"
    EXTRACTING = "extracting"
    CLASSIFYING = "classifying"
    RETRIEVING_EVIDENCE = "retrieving_evidence"
    DEBATING = "debating"
    JUDGING = "judging"
    GENERATING_RESPONSE = "generating_response"
    COMPLETED = "completed"
    FAILED = "failed"


class QuickClassificationResult(BaseModel):
    """Quick classification from XLM-RoBERTa."""
    model: str = "xlm-roberta"
    verdict: VerdictType
    confidence: float = Field(..., ge=0.0, le=1.0)
    category: Optional[str] = None
    time_ms: int = 0


class EvidenceItem(BaseModel):
    """Single evidence item."""
    evidence_id: str
    source: str  # serp, pinecone, neo4j
    title: Optional[str] = None
    url: Optional[str] = None
    content_snippet: str
    relevance_score: float
    verdict_in_source: Optional[VerdictType] = None


class DebateSummary(BaseModel):
    """Summary of debate session."""
    session_id: str
    rounds_completed: int = 0
    for_total_score: float = 0.0
    against_total_score: float = 0.0
    winner: Optional[str] = None
    debate_duration_seconds: int = 0


class FinalVerdict(BaseModel):
    """Final verdict with confidence and reasoning."""
    verdict: VerdictType
    confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_level: str = "low"  # low, medium, high, definitive
    reasoning_summary: str = ""
    reasoning_detailed: Optional[str] = None
    key_points: List[str] = []
    dissenting_points: List[str] = []


class VerificationBase(BaseModel):
    """Base verification fields."""
    claim: str
    language: str = "en"


class VerificationCreate(VerificationBase):
    """Model for creating a verification."""
    claim_id: str
    user_id: Optional[str] = None
    priority: str = "normal"
    source_context: Optional[str] = None


class VerificationInDB(VerificationBase):
    """Verification as stored in MongoDB."""
    id: Optional[str] = Field(None, alias="_id")
    verification_id: str
    claim_id: str
    user_id: Optional[str] = None
    
    # Status
    status: VerificationStatus = VerificationStatus.QUEUED
    current_step: Optional[str] = None
    progress_percent: int = 0
    
    # Results
    quick_classification: Optional[QuickClassificationResult] = None
    evidence_items: List[EvidenceItem] = []
    debate_summary: Optional[DebateSummary] = None
    final_verdict: Optional[FinalVerdict] = None
    
    # Generated content
    citizen_response: Optional[str] = None
    journalist_response: Optional[str] = None
    audio_url: Optional[str] = None
    share_url: Optional[str] = None
    
    # Metrics
    processing_time_seconds: float = 0.0
    total_evidence_count: int = 0
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Error handling
    error_message: Optional[str] = None
    retry_count: int = 0
    
    class Config:
        populate_by_name = True
        use_enum_values = True


class VerificationUpdate(BaseModel):
    """Model for updating a verification."""
    status: Optional[VerificationStatus] = None
    current_step: Optional[str] = None
    progress_percent: Optional[int] = None
    error_message: Optional[str] = None


class VerificationResponse(BaseModel):
    """Verification response for API."""
    verification_id: str
    claim: str
    status: str
    verdict: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = None
    processing_time_seconds: float = 0.0
    created_at: datetime
    completed_at: Optional[datetime] = None
