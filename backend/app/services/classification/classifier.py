"""
AURA Classifier Service
XLM-RoBERTa based initial fact classification via HuggingFace API
"""

from typing import Dict, Any, Optional
from datetime import datetime
import httpx

from app.core.logging import logger
from app.core.config import settings


class Classifier:
    """
    Initial fact classifier using finetuned XLM-RoBERTa model on HuggingFace.
    Provides quick FAKE/REAL classification before full debate.
    """
    
    def __init__(self):
        self.api_key = settings.HUGGINGFACE_API_KEY
        self.endpoint = settings.XLM_ROBERTA_ENDPOINT
        self.enabled = bool(self.api_key and self.endpoint)
    
    async def classify(
        self,
        text: str,
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Classify text as FAKE or REAL using XLM-RoBERTa.
        
        Returns:
            verdict: FAKE | REAL
            confidence: 0.0 - 1.0
            processing_time_ms: int
        """
        start_time = datetime.utcnow()
        
        if not self.enabled:
            logger.warning("XLM-RoBERTa classifier not configured")
            return self._fallback_response(text)
        
        try:
            result = await self._call_huggingface(text)
            
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return {
                "verdict": result.get("label", "UNKNOWN").upper(),
                "confidence": result.get("score", 0.5),
                "model": "xlm-roberta-finetuned",
                "language": language,
                "processing_time_ms": round(processing_time),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            return self._fallback_response(text)
    
    async def _call_huggingface(self, text: str) -> Dict[str, Any]:
        """Call HuggingFace Inference API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {"inputs": text}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.endpoint,
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                raise Exception(f"HuggingFace API error: {response.status_code}")
            
            result = response.json()
            
            # Handle different response formats
            if isinstance(result, list) and len(result) > 0:
                if isinstance(result[0], list):
                    # Classification with scores
                    best = max(result[0], key=lambda x: x.get("score", 0))
                    return best
                elif isinstance(result[0], dict):
                    return result[0]
            
            return {"label": "UNKNOWN", "score": 0.5}
    
    def _fallback_response(self, text: str) -> Dict[str, Any]:
        """Fallback when HuggingFace is unavailable."""
        return {
            "verdict": "PENDING_REVIEW",
            "confidence": 0.0,
            "model": "fallback",
            "message": "Classification unavailable, requires debate",
            "timestamp": datetime.utcnow().isoformat()
        }


# Global instance
classifier = Classifier()
