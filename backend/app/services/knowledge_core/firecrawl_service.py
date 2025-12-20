"""
AURA Firecrawl Service
Web scraping and content extraction via Firecrawl API
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx

from app.core.logging import logger
from app.core.config import settings


class FirecrawlService:
    """
    Web scraping service using Firecrawl API.
    Extracts clean content from URLs for evidence gathering.
    """
    
    FIRECRAWL_API_URL = "https://api.firecrawl.dev/v0/scrape"
    
    def __init__(self):
        self.api_key = settings.FIRECRAWL_API_KEY
        self.enabled = bool(self.api_key)
    
    async def crawl(
        self,
        urls: List[str],
        extract_main_content: bool = True,
        extract_metadata: bool = True,
        extract_structured_data: bool = True
    ) -> Dict[str, Any]:
        """
        Crawl and extract content from URLs.
        """
        if not self.enabled:
            logger.warning("Firecrawl API key not configured")
            return {"crawled": [], "failed": [], "error": "Firecrawl not configured"}
        
        crawled = []
        failed = []
        
        for url in urls[:10]:  # Limit to 10 URLs
            try:
                result = await self._crawl_url(url)
                crawled.append(result)
            except Exception as e:
                logger.error(f"Failed to crawl {url}: {e}")
                failed.append({"url": url, "error": str(e)})
        
        return {
            "crawled": crawled,
            "failed": failed,
            "total_crawled": len(crawled),
            "total_failed": len(failed)
        }
    
    async def _crawl_url(self, url: str) -> Dict[str, Any]:
        """Crawl a single URL using Firecrawl."""
        start_time = datetime.utcnow()
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "url": url,
            "pageOptions": {
                "includeHtml": False,
                "includeRawHtml": False,
                "onlyMainContent": True,
                "screenshot": False
            }
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                self.FIRECRAWL_API_URL,
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                raise Exception(f"Firecrawl error: {response.status_code}")
            
            data = response.json()
        
        crawl_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        result = data.get("data", {})
        
        content = result.get("markdown", result.get("content", ""))
        
        return {
            "url": url,
            "status": "success",
            "title": result.get("metadata", {}).get("title", ""),
            "main_content": content[:5000],  # Limit content length
            "word_count": len(content.split()),
            "metadata": {
                "author": result.get("metadata", {}).get("author", ""),
                "published_date": result.get("metadata", {}).get("publishedTime", ""),
                "description": result.get("metadata", {}).get("description", "")
            },
            "crawl_time_ms": round(crawl_time)
        }
    
    async def crawl_single(self, url: str) -> Optional[Dict[str, Any]]:
        """Crawl a single URL and return content."""
        result = await self.crawl([url])
        if result["crawled"]:
            return result["crawled"][0]
        return None


# Global instance
firecrawl_service = FirecrawlService()
