"""
AURA Audio Generator using ElevenLabs
Text-to-Speech service for audio responses
"""

from typing import Dict, Any, Optional
from datetime import datetime
import httpx
import hashlib
import os
from pathlib import Path

from app.core.logging import logger
from app.core.config import settings


class AudioGenerator:
    """
    Audio generation service using ElevenLabs API.
    Generates audio responses for fact-check verdicts.
    """
    
    BASE_URL = "https://api.elevenlabs.io/v1"
    
    # Voice options
    VOICES = {
        "rachel": "21m00Tcm4TlvDq8ikWAM",  # Female, calm
        "domi": "AZnzlk1XvdvUeBnXmlld",     # Female, strong
        "bella": "EXAVITQu4vr4xnSDxMaL",    # Female, soft
        "josh": "TxGEqnHWrfWFTfGW9XjX",     # Male, energetic
        "adam": "pNInz6obpgDQGcFmaJgB",     # Male, deep
    }
    
    # Models
    MODELS = {
        "multilingual_v2": "eleven_multilingual_v2",  # Best for Indian languages
        "turbo": "eleven_turbo_v2",                    # Fastest
        "monolingual": "eleven_monolingual_v1"        # English only
    }
    
    def __init__(self):
        self.api_key = settings.ELEVENLABS_API_KEY
        self.default_voice_id = getattr(settings, 'ELEVENLABS_VOICE_ID', self.VOICES["rachel"])
        self.enabled = bool(self.api_key)
        self.audio_dir = Path("static/audio")
        self.audio_dir.mkdir(parents=True, exist_ok=True)
    
    async def generate(
        self,
        text: str,
        language: str = "en",
        voice_id: str = None,
        verification_id: str = None
    ) -> Dict[str, Any]:
        """
        Generate audio from text using ElevenLabs.
        """
        if not self.enabled:
            logger.warning("ElevenLabs API key not configured")
            return {
                "success": False,
                "error": "ElevenLabs not configured",
                "fallback": True
            }
        
        start_time = datetime.utcnow()
        
        # Check cache
        cache_key = self._get_cache_key(text, language, voice_id)
        cached_path = self.audio_dir / f"{cache_key}.mp3"
        
        if cached_path.exists():
            logger.info(f"Returning cached audio: {cache_key}")
            return {
                "success": True,
                "cached": True,
                "file_path": str(cached_path),
                "audio_url": f"/static/audio/{cache_key}.mp3"
            }
        
        try:
            # Select voice
            voice = voice_id or self.default_voice_id
            
            # Use multilingual model for Indian languages
            model = "eleven_multilingual_v2" if language in ["hi", "mr", "ta", "te", "bn", "gu", "kn", "ml", "pa", "or"] else "eleven_turbo_v2"
            
            # Generate audio
            audio_content = await self._call_elevenlabs(
                text=text,
                voice_id=voice,
                model_id=model
            )
            
            # Save to file
            file_path = self.audio_dir / f"{cache_key}.mp3"
            with open(file_path, "wb") as f:
                f.write(audio_content)
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                "success": True,
                "cached": False,
                "file_path": str(file_path),
                "audio_url": f"/static/audio/{cache_key}.mp3",
                "model_used": model,
                "voice_id": voice,
                "text_length": len(text),
                "processing_time_seconds": round(processing_time, 2),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"ElevenLabs audio generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "fallback": True
            }
    
    async def _call_elevenlabs(
        self,
        text: str,
        voice_id: str,
        model_id: str
    ) -> bytes:
        """Call ElevenLabs TTS API."""
        url = f"{self.BASE_URL}/text-to-speech/{voice_id}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        
        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            
            if response.status_code != 200:
                error_detail = response.text
                logger.error(f"ElevenLabs API error: {response.status_code} - {error_detail}")
                raise Exception(f"ElevenLabs API error: {response.status_code}")
            
            return response.content
    
    async def generate_verdict_audio(
        self,
        claim: str,
        verdict: str,
        reasoning: str,
        language: str = "en",
        verification_id: str = None
    ) -> Dict[str, Any]:
        """
        Generate audio for a complete verdict announcement.
        """
        # Build announcement text
        if language == "hi":
            text = self._build_hindi_announcement(claim, verdict, reasoning)
        else:
            text = self._build_english_announcement(claim, verdict, reasoning)
        
        return await self.generate(
            text=text,
            language=language,
            verification_id=verification_id
        )
    
    def _build_english_announcement(
        self,
        claim: str,
        verdict: str,
        reasoning: str
    ) -> str:
        """Build English audio announcement."""
        verdict_phrases = {
            "TRUE": "verified as TRUE",
            "FALSE": "found to be FALSE",
            "MISLEADING": "determined to be MISLEADING",
            "UNVERIFIABLE": "could not be verified"
        }
        
        verdict_text = verdict_phrases.get(verdict, "has been reviewed")
        claim_short = claim[:150] + "..." if len(claim) > 150 else claim
        reasoning_short = reasoning[:200] + "..." if len(reasoning) > 200 else reasoning
        
        return f"""
        This is an AURA Fact-Check alert. 
        The claim: "{claim_short}" has been {verdict_text}. 
        {reasoning_short}
        Please verify information before sharing. 
        Thank you for using AURA Fact-Checker.
        """.strip()
    
    def _build_hindi_announcement(
        self,
        claim: str,
        verdict: str,
        reasoning: str
    ) -> str:
        """Build Hindi audio announcement."""
        verdict_hindi = {
            "TRUE": "सत्य पाया गया है",
            "FALSE": "झूठा पाया गया है",
            "MISLEADING": "भ्रामक पाया गया है",
            "UNVERIFIABLE": "सत्यापित नहीं किया जा सका"
        }
        
        verdict_text = verdict_hindi.get(verdict, "की समीक्षा की गई है")
        claim_short = claim[:150] + "..." if len(claim) > 150 else claim
        
        return f"""
        यह AURA फैक्ट-चेक अलर्ट है।
        दावा: "{claim_short}" {verdict_text}।
        कृपया जानकारी को साझा करने से पहले सत्यापित करें।
        AURA फैक्ट-चेकर का उपयोग करने के लिए धन्यवाद।
        """.strip()
    
    def _get_cache_key(self, text: str, language: str, voice_id: str) -> str:
        """Generate cache key for audio."""
        content = f"{text}_{language}_{voice_id}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    async def get_subscription_info(self) -> Dict[str, Any]:
        """Get ElevenLabs subscription info."""
        if not self.enabled:
            return {"error": "Not configured"}
        
        try:
            url = f"{self.BASE_URL}/user/subscription"
            headers = {"xi-api-key": self.api_key}
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    return response.json()
                return {"error": f"API error: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}


# Global instance
audio_generator = AudioGenerator()
