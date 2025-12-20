"""
AURA Pydantic Schemas - Input Processing
Request and response models for input endpoints
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class ClaimPriority(str, Enum):
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class ClaimSubmission(BaseModel):
    """Request model for submitting a text claim."""
    claim: str = Field(..., min_length=10, max_length=5000, description="The claim text to verify")
    language: Optional[str] = Field(None, description="ISO 639-1 language code, auto-detect if not provided")
    source_context: Optional[str] = Field(None, description="Where the user found this claim")
    priority: Optional[ClaimPriority] = Field(ClaimPriority.NORMAL)
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "claim": "5G towers spread COVID-19",
                "language": "en",
                "source_context": "WhatsApp forward",
                "priority": "normal",
                "metadata": {"user_location": "Mumbai, India"}
            }
        }


class ClaimResponse(BaseModel):
    """Response model for claim submission."""
    verification_id: str
    status: str
    estimated_time_seconds: int
    queue_position: int
    websocket_url: str
    created_at: str


class URLSubmission(BaseModel):
    """Request model for submitting a URL."""
    url: str = Field(..., description="Social media post URL")
    platform: Optional[str] = Field(None, description="Platform name, auto-detect if not provided")
    include_comments: bool = Field(False, description="Whether to analyze comments")
    priority: Optional[ClaimPriority] = Field(ClaimPriority.NORMAL)
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://twitter.com/user/status/123456789",
                "platform": "twitter",
                "include_comments": False
            }
        }


class URLResponse(BaseModel):
    """Response model for URL submission."""
    verification_id: str
    status: str
    extracted_claim: Optional[str]
    media_detected: List[str]
    estimated_time_seconds: int
    websocket_url: str


class ImageSubmission(BaseModel):
    """Request model for image submission metadata."""
    caption: Optional[str] = None
    priority: Optional[ClaimPriority] = ClaimPriority.NORMAL


class ImageResponse(BaseModel):
    """Response model for image submission."""
    verification_id: str
    status: str
    extracted_text: Optional[str]
    estimated_time_seconds: int
    websocket_url: str


class VerificationStep(BaseModel):
    """Current step in verification process."""
    name: str
    progress_percent: int
    current_agent: Optional[str] = None


class QuickClassification(BaseModel):
    """Quick classification result."""
    verdict: str
    confidence: float


class VerificationStatus(BaseModel):
    """Verification status response."""
    verification_id: str
    status: str  # queued, extracting, classifying, retrieving_evidence, debating, judging, generating_response, completed, failed
    current_step: Optional[VerificationStep] = None
    quick_classification: Optional[QuickClassification] = None
    estimated_completion: Optional[str] = None
    created_at: str
