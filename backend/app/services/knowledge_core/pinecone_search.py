"""
AURA Pinecone Search Service
Vector similarity search for semantic fact matching
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from app.core.logging import logger
from app.core.config import settings


class PineconeSearch:
    """
    Vector similarity search in Pinecone for semantic fact matching.
    Finds similar previously verified claims.
    """
    
    def __init__(self):
        self.api_key = settings.PINECONE_API_KEY
        self.index_name = settings.PINECONE_INDEX_NAME
        self.enabled = bool(self.api_key)
        self._index = None
    
    async def search(
        self,
        query: str,
        top_k: int = 10,
        category: str = None,
        min_score: float = 0.7
    ) -> Dict[str, Any]:
        """
        Search for similar claims in Pinecone vector database.
        """
        if not self.enabled:
            logger.warning("Pinecone API key not configured")
            return {"matches": [], "error": "Pinecone not configured"}
        
        start_time = datetime.utcnow()
        
        try:
            # Get embedding for query
            embedding = await self._get_embedding(query)
            
            # Search Pinecone
            matches = await self._query_pinecone(
                embedding=embedding,
                top_k=top_k,
                category=category,
                min_score=min_score
            )
            
            search_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return {
                "query": query,
                "matches": matches,
                "total_matches": len(matches),
                "search_time_ms": round(search_time)
            }
            
        except Exception as e:
            logger.error(f"Pinecone search failed: {e}")
            return {"matches": [], "error": str(e)}
    
    async def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding using Google Generative AI (lightweight, API-based)."""
        try:
            import google.generativeai as genai
            from app.core.config import settings
            
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            result = genai.embed_content(
                model="models/embedding-001",
                content=text,
                task_type="retrieval_query"
            )
            return result['embedding']
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return []
    
    async def _query_pinecone(
        self,
        embedding: List[float],
        top_k: int,
        category: str,
        min_score: float
    ) -> List[Dict]:
        """Query Pinecone index."""
        try:
            from pinecone import Pinecone
            
            pc = Pinecone(api_key=self.api_key)
            index = pc.Index(self.index_name)
            
            filter_dict = None
            if category:
                filter_dict = {"category": category}
            
            results = index.query(
                vector=embedding,
                top_k=top_k,
                include_metadata=True,
                filter=filter_dict
            )
            
            matches = []
            for match in results.get("matches", []):
                if match.get("score", 0) >= min_score:
                    matches.append({
                        "id": match.get("id"),
                        "score": round(match.get("score", 0), 4),
                        "metadata": match.get("metadata", {})
                    })
            
            return matches
            
        except Exception as e:
            logger.error(f"Pinecone query failed: {e}")
            return []
    
    async def upsert(
        self,
        id: str,
        text: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """Add or update a fact in Pinecone."""
        if not self.enabled:
            return False
        
        try:
            from pinecone import Pinecone
            
            embedding = await self._get_embedding(text)
            if not embedding:
                return False
            
            pc = Pinecone(api_key=self.api_key)
            index = pc.Index(self.index_name)
            
            index.upsert(vectors=[{
                "id": id,
                "values": embedding,
                "metadata": metadata
            }])
            
            return True
            
        except Exception as e:
            logger.error(f"Pinecone upsert failed: {e}")
            return False


# Global instance
pinecone_search = PineconeSearch()
