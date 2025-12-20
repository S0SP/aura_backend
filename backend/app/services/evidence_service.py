"""
AURA Service - Evidence Retrieval
Multi-source evidence retrieval from SERP, Pinecone, and Neo4j
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio

from app.core.config import settings
from app.core.logging import logger
from app.db.pinecone_db import search_vectors, generate_embedding
from app.db.neo4j_db import find_related_entities, query_fact_relationships


class EvidenceRetrievalService:
    """Service for retrieving evidence from multiple sources."""
    
    def __init__(self):
        self.serp_enabled = bool(settings.SERP_API_KEY)
        self.firecrawl_enabled = bool(settings.FIRECRAWL_API_KEY)
    
    async def search_all_sources(
        self,
        query: str,
        entities: List[str] = None,
        limit_per_source: int = 5
    ) -> Dict[str, Any]:
        """
        Search all evidence sources in parallel.
        
        Args:
            query: Search query
            entities: Extracted entities for graph search
            limit_per_source: Max results per source
            
        Returns:
            Aggregated results from all sources
        """
        start_time = datetime.utcnow()
        
        # Run searches in parallel
        tasks = [
            self.search_serp(query, limit_per_source),
            self.search_pinecone(query, limit_per_source),
            self.search_neo4j(entities or [], limit_per_source)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        serp_results = results[0] if not isinstance(results[0], Exception) else []
        pinecone_results = results[1] if not isinstance(results[1], Exception) else []
        neo4j_results = results[2] if not isinstance(results[2], Exception) else []
        
        # Combine and rank results
        all_results = self._rank_results(
            serp_results, pinecone_results, neo4j_results
        )
        
        elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return {
            "query": query,
            "total_results": len(all_results),
            "results": all_results,
            "sources_searched": {
                "serp": {"found": len(serp_results), "enabled": self.serp_enabled},
                "pinecone": {"found": len(pinecone_results), "enabled": True},
                "neo4j": {"found": len(neo4j_results), "enabled": True}
            },
            "search_time_ms": elapsed_ms
        }
    
    async def search_serp(
        self,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search Google using SerpAPI.
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of search results
        """
        if not self.serp_enabled:
            return []
        
        try:
            from serpapi import GoogleSearch
            
            # Add fact-check specific terms
            search_query = f"{query} fact check OR debunked OR verified"
            
            params = {
                "q": search_query,
                "api_key": settings.SERP_API_KEY,
                "num": limit,
                "gl": "in",  # India
                "hl": "en"
            }
            
            search = GoogleSearch(params)
            results = search.get_dict()
            
            organic_results = results.get("organic_results", [])
            
            formatted = []
            for i, result in enumerate(organic_results[:limit]):
                formatted.append({
                    "rank": i + 1,
                    "source": "serp",
                    "title": result.get("title", ""),
                    "url": result.get("link", ""),
                    "content_snippet": result.get("snippet", ""),
                    "domain": result.get("displayed_link", ""),
                    "relevance_score": 1.0 - (i * 0.05)  # Simple ranking
                })
            
            logger.info(f"SERP search returned {len(formatted)} results")
            return formatted
            
        except Exception as e:
            logger.error(f"SERP search failed: {e}")
            return []
    
    async def search_pinecone(
        self,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search Pinecone vector database.
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of similar facts
        """
        try:
            # Generate query embedding
            query_embedding = generate_embedding(query)
            
            # Search Pinecone
            results = await search_vectors(
                query_vector=query_embedding,
                top_k=limit,
                include_metadata=True
            )
            
            formatted = []
            for i, result in enumerate(results):
                formatted.append({
                    "rank": i + 1,
                    "source": "pinecone",
                    "title": result.metadata.get("title", "Known Fact"),
                    "url": result.metadata.get("source_url"),
                    "content_snippet": result.metadata.get("content", ""),
                    "verdict_in_source": result.metadata.get("verdict"),
                    "relevance_score": result.score
                })
            
            logger.info(f"Pinecone search returned {len(formatted)} results")
            return formatted
            
        except Exception as e:
            logger.error(f"Pinecone search failed: {e}")
            return []
    
    async def search_neo4j(
        self,
        entities: List[str],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search Neo4j knowledge graph.
        
        Args:
            entities: List of entities to query
            limit: Maximum results
            
        Returns:
            Related facts and relationships
        """
        if not entities:
            return []
        
        try:
            results = []
            
            # Find related entities for each entity
            for entity in entities[:3]:  # Limit to first 3 entities
                related = await find_related_entities(
                    entity, 
                    relationship_depth=2,
                    limit=limit // len(entities)
                )
                
                for item in related:
                    results.append({
                        "rank": len(results) + 1,
                        "source": "neo4j",
                        "title": f"Relationship: {entity}",
                        "content_snippet": f"{entity} is related to {item.get('entity')} via {', '.join(item.get('relationship_types', []))}",
                        "entities": [entity, item.get("entity")],
                        "relationship_types": item.get("relationship_types", []),
                        "relevance_score": 0.8
                    })
            
            logger.info(f"Neo4j search returned {len(results)} results")
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Neo4j search failed: {e}")
            return []
    
    async def crawl_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Crawl and extract content from a URL using Firecrawl.
        
        Args:
            url: URL to crawl
            
        Returns:
            Extracted content
        """
        if not self.firecrawl_enabled:
            return None
        
        try:
            from firecrawl import FirecrawlApp
            
            app = FirecrawlApp(api_key=settings.FIRECRAWL_API_KEY)
            result = app.scrape_url(url)
            
            return {
                "url": url,
                "title": result.get("metadata", {}).get("title", ""),
                "content": result.get("markdown", ""),
                "word_count": len(result.get("markdown", "").split()),
                "metadata": result.get("metadata", {})
            }
            
        except Exception as e:
            logger.error(f"Firecrawl failed for {url}: {e}")
            return None
    
    def _rank_results(
        self,
        serp: List[Dict],
        pinecone: List[Dict],
        neo4j: List[Dict]
    ) -> List[Dict[str, Any]]:
        """
        Combine and rank results from all sources.
        Uses k-top ranking algorithm.
        """
        # Assign source weights
        weights = {
            "serp": 0.4,
            "pinecone": 0.4,
            "neo4j": 0.2
        }
        
        all_results = []
        
        # Process each source
        for result in serp:
            result["combined_score"] = result.get("relevance_score", 0.5) * weights["serp"]
            all_results.append(result)
        
        for result in pinecone:
            result["combined_score"] = result.get("relevance_score", 0.5) * weights["pinecone"]
            all_results.append(result)
        
        for result in neo4j:
            result["combined_score"] = result.get("relevance_score", 0.5) * weights["neo4j"]
            all_results.append(result)
        
        # Sort by combined score
        all_results.sort(key=lambda x: x.get("combined_score", 0), reverse=True)
        
        # Re-assign ranks
        for i, result in enumerate(all_results):
            result["rank"] = i + 1
        
        return all_results


# Global service instance
evidence_service = EvidenceRetrievalService()
