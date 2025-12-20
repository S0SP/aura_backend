"""
AURA Claim Categorizer Service
Categorizes claims by domain for system prompt switching
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from app.core.logging import logger


class ClaimCategorizer:
    """
    Categorizes claims by domain to enable system prompt switching.
    Categories: health, political, scientific, economic, social, religious, other
    """
    
    # Domain keywords for categorization
    CATEGORY_KEYWORDS = {
        "health": [
            "covid", "vaccine", "medicine", "doctor", "hospital", "disease",
            "virus", "cancer", "treatment", "cure", "ayurveda",
            "ivermectin", "hydroxychloroquine", "immunity", "infection", "pandemic",
            "who", "cdc", "icmr", "aiims", "health ministry"
        ],
        "political": [
            "election", "vote", "bjp", "congress", "aap", "modi", "rahul gandhi",
            "parliament", "government", "minister", "mla", "mp", "party",
            "president", "prime minister", "chief minister", "corruption",
            "scam", "policy", "bill", "law", "constitution"
        ],
        "scientific": [
            "research", "study", "scientist", "nasa", "isro", "space",
            "climate", "environment", "global warming", "earth", "physics",
            "chemistry", "biology", "experiment", "discovery", "technology",
            "ai", "quantum", "nuclear"
        ],
        "economic": [
            "rupee", "dollar", "stock", "market", "gdp", "inflation",
            "rbi", "bank", "loan", "tax", "gst", "budget", "finance",
            "economy", "unemployment", "job", "salary", "price", "rate"
        ],
        "social": [
            "caste", "reservation", "dalit", "obc", "sc", "st", "minority",
            "muslim", "hindu", "christian", "sikh", "riot", "communal",
            "lynching", "protest", "farmer", "women", "rape", "crime"
        ],
        "religious": [
            "temple", "mosque", "church", "gurdwara", "god", "prayer",
            "ram", "krishna", "allah", "jesus", "guru", "saint", "baba",
            "pilgrimage", "festival", "diwali", "eid", "christmas"
        ]
    }
    
    # Indian context keywords
    INDIAN_KEYWORDS = [
        "india", "indian", "bharat", "delhi", "mumbai", "chennai", "kolkata",
        "bangalore", "hyderabad", "pune", "ahmedabad", "jaipur", "lucknow",
        "modi", "bjp", "congress", "aap", "rss", "jnu", "iit", "upsc"
    ]
    
    def __init__(self):
        pass
    
    def categorize(self, claim: str) -> Dict[str, Any]:
        """
        Categorize a claim by domain.
        
        Returns:
            category: Primary category
            subcategories: Related categories
            is_indian_context: Whether claim relates to India
            confidence: Categorization confidence
        """
        claim_lower = claim.lower()
        
        # Score each category
        category_scores = {}
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in claim_lower)
            if score > 0:
                category_scores[category] = score
        
        # Determine primary category
        if category_scores:
            primary = max(category_scores, key=category_scores.get)
            confidence = min(category_scores[primary] / 5, 1.0)  # Normalize to max 1.0
            subcategories = [c for c, s in category_scores.items() if c != primary and s > 0]
        else:
            primary = "other"
            confidence = 0.5
            subcategories = []
        
        # Check Indian context
        is_indian = any(kw in claim_lower for kw in self.INDIAN_KEYWORDS)
        
        return {
            "category": primary,
            "subcategories": subcategories[:2],  # Max 2 subcategories
            "is_indian_context": is_indian,
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_prompt_mode(self, category: str) -> str:
        """
        Get the appropriate prompt mode for agent switching.
        """
        prompt_modes = {
            "health": "HEALTH_EXPERT",
            "political": "POLITICAL_ANALYST",
            "scientific": "SCIENCE_EXPERT",
            "economic": "ECONOMICS_ANALYST",
            "social": "SOCIAL_ANALYST",
            "religious": "CULTURAL_EXPERT",
            "other": "GENERAL_ANALYST"
        }
        return prompt_modes.get(category, "GENERAL_ANALYST")


# Global instance
claim_categorizer = ClaimCategorizer()
