"""
AURA K-Top Ranker Service
Weighted ranking algorithm for evidence prioritization
"""

from typing import Dict, Any, List
from datetime import datetime

from app.core.logging import logger


class KTopRanker:
    """
    K-Top ranking algorithm for evidence prioritization.
    Combines relevance, authority, and recency scores.
    """
    
    DEFAULT_WEIGHTS = {
        "relevance": 0.4,
        "authority": 0.35,
        "recency": 0.25
    }
    
    def __init__(self):
        pass
    
    def rank(
        self,
        results: List[Dict],
        k: int = 10,
        weights: Dict[str, float] = None
    ) -> List[Dict]:
        """
        Rank results using weighted scoring and return top K.
        
        Args:
            results: List of evidence items to rank
            k: Number of top results to return
            weights: Scoring weights for relevance, authority, recency
        """
        if not results:
            return []
        
        if weights is None:
            weights = self.DEFAULT_WEIGHTS
        
        # Normalize weights to sum to 1
        total_weight = sum(weights.values())
        weights = {k: v / total_weight for k, v in weights.items()}
        
        # Calculate combined score for each result
        scored_results = []
        for result in results:
            combined_score = self._calculate_combined_score(result, weights)
            result["combined_score"] = round(combined_score, 4)
            scored_results.append(result)
        
        # Sort by combined score (descending)
        scored_results.sort(key=lambda x: x.get("combined_score", 0), reverse=True)
        
        # Add rank and return top K
        ranked = []
        for i, result in enumerate(scored_results[:k]):
            result["rank"] = i + 1
            ranked.append(result)
        
        return ranked
    
    def _calculate_combined_score(
        self,
        result: Dict,
        weights: Dict[str, float]
    ) -> float:
        """Calculate weighted combined score."""
        
        # Get individual scores (normalize to 0-1)
        relevance = self._get_relevance_score(result)
        authority = self._get_authority_score(result)
        recency = self._get_recency_score(result)
        
        # Weighted combination
        combined = (
            weights.get("relevance", 0.4) * relevance +
            weights.get("authority", 0.35) * authority +
            weights.get("recency", 0.25) * recency
        )
        
        return combined
    
    def _get_relevance_score(self, result: Dict) -> float:
        """Extract or estimate relevance score."""
        # Check various score fields
        if "relevance_score" in result:
            return min(result["relevance_score"], 1.0)
        if "similarity_score" in result:
            return min(result["similarity_score"], 1.0)
        if "score" in result:
            return min(result["score"], 1.0)
        return 0.5  # Default
    
    def _get_authority_score(self, result: Dict) -> float:
        """Extract or estimate authority score."""
        if "domain_authority" in result:
            # Normalize from 0-100 to 0-1
            return result["domain_authority"] / 100.0
        
        # Estimate based on source type
        source_type = result.get("source_type", "")
        if source_type == "neo4j" or source_type == "neo4j_inference":
            return 0.9  # Graph-verified
        elif source_type == "pinecone":
            return 0.85  # Pre-verified facts
        elif source_type == "serp":
            if result.get("is_trusted", False):
                return 0.9
            return 0.6
        
        return 0.5  # Default
    
    def _get_recency_score(self, result: Dict) -> float:
        """Calculate recency score based on date."""
        recency = result.get("recency") or result.get("published_date")
        
        if not recency:
            return 0.5  # Default for unknown dates
        
        try:
            if isinstance(recency, str):
                # Try parsing date
                from dateutil import parser
                date = parser.parse(recency)
                days_old = (datetime.now() - date).days
            else:
                days_old = 365  # Default to 1 year old
            
            # Score: 1.0 for today, 0.5 for 1 year, 0.1 for 5 years
            if days_old <= 7:
                return 1.0
            elif days_old <= 30:
                return 0.9
            elif days_old <= 90:
                return 0.8
            elif days_old <= 365:
                return 0.6
            else:
                return max(0.1, 0.5 - (days_old - 365) / 1825)
        except:
            return 0.5


# Global instance
k_top_ranker = KTopRanker()
