"""
AURA WhatsApp Service
Facebook Business API integration (NOT Twilio)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx
import json

from app.core.logging import logger
from app.core.config import settings


class WhatsAppService:
    """
    WhatsApp Business API service using Facebook/Meta Graph API.
    Handles incoming messages (text, images, mixed) and sends responses.
    """
    
    GRAPH_API_URL = "https://graph.facebook.com"
    
    def __init__(self):
        self.access_token = settings.FB_ACCESS_TOKEN
        self.phone_number_id = settings.FB_PHONE_NUMBER_ID
        self.api_version = getattr(settings, 'FB_API_VERSION', 'v18.0')
        self.verify_token = settings.FB_WEBHOOK_VERIFY_TOKEN
        self.enabled = bool(self.access_token and self.phone_number_id)
    
    def verify_webhook(self, mode: str, token: str, challenge: str) -> Optional[str]:
        """
        Verify webhook callback from Facebook.
        Called when Facebook verifies the webhook URL.
        """
        if mode == "subscribe" and token == self.verify_token:
            logger.info("WhatsApp webhook verified successfully")
            return challenge
        logger.warning("WhatsApp webhook verification failed")
        return None
    
    async def process_webhook(self, payload: Dict) -> Dict[str, Any]:
        """
        Process incoming webhook from Facebook.
        Handles text messages, images, and mixed content.
        """
        try:
            entry = payload.get("entry", [])
            if not entry:
                return {"status": "no_entry"}
            
            changes = entry[0].get("changes", [])
            if not changes:
                return {"status": "no_changes"}
            
            value = changes[0].get("value", {})
            messages = value.get("messages", [])
            
            if not messages:
                # Might be a status update
                statuses = value.get("statuses", [])
                if statuses:
                    return {"status": "status_update", "statuses": statuses}
                return {"status": "no_messages"}
            
            # Process each message
            processed = []
            for msg in messages:
                result = await self._process_message(msg, value)
                processed.append(result)
            
            return {
                "status": "processed",
                "messages_count": len(processed),
                "messages": processed
            }
            
        except Exception as e:
            logger.error(f"WhatsApp webhook processing failed: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _process_message(self, message: Dict, value: Dict) -> Dict[str, Any]:
        """Process a single incoming message."""
        msg_type = message.get("type")
        from_number = message.get("from")
        msg_id = message.get("id")
        timestamp = message.get("timestamp")
        
        result = {
            "message_id": msg_id,
            "from": from_number,
            "type": msg_type,
            "timestamp": timestamp
        }
        
        if msg_type == "text":
            result["text"] = message.get("text", {}).get("body", "")
        
        elif msg_type == "image":
            image_info = message.get("image", {})
            result["image_id"] = image_info.get("id")
            result["image_mime"] = image_info.get("mime_type")
            result["image_caption"] = image_info.get("caption", "")
            # Download image for OCR processing
            result["image_url"] = await self._get_media_url(image_info.get("id"))
        
        elif msg_type == "document":
            doc_info = message.get("document", {})
            result["document_id"] = doc_info.get("id")
            result["document_name"] = doc_info.get("filename")
        
        # Get contact info
        contacts = value.get("contacts", [])
        if contacts:
            result["contact_name"] = contacts[0].get("profile", {}).get("name", "Unknown")
        
        return result
    
    async def _get_media_url(self, media_id: str) -> Optional[str]:
        """Get download URL for a media file."""
        if not media_id or not self.enabled:
            return None
        
        url = f"{self.GRAPH_API_URL}/{self.api_version}/{media_id}"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    return response.json().get("url")
        except Exception as e:
            logger.error(f"Failed to get media URL: {e}")
        
        return None
    
    async def download_media(self, media_url: str) -> Optional[bytes]:
        """Download media content from WhatsApp CDN."""
        if not media_url:
            return None
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(media_url, headers=headers)
                if response.status_code == 200:
                    return response.content
        except Exception as e:
            logger.error(f"Failed to download media: {e}")
        
        return None
    
    async def send_text_message(
        self,
        to: str,
        text: str,
        preview_url: bool = False
    ) -> Dict[str, Any]:
        """Send a text message to a WhatsApp user."""
        if not self.enabled:
            logger.warning("WhatsApp not configured")
            return {"success": False, "error": "WhatsApp not configured"}
        
        url = f"{self.GRAPH_API_URL}/{self.api_version}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {
                "preview_url": preview_url,
                "body": text
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "message_id": data.get("messages", [{}])[0].get("id"),
                        "to": to
                    }
                else:
                    return {
                        "success": False,
                        "error": response.text,
                        "status_code": response.status_code
                    }
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_fact_check_result(
        self,
        to: str,
        claim: str,
        verdict: str,
        confidence: float,
        summary: str,
        share_url: str = None
    ) -> Dict[str, Any]:
        """Send a formatted fact-check result."""
        emoji_map = {
            "TRUE": "✅",
            "FALSE": "❌",
            "MISLEADING": "⚠️",
            "UNVERIFIABLE": "❓"
        }
        
        emoji = emoji_map.get(verdict, "🔍")
        confidence_pct = int(confidence * 100)
        
        message = f"""
{emoji} *AURA Fact-Check Result*

📝 *Claim:*
"{claim[:200]}..."

🎯 *Verdict:* {verdict}
📊 *Confidence:* {confidence_pct}%

📖 *Summary:*
{summary[:300]}

{"🔗 " + share_url if share_url else ""}

_Powered by AURA Fact-Checker_
        """.strip()
        
        return await self.send_text_message(to, message, preview_url=bool(share_url))
    
    async def send_processing_notification(
        self,
        to: str,
        claim: str,
        verification_id: str,
        estimated_time: int = 30
    ) -> Dict[str, Any]:
        """Send notification that claim is being processed."""
        message = f"""
🔍 *Checking your claim...*

📝 "{claim[:100]}..."

⏱️ Estimated time: {estimated_time} seconds
📊 Claim ID: `{verification_id}`

_You'll receive the result shortly._
        """.strip()
        
        return await self.send_text_message(to, message)


# Global instance
whatsapp_service = WhatsAppService()
