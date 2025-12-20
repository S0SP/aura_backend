"""
AURA Validators
Input validation utilities for claims, URLs, and other data
"""

import re
from typing import Optional, Tuple, List
from urllib.parse import urlparse
from pydantic import BaseModel, validator, field_validator
from enum import Enum


class ClaimPriority(str, Enum):
    """Claim verification priority levels."""
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class SocialPlatform(str, Enum):
    """Supported social media platforms."""
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    LINKEDIN = "linkedin"
    REDDIT = "reddit"
    UNKNOWN = "unknown"


class ContentType(str, Enum):
    """Types of content that can be verified."""
    TEXT = "text"
    IMAGE = "image"
    URL = "url"
    WHATSAPP = "whatsapp"
    MIXED = "mixed"


# Platform URL patterns
PLATFORM_PATTERNS = {
    SocialPlatform.TWITTER: [
        r'(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)/\w+/status/\d+',
        r'(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)/\w+',
    ],
    SocialPlatform.FACEBOOK: [
        r'(?:https?://)?(?:www\.)?facebook\.com/.+',
        r'(?:https?://)?(?:www\.)?fb\.com/.+',
    ],
    SocialPlatform.INSTAGRAM: [
        r'(?:https?://)?(?:www\.)?instagram\.com/p/[\w-]+',
        r'(?:https?://)?(?:www\.)?instagram\.com/reel/[\w-]+',
    ],
    SocialPlatform.YOUTUBE: [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+',
        r'(?:https?://)?(?:www\.)?youtu\.be/[\w-]+',
    ],
    SocialPlatform.TIKTOK: [
        r'(?:https?://)?(?:www\.)?tiktok\.com/@[\w.]+/video/\d+',
        r'(?:https?://)?(?:vm\.)?tiktok\.com/[\w-]+',
    ],
    SocialPlatform.LINKEDIN: [
        r'(?:https?://)?(?:www\.)?linkedin\.com/posts/.+',
        r'(?:https?://)?(?:www\.)?linkedin\.com/feed/update/.+',
    ],
    SocialPlatform.REDDIT: [
        r'(?:https?://)?(?:www\.)?reddit\.com/r/\w+/comments/\w+',
    ],
}


def validate_claim_text(text: str) -> Tuple[bool, Optional[str]]:
    """
    Validate claim text.
    
    Args:
        text: Claim text to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not text:
        return False, "Claim text is required"
    
    if len(text.strip()) < 10:
        return False, "Claim must be at least 10 characters"
    
    if len(text) > 5000:
        return False, "Claim must be less than 5000 characters"
    
    # Check for minimum word count
    words = text.split()
    if len(words) < 3:
        return False, "Claim must contain at least 3 words"
    
    return True, None


def validate_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate URL format.
    
    Args:
        url: URL to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url:
        return False, "URL is required"
    
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            return False, "Invalid URL format"
        
        if result.scheme not in ['http', 'https']:
            return False, "URL must use http or https scheme"
        
        return True, None
    except Exception:
        return False, "Invalid URL"


def detect_platform(url: str) -> SocialPlatform:
    """
    Detect social media platform from URL.
    
    Args:
        url: URL to analyze
        
    Returns:
        Detected platform or UNKNOWN
    """
    for platform, patterns in PLATFORM_PATTERNS.items():
        for pattern in patterns:
            if re.match(pattern, url, re.IGNORECASE):
                return platform
    
    return SocialPlatform.UNKNOWN


def validate_phone_number(phone: str) -> Tuple[bool, Optional[str]]:
    """
    Validate phone number format.
    
    Args:
        phone: Phone number to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not phone:
        return False, "Phone number is required"
    
    # Remove all non-digit characters except +
    cleaned = re.sub(r'[^\d+]', '', phone)
    
    # Check length (international format)
    if len(cleaned) < 10 or len(cleaned) > 15:
        return False, "Invalid phone number length"
    
    # Check format
    if not re.match(r'^\+?\d{10,15}$', cleaned):
        return False, "Invalid phone number format"
    
    return True, None


def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """
    Validate email format.
    
    Args:
        email: Email to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email:
        return False, "Email is required"
    
    email_pattern = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )
    
    if not email_pattern.match(email):
        return False, "Invalid email format"
    
    return True, None


def validate_language_code(code: str) -> Tuple[bool, Optional[str]]:
    """
    Validate ISO 639-1 language code.
    
    Args:
        code: Language code to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Common supported languages
    supported_languages = {
        'en', 'hi', 'mr', 'ta', 'te', 'bn', 'gu', 'kn', 'ml', 'pa',
        'es', 'fr', 'de', 'pt', 'ar', 'zh', 'ja', 'ko', 'ru'
    }
    
    if not code:
        return True, None  # Auto-detect if not provided
    
    if code.lower() not in supported_languages:
        return False, f"Unsupported language code: {code}"
    
    return True, None


def validate_priority(priority: str) -> Tuple[bool, Optional[str]]:
    """
    Validate claim priority level.
    
    Args:
        priority: Priority value to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    valid_priorities = [p.value for p in ClaimPriority]
    
    if priority not in valid_priorities:
        return False, f"Priority must be one of: {', '.join(valid_priorities)}"
    
    return True, None


def validate_image_content_type(content_type: str) -> Tuple[bool, Optional[str]]:
    """
    Validate image content type.
    
    Args:
        content_type: MIME type to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    valid_types = {
        'image/jpeg', 'image/jpg', 'image/png', 
        'image/gif', 'image/webp', 'image/bmp'
    }
    
    if content_type not in valid_types:
        return False, f"Unsupported image type: {content_type}"
    
    return True, None


def validate_verification_id(vid: str) -> Tuple[bool, Optional[str]]:
    """
    Validate verification ID format.
    
    Args:
        vid: Verification ID to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not vid:
        return False, "Verification ID is required"
    
    if not vid.startswith("ver_"):
        return False, "Invalid verification ID format"
    
    # Check random part length (after ver_)
    if len(vid) < 16:
        return False, "Invalid verification ID length"
    
    return True, None


def validate_debate_session_id(sid: str) -> Tuple[bool, Optional[str]]:
    """
    Validate debate session ID format.
    
    Args:
        sid: Session ID to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not sid:
        return False, "Session ID is required"
    
    if not sid.startswith("dbt_"):
        return False, "Invalid session ID format"
    
    if len(sid) < 16:
        return False, "Invalid session ID length"
    
    return True, None


def sanitize_input(text: str) -> str:
    """
    Sanitize user input to prevent injection attacks.
    
    Args:
        text: Text to sanitize
        
    Returns:
        Sanitized text
    """
    if not text:
        return ""
    
    # Remove null bytes
    text = text.replace('\x00', '')
    
    # Remove control characters (except newline, tab)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    
    return text.strip()


def extract_claims_from_text(text: str) -> List[str]:
    """
    Extract potential claims from a longer text.
    
    Args:
        text: Text to extract claims from
        
    Returns:
        List of potential claims
    """
    # Split by sentence-ending punctuation
    sentences = re.split(r'[.!?]+', text)
    
    claims = []
    for sentence in sentences:
        sentence = sentence.strip()
        # Filter out very short sentences
        if len(sentence) > 20 and len(sentence.split()) >= 4:
            claims.append(sentence)
    
    return claims
