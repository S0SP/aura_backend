"""
AURA Pydantic Models - Debate
MongoDB document model for debate sessions
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class DebateStatus(str, Enum):
    """Debate session status."""
    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    ROUND_COMPLETE = "round_complete"
    JUDGING = "judging"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentRole(str, Enum):
    """Agent roles in debate."""
    FOR_AGENT = "for_agent"
    AGAINST_AGENT = "against_agent"
    NEUTRAL_AGENT = "neutral_agent"
    JUDGE_AGENT = "judge_agent"


class Exchange(BaseModel):
    """Single exchange in a debate round."""
    exchange_number: int
    agent: AgentRole
    agent_name: str = ""
    argument: str = ""
    evidence_cited: List[str] = []
    evidence_queries: List[Dict[str, Any]] = []
    token_count: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class RoundScore(BaseModel):
    """Scores for a debate round."""
    for_agent: Dict[str, float] = {
        "argument_strength": 0.0,
        "evidence_quality": 0.0,
        "logical_consistency": 0.0,
        "source_reliability": 0.0,
        "weighted_total": 0.0
    }
    against_agent: Dict[str, float] = {
        "argument_strength": 0.0,
        "evidence_quality": 0.0,
        "logical_consistency": 0.0,
        "source_reliability": 0.0,
        "weighted_total": 0.0
    }
    neutral_agent: Dict[str, float] = {
        "analysis_quality": 0.0,
        "gap_identification": 0.0,
        "objectivity": 0.0,
        "weighted_total": 0.0
    }
    round_winner: str = ""
    margin: str = ""
    key_factors: List[str] = []


class DebateRound(BaseModel):
    """Single round of debate."""
    round_number: int
    status: str = "pending"
    exchanges: List[Exchange] = []
    round_scores: Optional[RoundScore] = None
    judge_feedback: str = ""
    next_round_focus: List[str] = []
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class DebateConfig(BaseModel):
    """Debate session configuration."""
    max_rounds: int = 4
    exchanges_per_round: int = 4
    time_limit_per_exchange_seconds: int = 30
    require_evidence_citation: bool = True
    llm_model: str = "gemini-1.5-flash"
    temperature: float = 0.7


class DebateInDB(BaseModel):
    """Debate session as stored in MongoDB."""
    id: Optional[str] = Field(None, alias="_id")
    session_id: str
    verification_id: str
    claim: str
    
    # Status
    status: DebateStatus = DebateStatus.INITIATED
    current_round: int = 0
    current_exchange: int = 0
    
    # Configuration
    config: DebateConfig = Field(default_factory=DebateConfig)
    
    # Rounds
    rounds: List[DebateRound] = []
    
    # Evidence provided to agents
    initial_evidence: List[Dict[str, Any]] = []
    quick_classification: Optional[Dict[str, Any]] = None
    
    # Final results
    final_verdict: Optional[Dict[str, Any]] = None
    final_scores: Dict[str, float] = {}
    winner: Optional[str] = None
    
    # Metrics
    total_exchanges: int = 0
    total_evidence_cited: int = 0
    unique_sources: int = 0
    debate_duration_seconds: int = 0
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        populate_by_name = True
        use_enum_values = True


class DebateCreate(BaseModel):
    """Model for creating a debate session."""
    verification_id: str
    claim: str
    initial_evidence: List[Dict[str, Any]] = []
    quick_classification: Optional[Dict[str, Any]] = None
    config: Optional[DebateConfig] = None
