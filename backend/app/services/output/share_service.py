"""
AURA Service - Share Service
URL shortening and social sharing for verification results
"""

from typing import Optional, Dict, Any
from datetime import datetime
import hashlib
import string
import random

from app.core.logging import logger
from app.core.config import settings
from app.db.redis_db import get_redis


class ShareService:
    """Service for generating shareable content and short URLs."""
    
    # Short URL character set
    CHARS = string.ascii_letters + string.digits
    SHORT_URL_LENGTH = 8
    
    # Social media templates
    SOCIAL_TEMPLATES = {
        "twitter": "{emoji} Claim: \"{claim}\" - {verdict}\n\nVerified by @AURAFactCheck\n🔗 {url}",
        "whatsapp": "{emoji} *Fact Check*\n\nClaim: \"{claim}\"\n\n*Verdict: {verdict}*\n\n{summary}\n\n🔗 Verify yourself: {url}",
        "facebook": "Fact Check Result:\n\n{emoji} {verdict}\n\nClaim: \"{claim}\"\n\n{summary}\n\nVerified by AURA Fact-Checker\n{url}",
        "telegram": "{emoji} *Fact Check*\n\n*Claim:* {claim}\n\n*Verdict:* {verdict}\n\n{summary}\n\n[Verify yourself]({url})"
    }
    
    # Verdict emojis
    VERDICT_EMOJIS = {
        "TRUE": "✅",
        "FALSE": "❌",
        "MISLEADING": "⚠️",
        "PARTIALLY_TRUE": "🔶",
        "UNVERIFIABLE": "❓"
    }
    
    async def generate_share_url(
        self,
        verification_id: str,
        claim: str,
        verdict: str,
        confidence: float,
        summary: str = ""
    ) -> Dict[str, Any]:
        """
        Generate a short shareable URL for a verification.
        
        Args:
            verification_id: Verification ID
            claim: Original claim
            verdict: Verification verdict
            confidence: Confidence score
            summary: Brief summary
            
        Returns:
            Share URL and metadata
        """
        # Generate short code
        short_code = self._generate_short_code(verification_id)
        
        # Store mapping in Redis
        await self._store_short_url(short_code, {
            "verification_id": verification_id,
            "claim": claim,
            "verdict": verdict,
            "confidence": confidence,
            "summary": summary,
            "created_at": datetime.utcnow().isoformat()
        })
        
        base_url = settings.BASE_URL if hasattr(settings, 'BASE_URL') else "https://aura.in"
        short_url = f"{base_url}/v/{short_code}"
        
        return {
            "short_code": short_code,
            "short_url": short_url,
            "verification_id": verification_id,
            "qr_code_url": f"{base_url}/api/v1/output/qr/{short_code}",
            "expires_at": None,  # Permanent links
            "created_at": datetime.utcnow().isoformat()
        }
    
    async def generate_social_share(
        self,
        verification_id: str,
        claim: str,
        verdict: str,
        summary: str,
        platform: str,
        short_url: str = None
    ) -> Dict[str, Any]:
        """
        Generate platform-specific share content.
        
        Args:
            verification_id: Verification ID
            claim: Original claim
            verdict: Verification verdict
            summary: Brief summary
            platform: Social platform (twitter, whatsapp, facebook, telegram)
            short_url: Optional pre-generated short URL
            
        Returns:
            Platform-specific share content
        """
        if not short_url:
            share_data = await self.generate_share_url(
                verification_id, claim, verdict, 0.8, summary
            )
            short_url = share_data["short_url"]
        
        emoji = self.VERDICT_EMOJIS.get(verdict, "❓")
        template = self.SOCIAL_TEMPLATES.get(platform, self.SOCIAL_TEMPLATES["twitter"])
        
        # Truncate claim for social media
        max_claim_length = 100 if platform == "twitter" else 200
        truncated_claim = claim[:max_claim_length] + "..." if len(claim) > max_claim_length else claim
        
        # Format message
        message = template.format(
            emoji=emoji,
            claim=truncated_claim,
            verdict=verdict,
            summary=summary[:150] if summary else "",
            url=short_url
        )
        
        # Generate share links
        share_links = self._generate_share_links(message, short_url, platform)
        
        return {
            "platform": platform,
            "message": message,
            "character_count": len(message),
            "share_url": share_links.get("direct_share_url"),
            "intent_url": share_links.get("intent_url"),
            "verification_id": verification_id
        }
    
    async def resolve_short_url(self, short_code: str) -> Optional[Dict[str, Any]]:
        """
        Resolve a short code to verification data.
        
        Args:
            short_code: Short URL code
            
        Returns:
            Verification data or None
        """
        redis = await get_redis()
        if not redis:
            return None
        
        data = await redis.get(f"share:{short_code}")
        if data:
            import json
            return json.loads(data)
        return None
    
    async def get_share_analytics(self, short_code: str) -> Dict[str, Any]:
        """
        Get analytics for a shared link.
        
        Args:
            short_code: Short URL code
            
        Returns:
            Analytics data
        """
        redis = await get_redis()
        if not redis:
            return {"views": 0, "shares": 0}
        
        views = await redis.get(f"share:views:{short_code}") or 0
        shares = await redis.get(f"share:clicks:{short_code}") or 0
        
        return {
            "short_code": short_code,
            "views": int(views),
            "shares": int(shares),
            "platforms": {}  # Could track per-platform
        }
    
    async def track_share_view(self, short_code: str) -> None:
        """Track a view of a shared link."""
        redis = await get_redis()
        if redis:
            await redis.incr(f"share:views:{short_code}")
    
    def _generate_short_code(self, verification_id: str) -> str:
        """Generate a unique short code."""
        # Use hash + random for uniqueness
        base = hashlib.sha256(verification_id.encode()).hexdigest()[:6]
        suffix = ''.join(random.choices(self.CHARS, k=2))
        return f"{base}{suffix}"
    
    async def _store_short_url(self, short_code: str, data: Dict) -> None:
        """Store short URL mapping in Redis."""
        redis = await get_redis()
        if redis:
            import json
            await redis.set(
                f"share:{short_code}",
                json.dumps(data),
                ex=None  # No expiry for permanent links
            )
    
    def _generate_share_links(
        self,
        message: str,
        url: str,
        platform: str
    ) -> Dict[str, str]:
        """Generate platform-specific share intent URLs."""
        from urllib.parse import quote
        
        links = {}
        encoded_message = quote(message)
        encoded_url = quote(url)
        
        if platform == "twitter":
            links["intent_url"] = f"https://twitter.com/intent/tweet?text={encoded_message}"
            links["direct_share_url"] = links["intent_url"]
            
        elif platform == "whatsapp":
            links["intent_url"] = f"https://wa.me/?text={encoded_message}"
            links["direct_share_url"] = links["intent_url"]
            
        elif platform == "facebook":
            links["intent_url"] = f"https://www.facebook.com/sharer/sharer.php?u={encoded_url}&quote={encoded_message}"
            links["direct_share_url"] = links["intent_url"]
            
        elif platform == "telegram":
            links["intent_url"] = f"https://t.me/share/url?url={encoded_url}&text={encoded_message}"
            links["direct_share_url"] = links["intent_url"]
        
        return links
    
    async def generate_embed_code(
        self,
        verification_id: str,
        style: str = "card"
    ) -> Dict[str, str]:
        """
        Generate embeddable HTML/iframe code.
        
        Args:
            verification_id: Verification ID
            style: 'card', 'badge', or 'minimal'
            
        Returns:
            Embed codes
        """
        base_url = settings.BASE_URL if hasattr(settings, 'BASE_URL') else "https://aura.in"
        embed_url = f"{base_url}/embed/{verification_id}?style={style}"
        
        return {
            "iframe": f'<iframe src="{embed_url}" width="400" height="200" frameborder="0"></iframe>',
            "script": f'<script src="{base_url}/embed.js" data-verification="{verification_id}" data-style="{style}"></script>',
            "direct_url": embed_url
        }


# Global instance
share_service = ShareService()
