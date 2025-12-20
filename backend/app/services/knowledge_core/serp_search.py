"""
AURA SERP Search Service
Google Search API integration via SerpAPI
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx

from app.core.logging import logger
from app.core.config import settings


class SerpSearch:
    """
    Google SERP API search for fact-check articles.
    Uses SerpAPI for reliable search results.
    """
    
    SERP_API_URL = "https://serpapi.com/search"
    
    # Authoritative fact-checking domains
    TRUSTED_DOMAINS = [
        "who.int", "cdc.gov", "reuters.com", "factcheck.org",
        "snopes.com", "altnews.in", "boomlive.in", "thequint.com",
        "pib.gov.in", "mohfw.gov.in"
    ]
    
    def __init__(self):
        self.api_key = settings.SERP_API_KEY
        self.enabled = bool(self.api_key)
    
    async def search(
        self,
        query: str,
        num_results: int = 10,
        site_filters: List[str] = None,
        date_range: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Search Google for fact-check articles related to a claim.
        """
        if not self.enabled:
            logger.warning("SerpAPI key not configured")
            return {"results": [], "error": "SerpAPI not configured"}
        
        start_time = datetime.utcnow()
        
        # Build query with site filters
        full_query = f"{query} fact check"
        if site_filters:
            site_query = " OR ".join([f"site:{s}" for s in site_filters[:5]])
            full_query = f"{query} ({site_query})"
        
        params = {
            "q": full_query,
            "api_key": self.api_key,
            "num": min(num_results, 20),
            "engine": "google"
        }
        
        # Add date range if specified
        if date_range:
            if date_range.get("from"):
                params["tbs"] = f"cdr:1,cd_min:{date_range['from']}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.SERP_API_URL, params=params)
                
                if response.status_code != 200:
                    raise Exception(f"SerpAPI error: {response.status_code}")
                
                data = response.json()
                
            results = self._parse_results(data)
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return {
                "query": query,
                "results": results,
                "total_results": len(results),
                "search_time_ms": round(processing_time)
            }
            
        except Exception as e:
            logger.error(f"SERP search failed: {e}")
            return {"results": [], "error": str(e)}
    
    def _parse_results(self, data: Dict) -> List[Dict]:
        """Parse SerpAPI response into standardized format."""
        results = []
        
        for item in data.get("organic_results", []):
            domain = self._extract_domain(item.get("link", ""))
            
            results.append({
                "position": item.get("position", 0),
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "domain": domain,
                "is_trusted": domain in self.TRUSTED_DOMAINS,
                "domain_authority": self._estimate_authority(domain)
            })
        
        return results
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc.replace("www.", "")
        except:
            return ""
    
    def _estimate_authority(self, domain: str) -> int:
        """Estimate domain authority (simplified)."""
        if domain in ["who.int", "cdc.gov", "pib.gov.in"]:
            return 98
        elif domain in self.TRUSTED_DOMAINS:
            return 85
        elif ".gov" in domain or ".edu" in domain:
            return 80
        elif ".org" in domain:
            return 70
        else:
            return 50


# Global instance
serp_search = SerpSearch()
