"""
AURA Service - Classification
XLM-RoBERTa based claim classification via HuggingFace
"""

from typing import Dict, Any, Optional
from datetime import datetime
import httpx

from app.core.config import settings
from app.core.logging import logger
from app.models.verification import VerdictType, QuickClassificationResult


class ClassificationService:
    """Service for quick claim classification using XLM-RoBERTa."""
    
    # Category mapping
    CATEGORIES = {
        "health": ["vaccine", "covid", "virus", "medicine", "cure", "treatment", "disease"],
        "political": ["election", "government", "minister", "party", "vote", "parliament"],
        "financial": ["bank", "money", "tax", "scheme", "fraud", "investment", "rupee"],
        "science": ["research", "study", "scientist", "climate", "space", "technology"],
        "social": ["community", "religion", "caste", "riot", "protest"],
        "disaster": ["earthquake", "flood", "cyclone", "accident", "emergency"]
    }
    
    # Verdict mapping from model outputs
    VERDICT_MAP = {
        "true": VerdictType.TRUE,
        "false": VerdictType.FALSE,
        "misleading": VerdictType.MISLEADING,
        "partially_true": VerdictType.PARTIALLY_TRUE,
        "half_true": VerdictType.PARTIALLY_TRUE,
        "unverified": VerdictType.UNVERIFIABLE,
        "unverifiable": VerdictType.UNVERIFIABLE,
        "unknown": VerdictType.UNVERIFIABLE
    }
    
    def __init__(self):
        self.endpoint = settings.XLM_ROBERTA_ENDPOINT
        self.api_key = settings.HUGGINGFACE_API_KEY
        self.enabled = bool(self.endpoint and self.api_key)
    
    async def classify(
        self,
        claim: str,
        language: str = "en"
    ) -> QuickClassificationResult:
        """
        Classify a claim using XLM-RoBERTa.
        
        Args:
            claim: The claim text to classify
            language: Language code
            
        Returns:
            QuickClassificationResult
        """
        start_time = datetime.utcnow()
        
        # Detect category based on keywords
        category = self._detect_category(claim)
        
        if not self.enabled:
            # Fallback to heuristic classification
            return await self._heuristic_classify(claim, category, start_time)
        
        try:
            # Call HuggingFace Inference API
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.endpoint,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={"inputs": claim}
                )
                
                if response.status_code != 200:
                    logger.warning(f"Classification API returned {response.status_code}")
                    return await self._heuristic_classify(claim, category, start_time)
                
                results = response.json()
                
                # Parse model output
                verdict, confidence = self._parse_model_output(results)
                
                elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                
                return QuickClassificationResult(
                    model="xlm-roberta",
                    verdict=verdict,
                    confidence=confidence,
                    category=category,
                    time_ms=elapsed_ms
                )
                
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            return await self._heuristic_classify(claim, category, start_time)
    
    def _parse_model_output(
        self,
        results: Any
    ) -> tuple[VerdictType, float]:
        """Parse model output to verdict and confidence."""
        try:
            # Handle different HuggingFace output formats
            if isinstance(results, list) and len(results) > 0:
                if isinstance(results[0], list):
                    # Multi-label classification
                    top_result = max(results[0], key=lambda x: x.get("score", 0))
                else:
                    top_result = max(results, key=lambda x: x.get("score", 0))
                
                label = top_result.get("label", "unknown").lower()
                score = top_result.get("score", 0.5)
                
                verdict = self.VERDICT_MAP.get(label, VerdictType.UNVERIFIABLE)
                return verdict, score
            
            return VerdictType.UNVERIFIABLE, 0.5
            
        except Exception as e:
            logger.error(f"Failed to parse model output: {e}")
            return VerdictType.UNVERIFIABLE, 0.5
    
    def _detect_category(self, claim: str) -> str:
        """Detect claim category based on keywords."""
        claim_lower = claim.lower()
        
        for category, keywords in self.CATEGORIES.items():
            for keyword in keywords:
                if keyword in claim_lower:
                    return category
        
        return "other"
    
    async def _heuristic_classify(
        self,
        claim: str,
        category: str,
        start_time: datetime
    ) -> QuickClassificationResult:
        """
        Fallback heuristic classification when API is unavailable.
        
        Uses keyword patterns and common misinformation indicators.
        """
        claim_lower = claim.lower()
        
        # Misinformation indicators
        high_confidence_false_patterns = [
            "5g causes",
            "5g spreads",
            "vaccine causes autism",
            "microchip in vaccine",
            "flat earth",
            "moon landing fake"
        ]
        
        # Check for known false claims
        for pattern in high_confidence_false_patterns:
            if pattern in claim_lower:
                elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                return QuickClassificationResult(
                    model="heuristic",
                    verdict=VerdictType.FALSE,
                    confidence=0.85,
                    category=category,
                    time_ms=elapsed_ms
                )
        
        # Sensationalism indicators
        sensational_words = ["shocking", "breaking", "unbelievable", "must see", "they don't want you to know"]
        sensational_count = sum(1 for word in sensational_words if word in claim_lower)
        
        if sensational_count >= 2:
            elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            return QuickClassificationResult(
                model="heuristic",
                verdict=VerdictType.MISLEADING,
                confidence=0.6,
                category=category,
                time_ms=elapsed_ms
            )
        
        # Default: Unverifiable
        elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        return QuickClassificationResult(
            model="heuristic",
            verdict=VerdictType.UNVERIFIABLE,
            confidence=0.5,
            category=category,
            time_ms=elapsed_ms
        )
    
    async def batch_classify(
        self,
        claims: list[str]
    ) -> list[QuickClassificationResult]:
        """
        Classify multiple claims.
        
        Args:
            claims: List of claim texts
            
        Returns:
            List of classification results
        """
        results = []
        for claim in claims:
            result = await self.classify(claim)
            results.append(result)
        return results


# Global service instance
classification_service = ClassificationService()
