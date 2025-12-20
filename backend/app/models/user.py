"""
AURA Pydantic Models - User
MongoDB document model for users
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    """User roles."""
    CITIZEN = "citizen"
    JOURNALIST = "journalist"
    GOVERNMENT = "government"
    ADMIN = "admin"


class UserStatus(str, Enum):
    """User account status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class UserPreferences(BaseModel):
    """User preferences."""
    language: str = "en"
    notification_email: bool = True
    notification_whatsapp: bool = False
    response_format: str = "citizen"  # citizen, journalist, detailed
    audio_enabled: bool = False


class UserStats(BaseModel):
    """User usage statistics."""
    total_verifications: int = 0
    verifications_this_month: int = 0
    last_verification_at: Optional[datetime] = None
    api_calls_today: int = 0


class UserInDB(BaseModel):
    """User as stored in MongoDB."""
    id: Optional[str] = Field(None, alias="_id")
    user_id: str
    
    # Authentication
    email: Optional[str] = None
    password_hash: Optional[str] = None
    phone: Optional[str] = None
    whatsapp_verified: bool = False
    
    # Profile
    name: Optional[str] = None
    organization: Optional[str] = None
    role: UserRole = UserRole.CITIZEN
    
    # Status
    status: UserStatus = UserStatus.ACTIVE
    email_verified: bool = False
    
    # API access
    api_key_hash: Optional[str] = None
    api_key_created_at: Optional[datetime] = None
    
    # Preferences
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    
    # Stats
    stats: UserStats = Field(default_factory=UserStats)
    
    # Rate limiting
    rate_limit_tier: str = "free"  # free, basic, premium
    daily_limit: int = 50
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    
    class Config:
        populate_by_name = True
        use_enum_values = True


class UserCreate(BaseModel):
    """Model for creating a user."""
    email: Optional[str] = None
    password: Optional[str] = None
    phone: Optional[str] = None
    name: Optional[str] = None
    role: UserRole = UserRole.CITIZEN


class UserUpdate(BaseModel):
    """Model for updating a user."""
    name: Optional[str] = None
    phone: Optional[str] = None
    organization: Optional[str] = None
    preferences: Optional[UserPreferences] = None


class UserResponse(BaseModel):
    """User response for API (excludes sensitive data)."""
    user_id: str
    email: Optional[str] = None
    name: Optional[str] = None
    role: str
    status: str
    created_at: datetime
    stats: UserStats


class TokenData(BaseModel):
    """JWT token payload data."""
    user_id: str
    email: Optional[str] = None
    role: str = "citizen"
    exp: Optional[datetime] = None
