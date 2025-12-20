"""
AURA Pydantic Schemas - Debate Engine
Request and response models for debate endpoints
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    """Agent configuration."""
    model: str = "gemini-1.5-flash"
    temperature: float = 0.7
    role: str


class DebateConfig(BaseModel):
    """Debate configuration."""
    max_rounds: int = Field(4, ge=1, le=10)
    exchanges_per_round: int = Field(4, ge=2, le=8)
    time_limit_per_exchange_seconds: int = 30
    require_evidence_citation: bool = True


class DebateInitRequest(BaseModel):
    """Request model for initiating a debate."""
    verification_id: str
    claim: str
    initial_evidence: Optional[List[Dict[str, Any]]] = None
    quick_classification: Optional[Dict[str, Any]] = None
    debate_config: Optional[Dict[str, Any]] = Field(default_factory=dict)


class DebateInitResponse(BaseModel):
    """Response model for debate initiation."""
    session_id: str
    verification_id: str
    status: str
    agents_initialized: Dict[str, str]
    debate_config: Dict[str, Any]
    websocket_url: str
    created_at: str


class RoundScore(BaseModel):
    """Score for a debate round."""
    round: int
    for_score: float
    against_score: float
    neutral_assessment: str
    judge_notes: str


class DebateSessionStatus(BaseModel):
    """Debate session status response."""
    session_id: str
    status: str  # initiated, in_progress, judging, completed
    current_round: int
    current_exchange: int
    rounds_completed: int
    exchanges_completed: int
    total_exchanges_expected: int
    progress_percent: float
    round_scores: List[RoundScore]
    current_speaking: str
    last_exchange_summary: str
    estimated_completion: str


class ExchangeDetail(BaseModel):
    """Details of a single debate exchange."""
    exchange_number: int
    agent: str
    agent_name: str
    timestamp: Optional[str] = None
    argument: Optional[Dict[str, Any]] = None
    evidence_queries_made: Optional[List[Dict[str, Any]]] = None
    token_count: Optional[int] = None


class RoundSummary(BaseModel):
    """Summary of a debate round."""
    total_exchanges: int
    total_evidence_cited: int
    unique_sources: int
    key_points_debated: List[str]


class JudgeRoundEvaluation(BaseModel):
    """Judge's evaluation of a round."""
    for_score: float
    against_score: float
    neutral_score: Optional[float] = None
    round_winner: str
    reasoning: str
    key_evidence_this_round: List[str]
    areas_for_next_round: List[str]


class DebateRoundDetails(BaseModel):
    """Details of a specific debate round."""
    session_id: str
    round_number: int
    status: str
    exchanges: List[ExchangeDetail]
    round_summary: RoundSummary
    judge_evaluation: Optional[JudgeRoundEvaluation]


class JudgeEvaluationRequest(BaseModel):
    """Request model for judge evaluation."""
    session_id: str
    evaluation_type: str = Field(..., description="'round' or 'final'")
    round_number: Optional[int] = None
    evaluation_criteria: Optional[Dict[str, float]] = None


class AgentScore(BaseModel):
    """Agent scores from evaluation."""
    argument_strength: float
    evidence_quality: float
    logical_consistency: float
    source_reliability: float
    weighted_total: float


class NeutralScore(BaseModel):
    """Neutral agent score."""
    analysis_quality: float
    gap_identification: float
    objectivity: float
    weighted_total: float


class RoundVerdict(BaseModel):
    """Verdict for a round."""
    winner: str
    margin: str
    key_factors: List[str]


class CumulativeStatus(BaseModel):
    """Cumulative debate status."""
    rounds_completed: int
    for_total_score: float
    against_total_score: float
    leaning: str
    confidence_so_far: float


class JudgeEvaluationResponse(BaseModel):
    """Response model for judge evaluation."""
    session_id: str
    evaluation_type: str
    round_number: Optional[int]
    scores: Dict[str, Any]
    round_verdict: RoundVerdict
    cumulative_status: CumulativeStatus
    continue_debate: bool
    next_round_focus: List[str]


class FinalVerdict(BaseModel):
    """Final verdict from debate."""
    verdict: str  # TRUE, FALSE, MISLEADING, UNVERIFIABLE
    confidence: float
    reasoning: str
    key_evidence: List[Dict[str, Any]]
    dissenting_points: List[str]
    agent_scores_final: Dict[str, float]


class DebateSummary(BaseModel):
    """Summary of complete debate."""
    total_rounds: int
    total_exchanges: int
    total_evidence_cited: int
    unique_sources: int
    debate_duration_seconds: int


class DebateTranscript(BaseModel):
    """Full debate transcript."""
    session_id: str
    verification_id: str
    claim: str
    status: str
    debate_summary: DebateSummary
    rounds: List[Dict[str, Any]]
    final_verdict: FinalVerdict
    created_at: str
    completed_at: str
