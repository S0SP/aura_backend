"""
AURA Utility Module
Helper functions, validators, and generators
"""

from app.utils.helpers import (
    get_utc_now,
    get_utc_timestamp,
    clean_text,
    truncate_text,
    extract_urls,
    is_valid_url,
    safe_json_loads,
    safe_json_dumps
)
from app.utils.validators import (
    validate_claim_text,
    validate_url,
    validate_phone_number,
    validate_email,
    detect_platform,
    sanitize_input,
    ClaimPriority,
    SocialPlatform,
    ContentType
)
from app.utils.language_detector import (
    detect_language,
    get_language_name,
    is_language_supported,
    SupportedLanguage
)
from app.utils.id_generator import (
    generate_verification_id,
    generate_debate_session_id,
    generate_evidence_id,
    generate_user_id,
    generate_message_id,
    IDPrefix
)

__all__ = [
    # Helpers
    "get_utc_now",
    "get_utc_timestamp",
    "clean_text",
    "truncate_text",
    "extract_urls",
    "is_valid_url",
    "safe_json_loads",
    "safe_json_dumps",
    # Validators
    "validate_claim_text",
    "validate_url",
    "validate_phone_number",
    "validate_email",
    "detect_platform",
    "sanitize_input",
    "ClaimPriority",
    "SocialPlatform",
    "ContentType",
    # Language
    "detect_language",
    "get_language_name",
    "is_language_supported",
    "SupportedLanguage",
    # ID Generator
    "generate_verification_id",
    "generate_debate_session_id",
    "generate_evidence_id",
    "generate_user_id",
    "generate_message_id",
    "IDPrefix"
]
