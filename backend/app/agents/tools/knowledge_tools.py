"""
AURA LangChain Tools for Agents
Evidence retrieval, search, and analysis tools
"""

from typing import Dict, Any, List, Optional
from langchain.tools import Tool, StructuredTool
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from app.core.logging import logger


# ===========================================
# Tool Input Schemas
# ===========================================

class EvidenceSearchInput(BaseModel):
    """Input schema for evidence search tool."""
    query: str = Field(description="The claim or query to search evidence for")
    sources: List[str] = Field(
        default=["serp", "pinecone", "neo4j"],
        description="Sources to search: serp, pinecone, neo4j, firecrawl"
    )
    limit: int = Field(default=5, description="Number of results per source")


class FactCheckInput(BaseModel):
    """Input schema for fact check lookup tool."""
    claim: str = Field(description="The claim to check against verified facts")


class SourceCredibilityInput(BaseModel):
    """Input schema for source credibility assessment."""
    domain: str = Field(description="The domain to assess credibility for")


class GraphQueryInput(BaseModel):
    """Input schema for knowledge graph query."""
    entities: List[str] = Field(description="Entities to search in the knowledge graph")


# ===========================================
# Knowledge Tools (for evidence retrieval)
# ===========================================

async def search_evidence(query: str, sources: List[str] = None, limit: int = 5) -> Dict[str, Any]:
    """
    Search for evidence across multiple sources.
    Used by agents to gather supporting evidence for arguments.
    """
    try:
        from app.services.knowledge_core.aggregator import evidence_aggregator
        
        result = await evidence_aggregator.search_all(
            query=query,
            sources=sources or ["serp", "pinecone", "neo4j"],
            limit_per_source=limit
        )
        
        return {
            "success": True,
            "total_results": result.get("total_results", 0),
            "top_results": result.get("results", [])[:5],
            "sources": list(result.get("sources_searched", {}).keys())
        }
    except Exception as e:
        logger.error(f"Evidence search failed: {e}")
        return {"success": False, "error": str(e)}


async def lookup_fact(claim: str) -> Dict[str, Any]:
    """
    Look up a claim in verified facts database (Pinecone).
    Returns previously verified claims similar to the input.
    """
    try:
        from app.services.knowledge_core.pinecone_search import pinecone_search
        
        result = await pinecone_search.search(
            query=claim,
            top_k=5,
            min_score=0.75
        )
        
        matches = result.get("matches", [])
        
        if matches:
            best_match = matches[0]
            return {
                "found": True,
                "similarity": best_match.get("score", 0),
                "previous_verdict": best_match.get("metadata", {}).get("verdict", "Unknown"),
                "previous_evidence": best_match.get("metadata", {}).get("evidence", ""),
                "source": best_match.get("metadata", {}).get("source", ""),
                "all_matches": len(matches)
            }
        else:
            return {
                "found": False,
                "message": "No similar verified claims found"
            }
    except Exception as e:
        logger.error(f"Fact lookup failed: {e}")
        return {"found": False, "error": str(e)}


async def assess_source_credibility(domain: str) -> Dict[str, Any]:
    """
    Assess the credibility of a source domain.
    """
    # Trusted domains with high authority
    TRUSTED_DOMAINS = {
        "who.int": {"score": 98, "type": "International Health Authority"},
        "cdc.gov": {"score": 97, "type": "US Health Authority"},
        "pib.gov.in": {"score": 95, "type": "Indian Government"},
        "mohfw.gov.in": {"score": 95, "type": "Indian Health Ministry"},
        "reuters.com": {"score": 92, "type": "News Agency"},
        "factcheck.org": {"score": 90, "type": "Fact-Checking Organization"},
        "snopes.com": {"score": 88, "type": "Fact-Checking Organization"},
        "altnews.in": {"score": 85, "type": "Indian Fact-Checker"},
        "boomlive.in": {"score": 85, "type": "Indian Fact-Checker"},
    }
    
    domain_clean = domain.lower().replace("www.", "")
    
    if domain_clean in TRUSTED_DOMAINS:
        info = TRUSTED_DOMAINS[domain_clean]
        return {
            "domain": domain_clean,
            "credibility_score": info["score"],
            "type": info["type"],
            "trusted": True,
            "recommendation": "Highly reliable source"
        }
    elif ".gov" in domain_clean or ".edu" in domain_clean:
        return {
            "domain": domain_clean,
            "credibility_score": 80,
            "type": "Government/Education",
            "trusted": True,
            "recommendation": "Generally reliable"
        }
    elif ".org" in domain_clean:
        return {
            "domain": domain_clean,
            "credibility_score": 65,
            "type": "Organization",
            "trusted": False,
            "recommendation": "Verify against other sources"
        }
    else:
        return {
            "domain": domain_clean,
            "credibility_score": 50,
            "type": "Unknown",
            "trusted": False,
            "recommendation": "Use caution, verify claims"
        }


async def query_knowledge_graph(entities: List[str]) -> Dict[str, Any]:
    """
    Query the knowledge graph for entity relationships.
    """
    try:
        from app.services.knowledge_core.neo4j_search import neo4j_search
        
        result = await neo4j_search.query(
            entities=entities,
            relationship_depth=2,
            include_facts=True
        )
        
        return {
            "success": True,
            "nodes_found": len(result.get("nodes", [])),
            "relationships": result.get("relationships", [])[:5],
            "inference": result.get("graph_inference", ""),
            "related_facts": result.get("related_facts", [])[:3]
        }
    except Exception as e:
        logger.error(f"Graph query failed: {e}")
        return {"success": False, "error": str(e)}


# ===========================================
# Create LangChain Tools
# ===========================================

def create_evidence_search_tool() -> Tool:
    """Create evidence search tool for agents."""
    return Tool(
        name="evidence_search",
        description=(
            "Search for evidence related to a claim. Use this to find supporting or "
            "refuting evidence from trusted sources like WHO, CDC, Reuters, etc. "
            "Input should be the claim or topic to search for."
        ),
        func=lambda q: search_evidence(q),  # Sync wrapper
        coroutine=search_evidence
    )


def create_fact_lookup_tool() -> Tool:
    """Create fact lookup tool for agents."""
    return Tool(
        name="fact_lookup",
        description=(
            "Look up a claim in the database of previously verified facts. "
            "Use this to check if a similar claim has been fact-checked before. "
            "Input should be the claim text."
        ),
        func=lambda q: lookup_fact(q),
        coroutine=lookup_fact
    )


def create_credibility_tool() -> Tool:
    """Create source credibility assessment tool."""
    return Tool(
        name="assess_credibility",
        description=(
            "Assess the credibility of a source domain. Use this to evaluate "
            "how trustworthy a source is. Input should be the domain name."
        ),
        func=lambda d: assess_source_credibility(d),
        coroutine=assess_source_credibility
    )


def create_graph_query_tool() -> Tool:
    """Create knowledge graph query tool."""
    return Tool(
        name="query_knowledge_graph",
        description=(
            "Query the knowledge graph for relationships between entities. "
            "Use this to understand how concepts are related. "
            "Input should be a comma-separated list of entities."
        ),
        func=lambda e: query_knowledge_graph(e.split(",") if isinstance(e, str) else e),
        coroutine=lambda e: query_knowledge_graph(e.split(",") if isinstance(e, str) else e)
    )


def get_all_agent_tools() -> List[Tool]:
    """Get all tools available to debate agents."""
    return [
        create_evidence_search_tool(),
        create_fact_lookup_tool(),
        create_credibility_tool(),
        create_graph_query_tool()
    ]
