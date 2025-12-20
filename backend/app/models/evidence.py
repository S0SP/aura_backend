"""
AURA Pydantic Models - Evidence
MongoDB document model for evidence items
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class EvidenceSource(str, Enum):
    """Source of evidence."""
    SERP = "serp"
    PINECONE = "pinecone"
    NEO4J = "neo4j"
    FIRECRAWL = "firecrawl"
    MANUAL = "manual"


class EvidenceType(str, Enum):
    """Type of evidence."""
    FACT_CHECK = "fact_check"
    NEWS_ARTICLE = "news_article"
    SCIENTIFIC_PAPER = "scientific_paper"
    OFFICIAL_SOURCE = "official_source"
    SOCIAL_MEDIA = "social_media"
    KNOWLEDGE_GRAPH = "knowledge_graph"


class EvidenceInDB(BaseModel):
    """Evidence item as stored in MongoDB."""
    id: Optional[str] = Field(None, alias="_id")
    evidence_id: str
    
    # Source information
    source: EvidenceSource
    source_type: EvidenceType = EvidenceType.NEWS_ARTICLE
    
    # Content
    title: Optional[str] = None
    url: Optional[str] = None
    content: str = ""
    content_snippet: str = ""
    
    # Metadata
    domain: Optional[str] = None
    domain_authority: Optional[int] = None
    author: Optional[str] = None
    published_date: Optional[datetime] = None
    
    # Scoring
    relevance_score: float = 0.0
    credibility_score: float = 0.0
    combined_score: float = 0.0
    
    # Verdict information
    verdict_in_source: Optional[str] = None
    claim_supported: Optional[bool] = None
    
    # Vector embedding info
    embedding_id: Optional[str] = None
    chunk_index: Optional[int] = None
    
    # Relationships
    verification_id: Optional[str] = None
    related_claims: List[str] = []
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        use_enum_values = True


class EvidenceCreate(BaseModel):
    """Model for creating evidence."""
    source: EvidenceSource
    source_type: EvidenceType = EvidenceType.NEWS_ARTICLE
    title: Optional[str] = None
    url: Optional[str] = None
    content: str
    domain: Optional[str] = None
    verification_id: Optional[str] = None


class EvidenceSearchResult(BaseModel):
    """Evidence search result."""
    evidence_id: str
    rank: int
    source: str
    title: Optional[str] = None
    url: Optional[str] = None
    content_snippet: str
    relevance_score: float
    combined_score: float
    verdict_in_source: Optional[str] = None


# ===========================================
# Fact Model (for Knowledge Base)
# ===========================================

class FactCategory(str, Enum):
    """Categories for facts."""
    HEALTH = "health"
    POLITICAL = "political"
    FINANCIAL = "financial"
    SCIENCE = "science"
    SOCIAL = "social"
    DISASTER = "disaster"
    TECHNOLOGY = "technology"
    OTHER = "other"


class FactInDB(BaseModel):
    """Verified fact stored in knowledge base."""
    id: Optional[str] = Field(None, alias="_id")
    fact_id: str
    
    # Original claim
    claim: str
    claim_normalized: str = ""
    language: str = "en"
    
    # Verdict
    verdict: str  # TRUE, FALSE, MISLEADING, etc.
    confidence: float = 0.0
    
    # Evidence summary
    evidence_summary: str = ""
    primary_sources: List[str] = []
    
    # Categorization
    category: FactCategory = FactCategory.OTHER
    tags: List[str] = []
    entities: List[str] = []
    
    # Vector embedding
    embedding_id: Optional[str] = None
    
    # Neo4j relationships
    neo4j_node_id: Optional[str] = None
    related_facts: List[str] = []
    
    # Metadata
    source: str = ""  # Who verified this
    source_url: Optional[str] = None
    verified_by: str = "aura"
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    verified_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    # Usage stats
    times_matched: int = 0
    last_matched_at: Optional[datetime] = None
    
    class Config:
        populate_by_name = True
        use_enum_values = True


class FactCreate(BaseModel):
    """Model for creating a fact."""
    claim: str
    verdict: str
    evidence_summary: str
    source: str
    source_url: Optional[str] = None
    category: FactCategory = FactCategory.OTHER
