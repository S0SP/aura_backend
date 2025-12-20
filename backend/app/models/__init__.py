"""
AURA Models Package
Database document models for MongoDB
"""

from app.models.claim import (
    ClaimStatus,
    ClaimPriority,
    ClaimSource,
    ClaimBase,
    ClaimCreate,
    ClaimInDB,
    ClaimResponse
)
from app.models.verification import (
    VerdictType,
    VerificationStatus,
    QuickClassificationResult,
    EvidenceItem,
    DebateSummary,
    FinalVerdict,
    VerificationCreate,
    VerificationInDB,
    VerificationUpdate,
    VerificationResponse
)
from app.models.debate import (
    DebateStatus,
    AgentRole,
    Exchange,
    RoundScore,
    DebateRound,
    DebateConfig,
    DebateInDB,
    DebateCreate
)
from app.models.evidence import (
    EvidenceSource,
    EvidenceType,
    EvidenceInDB,
    EvidenceCreate,
    EvidenceSearchResult,
    FactCategory,
    FactInDB,
    FactCreate
)
from app.models.user import (
    UserRole,
    UserStatus,
    UserPreferences,
    UserStats,
    UserInDB,
    UserCreate,
    UserUpdate,
    UserResponse,
    TokenData
)

__all__ = [
    # Claim
    "ClaimStatus", "ClaimPriority", "ClaimSource",
    "ClaimBase", "ClaimCreate", "ClaimInDB", "ClaimResponse",
    # Verification
    "VerdictType", "VerificationStatus", "QuickClassificationResult",
    "EvidenceItem", "DebateSummary", "FinalVerdict",
    "VerificationCreate", "VerificationInDB", "VerificationUpdate", "VerificationResponse",
    # Debate
    "DebateStatus", "AgentRole", "Exchange", "RoundScore",
    "DebateRound", "DebateConfig", "DebateInDB", "DebateCreate",
    # Evidence
    "EvidenceSource", "EvidenceType", "EvidenceInDB", "EvidenceCreate",
    "EvidenceSearchResult", "FactCategory", "FactInDB", "FactCreate",
    # User
    "UserRole", "UserStatus", "UserPreferences", "UserStats",
    "UserInDB", "UserCreate", "UserUpdate", "UserResponse", "TokenData"
]
