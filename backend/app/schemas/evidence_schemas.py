"""
AURA Pydantic Schemas - Evidence/Knowledge Core
Request and response models for evidence endpoints
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class EvidenceSearchRequest(BaseModel):
    """Request model for evidence search."""
    query: str = Field(..., description="Search query")
    sources: List[str] = Field(
        default=["serp", "pinecone", "neo4j"],
        description="Sources to search"
    )
    limit_per_source: int = Field(5, ge=1, le=20)
    include_sources: Optional[Dict[str, Any]] = Field(None)
    ranking: Optional[Dict[str, Any]] = Field(None)


class EvidenceResult(BaseModel):
    """Single evidence result."""
    rank: int
    source_type: str
    title: Optional[str] = None
    url: Optional[str] = None
    content_snippet: Optional[str] = None
    verdict_in_source: Optional[str] = None
    domain_authority: Optional[int] = None
    relevance_score: float
    combined_score: float


class EvidenceSearchResponse(BaseModel):
    """Response model for evidence search."""
    query: str
    total_results: int
    top_k_results: int
    results: List[EvidenceResult]
    sources_searched: Dict[str, Dict[str, Any]]
    search_time_ms: int


class SerpSearchRequest(BaseModel):
    """Request model for SERP search."""
    query: str
    num_results: int = Field(10, ge=1, le=50)
    site_filters: Optional[List[str]] = None
    date_range: Optional[Dict[str, str]] = None


class SerpResult(BaseModel):
    """Single SERP result."""
    position: int
    title: str
    url: str
    snippet: str
    domain: str
    domain_authority: Optional[int] = None
    published_date: Optional[str] = None


class SerpSearchResponse(BaseModel):
    """Response model for SERP search."""
    search_query: str
    results: List[SerpResult]


class CrawlRequest(BaseModel):
    """Request model for URL crawling."""
    urls: List[str] = Field(..., max_length=10)
    extract: Optional[Dict[str, bool]] = Field(
        default={"main_content": True, "metadata": True, "structured_data": True}
    )
    clean: Optional[Dict[str, bool]] = Field(
        default={"remove_ads": True, "remove_navigation": True}
    )


class CrawledPage(BaseModel):
    """Single crawled page result."""
    url: str
    status: str
    title: Optional[str] = None
    main_content: Optional[str] = None
    word_count: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    structured_data: Optional[Dict[str, Any]] = None
    crawl_time_ms: int


class CrawlResponse(BaseModel):
    """Response model for URL crawling."""
    crawled: List[CrawledPage]
    failed: List[Dict[str, str]]


class VectorMatch(BaseModel):
    """Single vector search match."""
    id: str
    score: float
    metadata: Dict[str, Any]


class VectorSearchResponse(BaseModel):
    """Response model for vector search."""
    query: str
    matches: List[VectorMatch]


class GraphNode(BaseModel):
    """Graph node in query response."""
    id: str
    type: str
    properties: Dict[str, Any]


class GraphRelationship(BaseModel):
    """Graph relationship in query response."""
    from_node: str
    to_node: str
    type: str
    verified: Optional[bool] = None


class GraphQueryResponse(BaseModel):
    """Response model for graph query."""
    nodes: List[GraphNode]
    relationships: List[GraphRelationship]
    related_facts: List[Dict[str, Any]]
    graph_inference: str
