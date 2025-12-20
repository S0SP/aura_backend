"""
AURA Agent Tools - Search Tool
Tool for agents to search for evidence
"""

from typing import List, Dict, Any
from app.services.evidence_service import evidence_service
from app.core.logging import logger


class SearchTool:
    """Tool for searching evidence across multiple sources."""
    
    name = "search_evidence"
    description = """Search for evidence to support or refute a claim.
    Use this tool to find relevant information from web search, knowledge base, and fact-check databases.
    Input: Search query string
    Output: List of relevant evidence items with sources and credibility scores"""
    
    def __init__(self):
        self.evidence_service = evidence_service
    
    async def run(self, query: str, entities: List[str] = None) -> List[Dict[str, Any]]:
        """
        Execute a search for evidence.
        
        Args:
            query: Search query
            entities: Optional list of entities to include in graph search
            
        Returns:
            List of evidence items
        """
        try:
            result = await self.evidence_service.search_all_sources(
                query=query,
                entities=entities,
                limit_per_source=5
            )
            return result.get("results", [])
        except Exception as e:
            logger.error(f"Search tool failed: {e}")
            return []
    
    def _format_for_agent(self, results: List[Dict]) -> str:
        """Format results as text for agent consumption."""
        if not results:
            return "No relevant evidence found."
        
        formatted = "SEARCH RESULTS:\n\n"
        for i, r in enumerate(results[:5], 1):
            formatted += f"{i}. {r.get('title', 'Untitled')}\n"
            formatted += f"   Source: {r.get('source', 'Unknown')} | Score: {r.get('relevance_score', 0):.2f}\n"
            formatted += f"   {r.get('content_snippet', '')[:200]}...\n\n"
        
        return formatted


class FactCheckTool:
    """Tool for checking if a claim has been fact-checked before."""
    
    name = "check_factchecks"
    description = """Check if a claim has been previously fact-checked by reputable organizations.
    Use this to find existing verdicts on similar claims.
    Input: The claim to check
    Output: Previous fact-check results if found"""
    
    async def run(self, claim: str) -> List[Dict[str, Any]]:
        """
        Search for existing fact-checks.
        
        Args:
            claim: The claim to check
            
        Returns:
            List of matching fact-checks
        """
        try:
            # Search with fact-check specific query
            query = f"{claim} site:factcheck.org OR site:snopes.com OR site:altnews.in OR site:boomlive.in"
            result = await evidence_service.search_serp(query, limit=5)
            return result
        except Exception as e:
            logger.error(f"Fact-check tool failed: {e}")
            return []


class SourceCredibilityTool:
    """Tool for checking source credibility."""
    
    name = "check_source_credibility"
    description = """Check the credibility of a source.
    Input: Source URL or name
    Output: Credibility assessment"""
    
    # Known credibility scores
    KNOWN_SOURCES = {
        # High credibility
        "reuters.com": {"score": 9, "type": "news"},
        "apnews.com": {"score": 9, "type": "news"},
        "bbc.com": {"score": 8, "type": "news"},
        "who.int": {"score": 9, "type": "official"},
        "gov.in": {"score": 8, "type": "government"},
        "pib.gov.in": {"score": 9, "type": "government"},
        "factcheck.org": {"score": 9, "type": "factcheck"},
        "snopes.com": {"score": 8, "type": "factcheck"},
        "altnews.in": {"score": 8, "type": "factcheck"},
        "boomlive.in": {"score": 8, "type": "factcheck"},
        
        # Medium credibility
        "thehindu.com": {"score": 7, "type": "news"},
        "indianexpress.com": {"score": 7, "type": "news"},
        "ndtv.com": {"score": 7, "type": "news"},
        "timesofindia.com": {"score": 6, "type": "news"},
        "wikipedia.org": {"score": 6, "type": "encyclopedia"},
        
        # Low credibility
        "facebook.com": {"score": 3, "type": "social"},
        "twitter.com": {"score": 3, "type": "social"},
        "whatsapp": {"score": 2, "type": "messaging"},
        "youtube.com": {"score": 4, "type": "video"}
    }
    
    def run(self, source: str) -> Dict[str, Any]:
        """
        Check source credibility.
        
        Args:
            source: URL or source name
            
        Returns:
            Credibility assessment
        """
        source_lower = source.lower()
        
        for domain, info in self.KNOWN_SOURCES.items():
            if domain in source_lower:
                return {
                    "source": source,
                    "domain": domain,
                    "credibility_score": info["score"],
                    "source_type": info["type"],
                    "recommendation": self._get_recommendation(info["score"])
                }
        
        # Unknown source
        return {
            "source": source,
            "credibility_score": 5,
            "source_type": "unknown",
            "recommendation": "Verify independently - unknown source credibility"
        }
    
    def _get_recommendation(self, score: int) -> str:
        if score >= 8:
            return "Highly credible - can be cited with confidence"
        elif score >= 6:
            return "Generally reliable - verify key claims"
        elif score >= 4:
            return "Use with caution - seek corroboration"
        else:
            return "Low credibility - do not rely on without verification"


# Tool instances
search_tool = SearchTool()
factcheck_tool = FactCheckTool()
credibility_tool = SourceCredibilityTool()
