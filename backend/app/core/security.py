"""
AURA Security Module
JWT Authentication and Security Utilities
"""

import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader

from app.core.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def create_access_token(
    data: Dict[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Dictionary containing claims to encode
        expires_delta: Optional expiration time delta
        
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create a refresh token with longer expiration."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })
    
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and verify a JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> Dict[str, Any]:
    """
    Dependency to get current user from JWT token.
    
    Returns:
        Dictionary containing user_id and token payload
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    payload = decode_token(token)
    user_id = payload.get("sub")
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing subject"
        )
    
    return {"user_id": user_id, "payload": payload}


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> Optional[Dict[str, Any]]:
    """
    Dependency to optionally get current user (for public endpoints).
    Returns None if no valid token is provided.
    """
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        payload = decode_token(token)
        user_id = payload.get("sub")
        if user_id:
            return {"user_id": user_id, "payload": payload}
    except HTTPException:
        pass
    
    return None


async def verify_api_key(
    api_key: Optional[str] = Depends(api_key_header)
) -> str:
    """
    Verify API key from header.
    
    Returns:
        The validated API key
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key missing"
        )
    
    # In production, validate against stored API keys in database
    # For now, we'll check if it starts with the expected prefix
    if not api_key.startswith("aura_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format"
        )
    
    return api_key


def generate_api_key() -> str:
    """Generate a new API key."""
    random_part = ''.join(
        secrets.choice(string.ascii_letters + string.digits) 
        for _ in range(32)
    )
    return f"aura_{random_part}"


def verify_webhook_signature(
    payload: bytes,
    signature: str,
    secret: str
) -> bool:
    """
    Verify webhook signature for Facebook/WhatsApp webhooks.
    
    Args:
        payload: Raw request body
        signature: X-Hub-Signature-256 header value
        secret: Webhook secret from Facebook
        
    Returns:
        True if signature is valid
    """
    import hmac
    import hashlib
    
    if not signature.startswith("sha256="):
        return False
    
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(
        signature[7:],  # Remove "sha256=" prefix
        expected_signature
    )


# Rate limiting helper (basic implementation)
class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, list] = {}
    
    def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed for the given identifier."""
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_seconds)
        
        if identifier not in self._requests:
            self._requests[identifier] = []
        
        # Clean old requests
        self._requests[identifier] = [
            ts for ts in self._requests[identifier]
            if ts > window_start
        ]
        
        if len(self._requests[identifier]) >= self.max_requests:
            return False
        
        self._requests[identifier].append(now)
        return True


# Default rate limiter instances
default_rate_limiter = RateLimiter(max_requests=100, window_seconds=60)
strict_rate_limiter = RateLimiter(max_requests=10, window_seconds=60)
