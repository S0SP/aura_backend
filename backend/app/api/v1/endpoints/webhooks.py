"""
AURA API v1 - Webhooks Endpoints
Handles external service webhooks (WhatsApp, etc.)
"""

from fastapi import APIRouter, Request, HTTPException, Query
from datetime import datetime

from app.core.config import settings
from app.core.logging import logger
from app.core.security import verify_webhook_signature

router = APIRouter()


# ===========================================
# Facebook/WhatsApp Webhook
# ===========================================
@router.get("/facebook")
async def verify_facebook_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    """
    Verify Facebook webhook subscription.
    Called by Facebook when setting up the webhook.
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.FB_WEBHOOK_VERIFY_TOKEN:
        logger.info("Facebook webhook verified")
        return int(hub_challenge)
    
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/facebook")
async def handle_facebook_webhook(request: Request):
    """
    Handle incoming Facebook webhook events.
    Processes WhatsApp messages and status updates.
    """
    # Get raw body for signature verification
    body = await request.body()
    
    # Verify signature
    signature = request.headers.get("X-Hub-Signature-256", "")
    if settings.FB_APP_SECRET and not verify_webhook_signature(
        body, signature, settings.FB_APP_SECRET
    ):
        logger.warning("Invalid webhook signature")
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse webhook data
    data = await request.json()
    
    logger.info(f"Facebook webhook received: {data.get('object')}")
    
    # Process based on object type
    obj_type = data.get("object")
    
    if obj_type == "whatsapp_business_account":
        # Process WhatsApp events
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                if change.get("field") == "messages":
                    # Handle incoming messages
                    value = change.get("value", {})
                    messages = value.get("messages", [])
                    
                    for message in messages:
                        await _process_whatsapp_message(message, value)
                
                elif change.get("field") == "message_status":
                    # Handle status updates
                    pass
    
    return {"status": "received"}


async def _process_whatsapp_message(message: dict, value: dict):
    """Process a WhatsApp message from the webhook."""
    message_type = message.get("type")
    from_number = message.get("from")
    
    logger.info(f"WhatsApp message from {from_number}: {message_type}")
    
    # TODO: Queue for processing
    # This will be implemented in Module 5


# ===========================================
# General Status Webhook (for async updates)
# ===========================================
@router.post("/status")
async def status_webhook(
    verification_id: str,
    status: str,
    data: dict = None
):
    """
    Internal webhook for status updates.
    Used by background workers to report progress.
    """
    logger.info(f"Status update: {verification_id} -> {status}")
    
    # TODO: Update Redis and notify WebSocket clients
    
    return {"status": "received"}


# ===========================================
# Webhook Health Check
# ===========================================
@router.get("/health")
async def webhook_health():
    """Health check for webhook endpoints."""
    return {
        "status": "healthy",
        "facebook_configured": bool(settings.FB_APP_ID),
        "whatsapp_configured": bool(settings.FB_PHONE_NUMBER_ID)
    }
