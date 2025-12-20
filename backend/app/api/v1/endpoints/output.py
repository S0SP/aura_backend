"""
AURA API v1 - Output Generation Endpoints
Generates citizen/journalist responses, audio, and share links
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Response
from datetime import datetime

from app.core.logging import logger
from app.services.output.response_generator import response_generator
from app.services.output.audio_service import audio_service
from app.services.output.share_service import share_service
from app.services.verification_service import verification_service
from app.schemas.output_schemas import (
    VerdictResponse, CitizenResponse, JournalistResponse,
    GovernmentResponse, AudioRequest, AudioResponse,
    ShareRequest, ShareResponse
)

router = APIRouter()


# ===========================================
# GET /api/v1/output/verdict/{verification_id}
# ===========================================
@router.get("/verdict/{verification_id}", response_model=VerdictResponse)
async def get_verdict(verification_id: str):
    """
    Get the final verdict for a verification.
    
    Returns verdict, confidence, and summary.
    """
    verification = await verification_service.get_by_id(verification_id)
    if not verification:
        raise HTTPException(status_code=404, detail="Verification not found")
    
    if not verification.final_verdict:
        raise HTTPException(status_code=400, detail="Verification not yet complete")
    
    return VerdictResponse(
        verification_id=verification_id,
        verdict=verification.final_verdict.get("verdict", "UNVERIFIABLE"),
        confidence=verification.final_verdict.get("confidence", 0.5),
        confidence_level=verification.final_verdict.get("confidence_level", "low"),
        reasoning_summary=verification.final_verdict.get("reasoning_summary", ""),
        debated=bool(verification.debate_summary),
        processing_time_seconds=verification.processing_time_seconds,
        completed_at=verification.completed_at.isoformat() if verification.completed_at else None
    )


# ===========================================
# GET /api/v1/output/citizen/{verification_id}
# ===========================================
@router.get("/citizen/{verification_id}", response_model=CitizenResponse)
async def get_citizen_response(
    verification_id: str,
    language: str = Query("en", description="Response language code")
):
    """
    Get citizen-friendly response for a verification.
    
    Simple, accessible language with clear verdict and action.
    """
    verification = await verification_service.get_by_id(verification_id)
    if not verification:
        raise HTTPException(status_code=404, detail="Verification not found")
    
    if not verification.final_verdict:
        raise HTTPException(status_code=400, detail="Verification not yet complete")
    
    verdict = verification.final_verdict
    
    response = await response_generator.generate_citizen_response(
        claim=verification.claim,
        verdict=verdict.get("verdict", "UNVERIFIABLE"),
        confidence=verdict.get("confidence", 0.5),
        reasoning_summary=verdict.get("reasoning_summary", ""),
        key_points=verdict.get("key_points", []),
        language=language
    )
    
    return CitizenResponse(
        verification_id=verification_id,
        **response
    )


# ===========================================
# GET /api/v1/output/journalist/{verification_id}
# ===========================================
@router.get("/journalist/{verification_id}", response_model=JournalistResponse)
async def get_journalist_response(
    verification_id: str,
    language: str = Query("en", description="Response language code")
):
    """
    Get detailed journalist report for a verification.
    
    Comprehensive analysis with evidence citations.
    """
    verification = await verification_service.get_by_id(verification_id)
    if not verification:
        raise HTTPException(status_code=404, detail="Verification not found")
    
    if not verification.final_verdict:
        raise HTTPException(status_code=400, detail="Verification not yet complete")
    
    verdict = verification.final_verdict
    
    response = await response_generator.generate_journalist_response(
        claim=verification.claim,
        verdict=verdict.get("verdict", "UNVERIFIABLE"),
        confidence=verdict.get("confidence", 0.5),
        reasoning_detailed=verdict.get("reasoning_detailed", verdict.get("reasoning_summary", "")),
        evidence_items=verification.evidence_items,
        debate_summary=verification.debate_summary.model_dump() if verification.debate_summary else None,
        language=language
    )
    
    return JournalistResponse(
        verification_id=verification_id,
        **response
    )


# ===========================================
# GET /api/v1/output/government/{verification_id}
# ===========================================
@router.get("/government/{verification_id}", response_model=GovernmentResponse)
async def get_government_response(
    verification_id: str,
    severity: str = Query("medium", description="Alert severity"),
    regions: str = Query(None, description="Comma-separated affected regions")
):
    """
    Get CAP-format government alert for a verification.
    
    Suitable for integration with government alert systems.
    """
    verification = await verification_service.get_by_id(verification_id)
    if not verification:
        raise HTTPException(status_code=404, detail="Verification not found")
    
    if not verification.final_verdict:
        raise HTTPException(status_code=400, detail="Verification not yet complete")
    
    verdict = verification.final_verdict
    affected_regions = regions.split(",") if regions else None
    
    response = await response_generator.generate_government_alert(
        claim=verification.claim,
        verdict=verdict.get("verdict", "UNVERIFIABLE"),
        confidence=verdict.get("confidence", 0.5),
        severity=severity,
        affected_regions=affected_regions,
        category=verification.quick_classification.get("category", "other") if verification.quick_classification else "other"
    )
    
    return GovernmentResponse(
        verification_id=verification_id,
        **response
    )


# ===========================================
# POST /api/v1/output/audio
# ===========================================
@router.post("/audio", response_model=AudioResponse)
async def generate_audio(request: AudioRequest):
    """
    Generate audio version of verification result.
    
    Supports multiple Indian languages.
    """
    verification = await verification_service.get_by_id(request.verification_id)
    if not verification:
        raise HTTPException(status_code=404, detail="Verification not found")
    
    # Generate citizen response text for TTS
    citizen_response = await response_generator.generate_citizen_response(
        claim=verification.claim,
        verdict=verification.final_verdict.get("verdict", "UNVERIFIABLE") if verification.final_verdict else "UNVERIFIABLE",
        confidence=verification.final_verdict.get("confidence", 0.5) if verification.final_verdict else 0.5,
        reasoning_summary=verification.final_verdict.get("reasoning_summary", "") if verification.final_verdict else "",
        language=request.language
    )
    
    # Generate audio
    audio_result = await audio_service.generate_audio(
        text=citizen_response.get("response_text", ""),
        language=request.language,
        voice_gender=request.voice_gender,
        speaking_rate=request.speaking_rate
    )
    
    return AudioResponse(
        verification_id=request.verification_id,
        **audio_result
    )


# ===========================================
# GET /api/v1/output/audio/{audio_id}
# ===========================================
@router.get("/audio/{audio_id}")
async def get_audio_file(audio_id: str):
    """
    Get generated audio file.
    """
    audio_content = await audio_service.get_audio_file(audio_id)
    if not audio_content:
        raise HTTPException(status_code=404, detail="Audio not found")
    
    return Response(
        content=audio_content,
        media_type="audio/mpeg",
        headers={"Content-Disposition": f"attachment; filename={audio_id}.mp3"}
    )


# ===========================================
# GET /api/v1/output/audio/languages
# ===========================================
@router.get("/audio/languages")
async def get_supported_languages():
    """
    Get list of supported TTS languages.
    """
    return {
        "languages": audio_service.get_supported_languages(),
        "default": "en"
    }


# ===========================================
# POST /api/v1/output/share
# ===========================================
@router.post("/share", response_model=ShareResponse)
async def generate_share_link(request: ShareRequest):
    """
    Generate shareable link for a verification.
    
    Creates short URL and platform-specific share content.
    """
    verification = await verification_service.get_by_id(request.verification_id)
    if not verification:
        raise HTTPException(status_code=404, detail="Verification not found")
    
    # Generate short URL
    share_data = await share_service.generate_share_url(
        verification_id=request.verification_id,
        claim=verification.claim,
        verdict=verification.final_verdict.get("verdict", "UNVERIFIABLE") if verification.final_verdict else "UNVERIFIABLE",
        confidence=verification.final_verdict.get("confidence", 0.5) if verification.final_verdict else 0.5,
        summary=verification.final_verdict.get("reasoning_summary", "") if verification.final_verdict else ""
    )
    
    # Generate platform-specific content if requested
    platform_shares = {}
    if request.platforms:
        for platform in request.platforms:
            platform_data = await share_service.generate_social_share(
                verification_id=request.verification_id,
                claim=verification.claim,
                verdict=verification.final_verdict.get("verdict", "UNVERIFIABLE") if verification.final_verdict else "UNVERIFIABLE",
                summary=verification.final_verdict.get("reasoning_summary", "") if verification.final_verdict else "",
                platform=platform,
                short_url=share_data["short_url"]
            )
            platform_shares[platform] = platform_data
    
    # Generate embed code if requested
    embed_code = None
    if request.include_embed:
        embed_code = await share_service.generate_embed_code(
            verification_id=request.verification_id,
            style=request.embed_style or "card"
        )
    
    return ShareResponse(
        verification_id=request.verification_id,
        short_url=share_data["short_url"],
        short_code=share_data["short_code"],
        qr_code_url=share_data.get("qr_code_url"),
        platform_shares=platform_shares,
        embed_code=embed_code,
        created_at=share_data["created_at"]
    )


# ===========================================
# GET /api/v1/output/share/{short_code}
# ===========================================
@router.get("/share/{short_code}")
async def resolve_share_link(short_code: str):
    """
    Resolve a short code to verification data.
    """
    data = await share_service.resolve_short_url(short_code)
    if not data:
        raise HTTPException(status_code=404, detail="Share link not found")
    
    # Track view
    await share_service.track_share_view(short_code)
    
    return data


# ===========================================
# GET /api/v1/output/share/analytics/{short_code}
# ===========================================
@router.get("/share/analytics/{short_code}")
async def get_share_analytics(short_code: str):
    """
    Get analytics for a shared link.
    """
    return await share_service.get_share_analytics(short_code)
