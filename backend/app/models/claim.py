"""
AURA Pydantic Models - Claim
MongoDB document model for claims
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class ClaimStatus(str, Enum):
    """Claim processing status."""
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ClaimPriority(str, Enum):
    """Claim priority levels."""
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class ClaimSource(str, Enum):
    """Source of the claim."""
    API = "api"
    WHATSAPP = "whatsapp"
    WEB = "web"
    MOBILE = "mobile"
    GOVERNMENT = "government"


class ClaimBase(BaseModel):
    """Base claim fields."""
    claim_text: str = Field(..., min_length=10, max_length=5000)
    language: str = Field(default="en")
    source_context: Optional[str] = None
    priority: ClaimPriority = ClaimPriority.NORMAL
    source: ClaimSource = ClaimSource.API
    metadata: Optional[Dict[str, Any]] = None


class ClaimCreate(ClaimBase):
    """Model for creating a new claim."""
    user_id: Optional[str] = None
    whatsapp_from: Optional[str] = None


class ClaimInDB(ClaimBase):
    """Claim as stored in MongoDB."""
    id: Optional[str] = Field(None, alias="_id")
    claim_id: str
    user_id: Optional[str] = None
    whatsapp_from: Optional[str] = None
    status: ClaimStatus = ClaimStatus.PENDING
    verification_id: Optional[str] = None
    
    # Classification results
    quick_classification: Optional[Dict[str, Any]] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        populate_by_name = True
        use_enum_values = True


class ClaimResponse(BaseModel):
    """Claim response for API."""
    claim_id: str
    claim_text: str
    status: str
    verification_id: Optional[str] = None
    created_at: datetime
