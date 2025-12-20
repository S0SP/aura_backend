"""
AURA Schemas Module
Pydantic models for request/response validation
"""

from app.schemas.input_schemas import (
    ClaimSubmission,
    ClaimResponse,
    URLSubmission,
    URLResponse,
    ImageResponse,
    VerificationStatus
)
from app.schemas.evidence_schemas import (
    EvidenceSearchRequest,
    EvidenceSearchResponse,
    SerpSearchRequest,
    SerpSearchResponse,
    VectorSearchResponse,
    GraphQueryResponse
)
from app.schemas.debate_schemas import (
    DebateInitRequest,
    DebateInitResponse,
    DebateSessionStatus,
    DebateRoundDetails,
    JudgeEvaluationResponse,
    DebateTranscript
)
from app.schemas.output_schemas import (
    VerdictResponse,
    CitizenResponse,
    JournalistResponse,
    GovernmentResponse
)
from app.schemas.common_schemas import (
    VerdictType,
    StatusType,
    BaseResponse,
    ErrorResponse,
    PaginatedResponse,
    WebSocketMessage
)

__all__ = [
    # Input
    "ClaimSubmission",
    "ClaimResponse",
    "URLSubmission",
    "URLResponse",
    "ImageResponse",
    "VerificationStatus",
    # Evidence
    "EvidenceSearchRequest",
    "EvidenceSearchResponse",
    "SerpSearchRequest",
    "SerpSearchResponse",
    "VectorSearchResponse",
    "GraphQueryResponse",
    # Debate
    "DebateInitRequest",
    "DebateInitResponse",
    "DebateSessionStatus",
    "DebateRoundDetails",
    "JudgeEvaluationResponse",
    "DebateTranscript",
    # Output
    "VerdictResponse",
    "CitizenResponse",
    "JournalistResponse",
    "GovernmentResponse",
    # Common
    "VerdictType",
    "StatusType",
    "BaseResponse",
    "ErrorResponse",
    "PaginatedResponse",
    "WebSocketMessage"
]
