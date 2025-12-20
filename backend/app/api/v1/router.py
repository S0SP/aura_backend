"""
AURA API v1 Main Router
Combines all endpoint routers for the API gateway
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    input,
    evidence,
    debate,
    output,
    trends,
    gov,
    user,
    webhooks
)

api_router = APIRouter()

# ==========================================
# Input Processing Module
# ==========================================
api_router.include_router(
    input.router,
    prefix="/input",
    tags=["Input Processing"]
)

# ==========================================
# Knowledge Core / Evidence Module
# ==========================================
api_router.include_router(
    evidence.router,
    prefix="/evidence",
    tags=["Knowledge Core"]
)

# ==========================================
# Debate Engine Module
# ==========================================
api_router.include_router(
    debate.router,
    prefix="/debate",
    tags=["Debate Engine"]
)

# ==========================================
# Output & Response Generation Module
# ==========================================
api_router.include_router(
    output.router,
    prefix="/output",
    tags=["Output Generation"]
)

# ==========================================
# Trend Analysis Module
# ==========================================
api_router.include_router(
    trends.router,
    prefix="/trends",
    tags=["Trend Analysis"]
)

# ==========================================
# Government Portal Module
# ==========================================
api_router.include_router(
    gov.router,
    prefix="/gov",
    tags=["Government Portal"]
)

# ==========================================
# User Management Module
# ==========================================
api_router.include_router(
    user.router,
    prefix="/user",
    tags=["User Management"]
)

# ==========================================
# Webhooks (WhatsApp, etc.)
# ==========================================
api_router.include_router(
    webhooks.router,
    prefix="/webhooks",
    tags=["Webhooks"]
)
