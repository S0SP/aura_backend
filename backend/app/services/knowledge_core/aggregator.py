"""
AURA Evidence Aggregator Service
Aggregates evidence from multiple sources with scoring
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from app.core.logging import logger
from app.services.knowledge_core.serp_search import serp_search
from app.services.knowledge_core.pinecone_search import pinecone_search
from app.services.knowledge_core.neo4j_search import neo4j_search
from app.services.knowledge_core.k_top_ranker import k_top_ranker


class EvidenceAggregator:
    """
    Aggregates evidence from SERP, Pinecone, Neo4j, and Firecrawl.
    Provides unified search with K-Top ranking.
    """
    
    def __init__(self):
        pass
    
    async def search_all(
        self,
        query: str,
        sources: List[str] = None,
        limit_per_source: int = 5,
        ranking_weights: Dict[str, float] = None
    ) -> Dict[str, Any]:
        """
        Search all evidence sources and aggregate results.
        """
        if sources is None:
            sources = ["serp", "pinecone", "neo4j"]
        
        if ranking_weights is None:
            ranking_weights = {
                "relevance": 0.4,
                "authority": 0.35,
                "recency": 0.25
            }
        
        start_time = datetime.utcnow()
        all_results = []
        source_stats = {}
        
        # Search each source in parallel concept (sequential for simplicity)
        if "serp" in sources:
            serp_result = await serp_search.search(query, num_results=limit_per_source)
            serp_items = self._normalize_serp_results(serp_result.get("results", []))
            all_results.extend(serp_items)
            source_stats["serp"] = {
                "found": len(serp_items),
                "time_ms": serp_result.get("search_time_ms", 0)
            }
        
        if "pinecone" in sources:
            pinecone_result = await pinecone_search.search(query, top_k=limit_per_source)
            pinecone_items = self._normalize_pinecone_results(pinecone_result.get("matches", []))
            all_results.extend(pinecone_items)
            source_stats["pinecone"] = {
                "found": len(pinecone_items),
                "time_ms": pinecone_result.get("search_time_ms", 0)
            }
        
        if "neo4j" in sources:
            # Extract entities from query for graph search
            entities = self._extract_entities(query)
            neo4j_result = await neo4j_search.query(entities)
            neo4j_items = self._normalize_neo4j_results(neo4j_result)
            all_results.extend(neo4j_items)
            source_stats["neo4j"] = {
                "found": len(neo4j_items),
                "time_ms": neo4j_result.get("query_time_ms", 0)
            }
        
        # Rank all results using K-Top ranking
        ranked_results = k_top_ranker.rank(
            results=all_results,
            k=10,
            weights=ranking_weights
        )
        
        total_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return {
            "query": query,
            "total_results": len(all_results),
            "top_k_results": len(ranked_results),
            "results": ranked_results,
            "sources_searched": source_stats,
            "search_time_ms": round(total_time)
        }
    
    def _normalize_serp_results(self, results: List[Dict]) -> List[Dict]:
        """Normalize SERP results to common format."""
        normalized = []
        for r in results:
            normalized.append({
                "source_type": "serp",
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content_snippet": r.get("snippet", ""),
                "domain": r.get("domain", ""),
                "domain_authority": r.get("domain_authority", 50),
                "relevance_score": 0.8,  # Default for SERP
                "recency": None
            })
        return normalized
    
    def _normalize_pinecone_results(self, matches: List[Dict]) -> List[Dict]:
        """Normalize Pinecone results to common format."""
        normalized = []
        for m in matches:
            metadata = m.get("metadata", {})
            normalized.append({
                "source_type": "pinecone",
                "claim": metadata.get("claim", ""),
                "verdict": metadata.get("verdict", ""),
                "evidence": metadata.get("evidence", ""),
                "source": metadata.get("source", ""),
                "similarity_score": m.get("score", 0),
                "relevance_score": m.get("score", 0),
                "domain_authority": 85  # Pre-verified facts
            })
        return normalized
    
    def _normalize_neo4j_results(self, result: Dict) -> List[Dict]:
        """Normalize Neo4j results to common format."""
        normalized = []
        
        # Convert related facts
        for fact in result.get("related_facts", []):
            normalized.append({
                "source_type": "neo4j",
                "claim": fact.get("claim", ""),
                "verdict": fact.get("verdict", ""),
                "source": fact.get("source", ""),
                "graph_inference": result.get("graph_inference", ""),
                "relevance_score": 0.85,
                "domain_authority": 90  # Graph-verified
            })
        
        # Add graph inference as a result if available
        if result.get("graph_inference"):
            normalized.append({
                "source_type": "neo4j_inference",
                "inference": result["graph_inference"],
                "nodes": len(result.get("nodes", [])),
                "relationships": len(result.get("relationships", [])),
                "relevance_score": 0.9,
                "domain_authority": 90
            })
        
        return normalized
    
    def _extract_entities(self, query: str) -> List[str]:
        """Extract key entities from query for graph search."""
        # Simple extraction - in production use NER
        words = query.split()
        # Filter to capitalized words or known entity patterns
        entities = [w for w in words if w[0].isupper() or len(w) > 5]
        return entities[:5]


# Global instance
evidence_aggregator = EvidenceAggregator()
