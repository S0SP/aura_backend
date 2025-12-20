"""
AURA API v1 - Input Processing Endpoints
Handles claim submission, URL processing, WhatsApp webhooks, and image uploads
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query, UploadFile, File
from fastapi.responses import JSONResponse
from datetime import datetime

from app.core.logging import logger
from app.core.security import get_current_user, get_optional_user
from app.utils.id_generator import generate_verification_id
from app.utils.validators import (
    validate_claim_text, validate_url, detect_platform,
    ClaimPriority, ContentType
)
from app.utils.language_detector import detect_language
from app.schemas.input_schemas import (
    ClaimSubmission, ClaimResponse,
    URLSubmission, URLResponse,
    ImageSubmission, ImageResponse,
    VerificationStatus
)

router = APIRouter()


# ===========================================
# POST /api/v1/input/claim
# ===========================================
@router.post("/claim", response_model=ClaimResponse, status_code=202)
async def submit_claim(
    submission: ClaimSubmission,
    background_tasks: BackgroundTasks,
    current_user: Optional[dict] = Depends(get_optional_user)
):
    """
    Submit a text claim for fact-checking verification.
    
    The claim will be queued for processing through:
    1. Quick Classification (XLM-RoBERTa)
    2. Evidence Retrieval (SERP, Pinecone, Neo4j)
    3. Multi-Agent Debate (CrewAI)
    4. Final Verdict Generation
    
    Returns a verification_id for tracking progress via WebSocket or polling.
    """
    # Validate claim text
    is_valid, error = validate_claim_text(submission.claim)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)
    
    # Detect language if not provided
    language = submission.language
    if not language:
        detection = detect_language(submission.claim)
        language = detection.language
    
    # Generate verification ID
    verification_id = generate_verification_id()
    
    # Create verification record
    verification_data = {
        "verification_id": verification_id,
        "claim": submission.claim,
        "language": language,
        "source_context": submission.source_context,
        "priority": submission.priority or ClaimPriority.NORMAL,
        "content_type": ContentType.TEXT,
        "status": "queued",
        "user_id": current_user["user_id"] if current_user else None,
        "metadata": submission.metadata,
        "created_at": datetime.utcnow().isoformat(),
        "estimated_time_seconds": 15
    }
    
    # TODO: Add to processing queue
    # background_tasks.add_task(process_claim, verification_data)
    
    logger.info(f"Claim submitted: {verification_id}")
    
    return ClaimResponse(
        verification_id=verification_id,
        status="queued",
        estimated_time_seconds=15,
        queue_position=1,  # TODO: Get actual queue position
        websocket_url=f"wss://api.aura.in/ws/{verification_id}",
        created_at=verification_data["created_at"]
    )


# ===========================================
# POST /api/v1/input/url
# ===========================================
@router.post("/url", response_model=URLResponse, status_code=202)
async def submit_url(
    submission: URLSubmission,
    background_tasks: BackgroundTasks,
    current_user: Optional[dict] = Depends(get_optional_user)
):
    """
    Submit a social media post URL for fact-checking.
    
    Supported platforms: Twitter/X, Facebook, Instagram, YouTube, TikTok, LinkedIn, Reddit
    
    The content will be extracted and processed through the verification pipeline.
    """
    # Validate URL
    is_valid, error = validate_url(submission.url)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)
    
    # Detect platform if not provided
    platform = submission.platform or detect_platform(submission.url)
    
    # Generate verification ID
    verification_id = generate_verification_id()
    
    verification_data = {
        "verification_id": verification_id,
        "url": submission.url,
        "platform": platform.value if hasattr(platform, 'value') else platform,
        "include_comments": submission.include_comments,
        "priority": submission.priority or ClaimPriority.NORMAL,
        "content_type": ContentType.URL,
        "status": "extracting_content",
        "user_id": current_user["user_id"] if current_user else None,
        "created_at": datetime.utcnow().isoformat(),
        "estimated_time_seconds": 25
    }
    
    # TODO: Add to processing queue for content extraction
    # background_tasks.add_task(process_url, verification_data)
    
    logger.info(f"URL submitted: {verification_id} - {platform}")
    
    return URLResponse(
        verification_id=verification_id,
        status="extracting_content",
        extracted_claim=None,  # Will be populated after extraction
        media_detected=[],
        estimated_time_seconds=25,
        websocket_url=f"wss://api.aura.in/ws/{verification_id}"
    )


# ===========================================
# POST /api/v1/input/whatsapp (Facebook Business API Webhook)
# ===========================================
@router.post("/whatsapp")
async def whatsapp_webhook(
    request_body: dict,
    background_tasks: BackgroundTasks
):
    """
    Receive messages from WhatsApp Business API (Facebook).
    
    Handles:
    - Text messages
    - Image messages (with OCR)
    - Forwarded messages
    
    Sends verification results back via WhatsApp.
    """
    try:
        # Extract message data from Facebook webhook format
        entry = request_body.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])
        
        if not messages:
            return {"status": "no_messages"}
        
        message = messages[0]
        from_number = message.get("from")
        message_type = message.get("type")
        
        # Generate verification ID
        verification_id = generate_verification_id()
        
        # Process based on message type
        if message_type == "text":
            claim_text = message.get("text", {}).get("body", "")
            
            # Detect language
            detection = detect_language(claim_text)
            
            verification_data = {
                "verification_id": verification_id,
                "claim": claim_text,
                "language": detection.language,
                "source_context": "WhatsApp forward",
                "content_type": ContentType.WHATSAPP,
                "whatsapp_from": from_number,
                "status": "queued",
                "created_at": datetime.utcnow().isoformat()
            }
            
            # TODO: Queue for processing
            # background_tasks.add_task(process_whatsapp_claim, verification_data)
            
        elif message_type == "image":
            image_data = message.get("image", {})
            media_id = image_data.get("id")
            caption = image_data.get("caption", "")
            
            verification_data = {
                "verification_id": verification_id,
                "media_id": media_id,
                "caption": caption,
                "content_type": ContentType.IMAGE,
                "whatsapp_from": from_number,
                "status": "extracting_text",
                "created_at": datetime.utcnow().isoformat()
            }
            
            # TODO: Queue for OCR processing
            # background_tasks.add_task(process_whatsapp_image, verification_data)
        
        logger.info(f"WhatsApp message received: {verification_id} from {from_number}")
        
        return {"status": "received", "verification_id": verification_id}
        
    except Exception as e:
        logger.error(f"WhatsApp webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# GET /api/v1/input/whatsapp (Webhook Verification)
# ===========================================
@router.get("/whatsapp")
async def verify_whatsapp_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    """
    Verify WhatsApp Business API webhook (Facebook verification challenge).
    """
    from app.core.config import settings
    
    if hub_mode == "subscribe" and hub_verify_token == settings.FB_WEBHOOK_VERIFY_TOKEN:
        logger.info("WhatsApp webhook verified successfully")
        return int(hub_challenge)
    
    raise HTTPException(status_code=403, detail="Verification failed")


# ===========================================
# POST /api/v1/input/image
# ===========================================
@router.post("/image", response_model=ImageResponse, status_code=202)
async def submit_image(
    image: UploadFile = File(...),
    caption: Optional[str] = None,
    priority: Optional[str] = None,
    background_tasks: BackgroundTasks = None,
    current_user: Optional[dict] = Depends(get_optional_user)
):
    """
    Submit an image for OCR text extraction and fact-checking.
    
    Supported formats: JPEG, PNG, GIF, WebP
    Maximum size: 10MB
    
    The image will be processed through:
    1. OCR text extraction (Tesseract)
    2. Claim identification
    3. Standard verification pipeline
    """
    # Validate file type
    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    if image.content_type not in allowed_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported image type: {image.content_type}"
        )
    
    # Check file size (10MB limit)
    contents = await image.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image too large (max 10MB)")
    
    # Generate verification ID
    verification_id = generate_verification_id()
    
    verification_data = {
        "verification_id": verification_id,
        "filename": image.filename,
        "content_type": image.content_type,
        "caption": caption,
        "priority": priority or ClaimPriority.NORMAL,
        "status": "extracting_text",
        "user_id": current_user["user_id"] if current_user else None,
        "created_at": datetime.utcnow().isoformat(),
        "image_size_bytes": len(contents)
    }
    
    # TODO: Save image and queue for OCR processing
    # background_tasks.add_task(process_image, verification_data, contents)
    
    logger.info(f"Image submitted: {verification_id} - {image.filename}")
    
    return ImageResponse(
        verification_id=verification_id,
        status="extracting_text",
        extracted_text=None,  # Will be populated after OCR
        estimated_time_seconds=30,
        websocket_url=f"wss://api.aura.in/ws/{verification_id}"
    )


# ===========================================
# GET /api/v1/input/status/{verification_id}
# ===========================================
@router.get("/status/{verification_id}", response_model=VerificationStatus)
async def get_verification_status(verification_id: str):
    """
    Get the current status of a verification request.
    
    Status values:
    - queued: Waiting in queue
    - extracting: Extracting content from URL/image
    - classifying: Running quick classification
    - retrieving_evidence: Searching for evidence
    - debating: Multi-agent debate in progress
    - judging: Judge agent evaluating
    - generating_response: Creating final response
    - completed: Verification complete
    - failed: Verification failed
    """
    # TODO: Fetch from database/cache
    # For now, return mock data
    
    return VerificationStatus(
        verification_id=verification_id,
        status="processing",
        current_step={
            "name": "debate_round_1",
            "progress_percent": 25,
            "current_agent": "for_agent"
        },
        quick_classification={
            "verdict": "LIKELY_FALSE",
            "confidence": 0.85
        },
        estimated_completion=datetime.utcnow().isoformat(),
        created_at=datetime.utcnow().isoformat()
    )


# ===========================================
# DELETE /api/v1/input/cancel/{verification_id}
# ===========================================
@router.delete("/cancel/{verification_id}")
async def cancel_verification(
    verification_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Cancel a pending verification request.
    
    Only the user who submitted the request can cancel it.
    Cannot cancel completed or in-progress verifications.
    """
    # TODO: Implement cancellation logic
    
    logger.info(f"Verification cancelled: {verification_id} by {current_user['user_id']}")
    
    return {
        "verification_id": verification_id,
        "status": "cancelled",
        "message": "Verification request cancelled successfully"
    }
