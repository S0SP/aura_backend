"""
AURA ID Generator
Generates unique IDs for various entities with prefixes
"""

import secrets
import string
from datetime import datetime
from typing import Optional
import uuid


def generate_id(prefix: str = "", length: int = 12) -> str:
    """
    Generate a unique ID with optional prefix.
    
    Args:
        prefix: Optional prefix for the ID (e.g., "ver", "dbt")
        length: Length of the random part (default 12)
    
    Returns:
        Unique ID string
    
    Examples:
        generate_id("ver") -> "ver_abc123xyz789"
        generate_id("dbt") -> "dbt_def456uvw012"
        generate_id() -> "abc123xyz789"
    """
    chars = string.ascii_lowercase + string.digits
    random_part = ''.join(secrets.choice(chars) for _ in range(length))
    
    if prefix:
        return f"{prefix}_{random_part}"
    return random_part


def generate_verification_id() -> str:
    """Generate a verification ID (ver_xxxxxxxxxxxx)."""
    return generate_id("ver")


def generate_debate_session_id() -> str:
    """Generate a debate session ID (dbt_xxxxxxxxxxxx)."""
    return generate_id("dbt")


def generate_evidence_id() -> str:
    """Generate an evidence ID (evd_xxxxxxxxxxxx)."""
    return generate_id("evd")


def generate_user_id() -> str:
    """Generate a user ID (usr_xxxxxxxxxxxx)."""
    return generate_id("usr")


def generate_message_id() -> str:
    """Generate a message ID for WhatsApp/notifications (msg_xxxxxxxxxxxx)."""
    return generate_id("msg")


def generate_claim_id() -> str:
    """Generate a claim ID (clm_xxxxxxxxxxxx)."""
    return generate_id("clm")


def generate_round_id() -> str:
    """Generate a debate round ID (rnd_xxxxxxxxxxxx)."""
    return generate_id("rnd")


def generate_exchange_id() -> str:
    """Generate a debate exchange ID (exc_xxxxxxxxxxxx)."""
    return generate_id("exc")


def generate_api_key_id() -> str:
    """Generate an API key ID (key_xxxxxxxxxxxxxxxxxxxx)."""
    return generate_id("key", length=24)


def generate_session_id() -> str:
    """Generate a session ID (ses_xxxxxxxxxxxx)."""
    return generate_id("ses")


def generate_timestamp_id(prefix: str = "") -> str:
    """
    Generate an ID with timestamp component for ordering.
    
    Args:
        prefix: Optional prefix
        
    Returns:
        ID with format: prefix_YYYYMMDDHHMMSS_random
    
    Example:
        generate_timestamp_id("ver") -> "ver_20250120074500_abc123"
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    random_part = generate_id("", 6)
    
    if prefix:
        return f"{prefix}_{timestamp}_{random_part}"
    return f"{timestamp}_{random_part}"


def generate_uuid() -> str:
    """Generate a standard UUID4."""
    return str(uuid.uuid4())


def generate_short_uuid() -> str:
    """Generate a short UUID (first 8 chars of UUID4)."""
    return str(uuid.uuid4())[:8]


def generate_webhook_id() -> str:
    """Generate a webhook event ID (whk_xxxxxxxxxxxx)."""
    return generate_id("whk")


def validate_id_format(id_str: str, expected_prefix: Optional[str] = None) -> bool:
    """
    Validate if a string matches the expected ID format.
    
    Args:
        id_str: The ID string to validate
        expected_prefix: Optional expected prefix
        
    Returns:
        True if valid, False otherwise
    """
    if not id_str or not isinstance(id_str, str):
        return False
    
    if expected_prefix:
        if not id_str.startswith(f"{expected_prefix}_"):
            return False
        # Check random part
        random_part = id_str[len(expected_prefix) + 1:]
        if len(random_part) < 6:
            return False
    else:
        if "_" in id_str:
            parts = id_str.split("_", 1)
            if len(parts[1]) < 6:
                return False
    
    return True


# ID type constants for reference
class IDPrefix:
    """Constants for ID prefixes."""
    VERIFICATION = "ver"
    DEBATE = "dbt"
    EVIDENCE = "evd"
    USER = "usr"
    MESSAGE = "msg"
    CLAIM = "clm"
    ROUND = "rnd"
    EXCHANGE = "exc"
    SESSION = "ses"
    WEBHOOK = "whk"
    API_KEY = "key"
