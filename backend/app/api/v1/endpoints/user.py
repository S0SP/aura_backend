"""
AURA API v1 - User Management Endpoints
Handles user registration, authentication, and profile management
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime

from app.core.security import (
    get_current_user, create_access_token, 
    hash_password, verify_password, generate_api_key
)
from app.utils.id_generator import generate_user_id

router = APIRouter()


@router.post("/register")
async def register_user(
    email: str,
    password: str,
    name: Optional[str] = None,
    phone: Optional[str] = None
):
    """Register a new user."""
    user_id = generate_user_id()
    
    # TODO: Save to database
    
    return {
        "user_id": user_id,
        "email": email,
        "name": name,
        "created_at": datetime.utcnow().isoformat()
    }


@router.post("/login")
async def login(email: str, password: str):
    """Authenticate user and return access token."""
    # TODO: Verify credentials against database
    
    token = create_access_token({"sub": "user_123"})
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 1800
    }


@router.get("/me")
async def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    """Get current user's profile."""
    return {
        "user_id": current_user["user_id"],
        "email": "",
        "name": "",
        "created_at": "",
        "verification_count": 0
    }


@router.put("/me")
async def update_profile(
    name: Optional[str] = None,
    phone: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Update user profile."""
    return {"status": "updated", "user_id": current_user["user_id"]}


@router.post("/api-key")
async def create_api_key_endpoint(current_user: dict = Depends(get_current_user)):
    """Generate a new API key for the user."""
    api_key = generate_api_key()
    
    return {
        "api_key": api_key,
        "created_at": datetime.utcnow().isoformat(),
        "message": "Store this key securely. It won't be shown again."
    }


@router.get("/history")
async def get_verification_history(
    limit: int = 20,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """Get user's verification history."""
    return {
        "verifications": [],
        "total": 0,
        "limit": limit,
        "offset": offset
    }


@router.delete("/me")
async def delete_account(current_user: dict = Depends(get_current_user)):
    """Delete user account."""
    return {"status": "deleted", "message": "Account scheduled for deletion"}
