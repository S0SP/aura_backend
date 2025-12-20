"""
AURA Service - Audio Generation
Text-to-Speech using ElevenLabs API
"""

from typing import Optional, Dict, Any
from datetime import datetime
import asyncio
import hashlib
import os
import httpx

from app.core.logging import logger
from app.core.config import settings


class AudioService:
    """Service for generating audio using ElevenLabs TTS."""
    
    # ElevenLabs API settings
    BASE_URL = "https://api.elevenlabs.io/v1"
    
    # Available voices (ElevenLabs multilingual voices)
    VOICES = {
        "rachel": "21m00Tcm4TlvDq8ikWAM",  # Female, calm
        "domi": "AZnzlk1XvdvUeBnXmlld",     # Female, strong
        "bella": "EXAVITQu4vr4xnSDxMaL",    # Female, soft
        "antoni": "ErXwobaYiN019PkySvjV",   # Male, deep
        "josh": "TxGEqnHWrfWFTfGW9XjX",     # Male, energetic
        "elli": "MF3mGyEYCl7XYWbV9V6O",     # Female, young
        "sam": "yoZ06aMxZJJ28mfd3POQ",      # Male, authoritative
        "arnold": "VR6AewLTigWG4xSOukaG",   # Male, deep
    }
    
    # Supported models
    MODELS = {
        "multilingual_v2": "eleven_multilingual_v2",  # Supports 29 languages including Indian
        "turbo_v2": "eleven_turbo_v2",                # Faster, English-optimized
    }
    
    # Language support (ElevenLabs multilingual v2 supports these Indian languages)
    SUPPORTED_LANGUAGES = {
        "en": "English",
        "hi": "Hindi",
        "ta": "Tamil",
        "te": "Telugu",
        "bn": "Bengali",
        "mr": "Marathi",
        "gu": "Gujarati",
        "kn": "Kannada",
        "ml": "Malayalam",
        "pa": "Punjabi"
    }
    
    def __init__(self):
        self.api_key = settings.ELEVENLABS_API_KEY
        self.default_voice_id = settings.ELEVENLABS_VOICE_ID if hasattr(settings, 'ELEVENLABS_VOICE_ID') else self.VOICES["rachel"]
        self.cache_dir = settings.AUDIO_CACHE_DIR if hasattr(settings, 'AUDIO_CACHE_DIR') else "/tmp/aura_audio"
        self.enabled = bool(self.api_key)
    
    async def generate_audio(
        self,
        text: str,
        language: str = "en",
        voice_id: str = None,
        model: str = "multilingual_v2",
        stability: float = 0.5,
        similarity_boost: float = 0.75
    ) -> Dict[str, Any]:
        """
        Generate audio from text using ElevenLabs API.
        
        Args:
            text: Text to convert to speech
            language: Language code (for multilingual model)
            voice_id: ElevenLabs voice ID
            model: Model to use (multilingual_v2 or turbo_v2)
            stability: Voice stability (0-1)
            similarity_boost: Voice similarity boost (0-1)
            
        Returns:
            Audio file info with URL
        """
        # Generate cache key
        cache_key = self._generate_cache_key(text, language, voice_id or self.default_voice_id)
        cached = self._check_cache(cache_key)
        if cached:
            logger.info(f"Audio cache hit: {cache_key}")
            return cached
        
        if not self.enabled:
            logger.warning("ElevenLabs API key not configured")
            return await self._generate_placeholder(text, language)
        
        try:
            voice = voice_id or self.default_voice_id
            model_id = self.MODELS.get(model, self.MODELS["multilingual_v2"])
            
            # Call ElevenLabs API
            audio_content = await self._call_elevenlabs(
                text=text,
                voice_id=voice,
                model_id=model_id,
                stability=stability,
                similarity_boost=similarity_boost
            )
            
            # Save to file
            filename = f"{cache_key}.mp3"
            os.makedirs(self.cache_dir, exist_ok=True)
            filepath = os.path.join(self.cache_dir, filename)
            
            with open(filepath, "wb") as f:
                f.write(audio_content)
            
            # Calculate duration estimate (rough: ~150 words per minute)
            word_count = len(text.split())
            duration_estimate = (word_count / 150) * 60
            
            result = {
                "audio_id": cache_key,
                "audio_url": f"/api/v1/output/audio/{cache_key}",
                "language": language,
                "language_name": self.SUPPORTED_LANGUAGES.get(language, "Unknown"),
                "voice_id": voice,
                "model": model,
                "duration_estimate_seconds": round(duration_estimate, 1),
                "format": "mp3",
                "file_size_bytes": len(audio_content),
                "provider": "elevenlabs",
                "generated_at": datetime.utcnow().isoformat()
            }
            
            self._save_to_cache(cache_key, result)
            logger.info(f"Generated audio: {cache_key} ({len(audio_content)} bytes)")
            return result
            
        except Exception as e:
            logger.error(f"ElevenLabs audio generation failed: {e}")
            return await self._generate_placeholder(text, language)
    
    async def _call_elevenlabs(
        self,
        text: str,
        voice_id: str,
        model_id: str,
        stability: float,
        similarity_boost: float
    ) -> bytes:
        """Call ElevenLabs Text-to-Speech API."""
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
                "stability": stability,
                "similarity_boost": similarity_boost
            }
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            
            if response.status_code != 200:
                error_detail = response.text
                logger.error(f"ElevenLabs API error: {response.status_code} - {error_detail}")
                raise Exception(f"ElevenLabs API error: {response.status_code}")
            
            return response.content
    
    async def _generate_placeholder(
        self,
        text: str,
        language: str
    ) -> Dict[str, Any]:
        """Generate placeholder response when TTS is unavailable."""
        cache_key = self._generate_cache_key(text, language, "placeholder")
        
        return {
            "audio_id": cache_key,
            "audio_url": None,
            "language": language,
            "language_name": self.SUPPORTED_LANGUAGES.get(language, "Unknown"),
            "format": "placeholder",
            "status": "unavailable",
            "message": "Audio generation temporarily unavailable. Configure ELEVENLABS_API_KEY in .env",
            "text_content": text,
            "provider": "none",
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def _generate_cache_key(
        self,
        text: str,
        language: str,
        voice_id: str
    ) -> str:
        """Generate cache key for audio content."""
        content = f"{text}:{language}:{voice_id}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _check_cache(self, cache_key: str) -> Optional[Dict]:
        """Check if audio is cached."""
        filepath = os.path.join(self.cache_dir, f"{cache_key}.mp3")
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            return {
                "audio_id": cache_key,
                "audio_url": f"/api/v1/output/audio/{cache_key}",
                "cached": True,
                "file_size_bytes": file_size,
                "provider": "elevenlabs"
            }
        return None
    
    def _save_to_cache(self, cache_key: str, metadata: Dict) -> None:
        """Save metadata to cache (could use Redis in production)."""
        pass
    
    async def get_audio_file(self, audio_id: str) -> Optional[bytes]:
        """Get audio file content by ID."""
        filepath = os.path.join(self.cache_dir, f"{audio_id}.mp3")
        if os.path.exists(filepath):
            with open(filepath, "rb") as f:
                return f.read()
        return None
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Get list of supported TTS languages."""
        return self.SUPPORTED_LANGUAGES.copy()
    
    def get_available_voices(self) -> Dict[str, str]:
        """Get available ElevenLabs voices."""
        return self.VOICES.copy()
    
    async def get_voice_info(self, voice_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific voice."""
        if not self.enabled:
            return None
        
        try:
            url = f"{self.BASE_URL}/voices/{voice_id}"
            headers = {"xi-api-key": self.api_key}
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    return response.json()
                return None
        except Exception as e:
            logger.error(f"Failed to get voice info: {e}")
            return None
    
    async def get_user_subscription(self) -> Optional[Dict[str, Any]]:
        """Get ElevenLabs subscription info (for rate limiting)."""
        if not self.enabled:
            return None
        
        try:
            url = f"{self.BASE_URL}/user/subscription"
            headers = {"xi-api-key": self.api_key}
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    return response.json()
                return None
        except Exception as e:
            logger.error(f"Failed to get subscription info: {e}")
            return None


# Global instance
audio_service = AudioService()
