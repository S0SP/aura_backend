"""
AURA Pydantic Schemas - Common/Shared
Common models used across multiple modules
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
    UNVERIFIABLE = "UNVERIFIABLE"
    PARTIALLY_TRUE = "PARTIALLY_TRUE"


class ConfidenceLevel(str, Enum):
    """Confidence levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    DEFINITIVE = "definitive"


class StatusType(str, Enum):
    """Verification status types."""
    QUEUED = "queued"
    EXTRACTING = "extracting"
    CLASSIFYING = "classifying"
    RETRIEVING_EVIDENCE = "retrieving_evidence"
    DEBATING = "debating"
    JUDGING = "judging"
    GENERATING_RESPONSE = "generating_response"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BaseResponse(BaseModel):
    """Base response model."""
    success: bool = True
    message: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ErrorResponse(BaseModel):
    """Error response model."""
    success: bool = False
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class PaginatedResponse(BaseModel):
    """Paginated response model."""
    items: List[Any]
    total: int
    limit: int
    offset: int
    has_more: bool


class HealthCheck(BaseModel):
    """Health check response."""
    status: str
    app: str
    version: str
    debug: bool
    dependencies: Optional[Dict[str, bool]] = None


class WebSocketMessage(BaseModel):
    """WebSocket message format."""
    type: str  # status_update, debate_exchange, verdict, error
    verification_id: str
    data: Dict[str, Any]
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class QueueItem(BaseModel):
    """Queue item for verification processing."""
    verification_id: str
    claim: str
    content_type: str
    priority: str
    created_at: str
    metadata: Optional[Dict[str, Any]] = None
