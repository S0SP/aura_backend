"""
AURA API v1 - Debate Engine Endpoints
Handles multi-agent debate sessions with real orchestration
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from datetime import datetime

from app.core.logging import logger
from app.core.config import settings
from app.utils.id_generator import generate_debate_session_id
from app.services.debate_service import debate_service
from app.models.debate import DebateConfig
from app.schemas.debate_schemas import (
    DebateInitRequest, DebateInitResponse,
    DebateSessionStatus, DebateRoundDetails,
    JudgeEvaluationRequest, JudgeEvaluationResponse,
    DebateTranscript
)

router = APIRouter()


# ===========================================
# POST /api/v1/debate/initiate
# ===========================================
@router.post("/initiate", response_model=DebateInitResponse, status_code=201)
async def initiate_debate(
    request: DebateInitRequest,
    background_tasks: BackgroundTasks
):
    """
    Start a new debate session with multi-agent setup.
    
    Initializes:
    - FOR Agent (Advocate) - Argues in favor of claim
    - AGAINST Agent (Skeptic) - Argues against claim
    - NEUTRAL Agent (Analyst) - Provides balanced analysis
    - JUDGE Agent - Evaluates arguments and evidence
    
    Debate runs for max 4 rounds with 4 exchanges each.
    """
    try:
        # Parse config
        config = DebateConfig(
            max_rounds=request.debate_config.get("max_rounds", settings.MAX_DEBATE_ROUNDS),
            exchanges_per_round=request.debate_config.get("exchanges_per_round", settings.EXCHANGES_PER_ROUND)
        ) if request.debate_config else DebateConfig()
        
        # Create debate session in database
        debate = await debate_service.create_session(
            verification_id=request.verification_id,
            claim=request.claim,
            initial_evidence=request.initial_evidence or [],
            quick_classification=request.quick_classification,
            config=config
        )
        
        logger.info(f"Initiated debate session: {debate.session_id} for {request.verification_id}")
        
        # Start debate in background if auto_start
        if request.auto_start:
            background_tasks.add_task(
                debate_service.run_debate,
                debate.session_id,
                request.verification_id
            )
        
        return DebateInitResponse(
            session_id=debate.session_id,
            verification_id=request.verification_id,
            status="initiated" if not request.auto_start else "starting",
            agents_initialized={
                "for_agent": "ready",
                "against_agent": "ready",
                "neutral_agent": "ready",
                "judge_agent": "ready"
            },
            debate_config={
                "max_rounds": config.max_rounds,
                "exchanges_per_round": config.exchanges_per_round,
                "estimated_completion_time_seconds": config.max_rounds * 30
            },
            websocket_url=f"wss://api.aura.in/ws/debate/{debate.session_id}",
            created_at=debate.created_at.isoformat()
        )
        
    except Exception as e:
        logger.error(f"Failed to initiate debate: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# POST /api/v1/debate/run/{session_id}
# ===========================================
@router.post("/run/{session_id}")
async def run_debate(
    session_id: str,
    background_tasks: BackgroundTasks
):
    """
    Start running the debate for an initiated session.
    Returns immediately, debate runs in background.
    """
    debate = await debate_service.get_session(session_id)
    if not debate:
        raise HTTPException(status_code=404, detail="Debate session not found")
    
    if debate.status.value not in ["initiated", "round_complete"]:
        raise HTTPException(status_code=400, detail=f"Cannot start debate in status: {debate.status}")
    
    # Run debate in background
    background_tasks.add_task(
        debate_service.run_debate,
        session_id,
        debate.verification_id
    )
    
    return {
        "session_id": session_id,
        "status": "starting",
        "message": "Debate started in background. Subscribe to WebSocket for updates."
    }


# ===========================================
# GET /api/v1/debate/session/{session_id}
# ===========================================
@router.get("/session/{session_id}", response_model=DebateSessionStatus)
async def get_debate_session(session_id: str):
    """
    Get current debate session status.
    
    Returns progress, scores, and current speaking agent.
    """
    debate = await debate_service.get_session(session_id)
    if not debate:
        raise HTTPException(status_code=404, detail="Debate session not found")
    
    # Calculate progress
    total_expected = debate.config.max_rounds * debate.config.exchanges_per_round
    completed = sum(len(r.get("exchanges", [])) if isinstance(r, dict) else len(r.exchanges) for r in debate.rounds)
    progress = int((completed / total_expected) * 100) if total_expected > 0 else 0
    
    # Get round scores
    round_scores = []
    for r in debate.rounds:
        if isinstance(r, dict):
            scores = r.get("round_scores", {})
        else:
            scores = r.round_scores if hasattr(r, 'round_scores') else {}
        round_scores.append(scores)
    
    return DebateSessionStatus(
        session_id=session_id,
        status=debate.status.value if hasattr(debate.status, 'value') else debate.status,
        current_round=len(debate.rounds),
        current_exchange=0,
        rounds_completed=len(debate.rounds),
        exchanges_completed=completed,
        total_exchanges_expected=total_expected,
        progress_percent=progress,
        round_scores=round_scores,
        current_speaking="judge_agent" if debate.status.value == "judging" else "for_agent",
        last_exchange_summary="",
        estimated_completion=datetime.utcnow().isoformat()
    )


# ===========================================
# POST /api/v1/debate/round/{session_id}
# ===========================================
@router.post("/round/{session_id}")
async def trigger_debate_round(
    session_id: str,
    round_number: int,
    focus_areas: Optional[List[str]] = None
):
    """
    Trigger the next debate round.
    
    Optional focus_areas from judge's feedback guide the discussion.
    """
    debate = await debate_service.get_session(session_id)
    if not debate:
        raise HTTPException(status_code=404, detail="Debate session not found")
    
    logger.info(f"Starting round {round_number} for session {session_id}")
    
    return {
        "session_id": session_id,
        "round_number": round_number,
        "status": "started",
        "message": "Round will be executed as part of full debate run",
        "focus_areas": focus_areas or []
    }


# ===========================================
# GET /api/v1/debate/round/{session_id}/{round_num}
# ===========================================
@router.get("/round/{session_id}/{round_num}", response_model=DebateRoundDetails)
async def get_round_details(session_id: str, round_num: int):
    """
    Get details of a specific debate round.
    
    Includes all exchanges, evidence cited, and judge evaluation.
    """
    debate = await debate_service.get_session(session_id)
    if not debate:
        raise HTTPException(status_code=404, detail="Debate session not found")
    
    if round_num > len(debate.rounds):
        raise HTTPException(status_code=404, detail=f"Round {round_num} not found")
    
    round_data = debate.rounds[round_num - 1]
    if isinstance(round_data, dict):
        exchanges = round_data.get("exchanges", [])
        round_scores = round_data.get("round_scores", {})
    else:
        exchanges = round_data.exchanges
        round_scores = round_data.round_scores
    
    return DebateRoundDetails(
        session_id=session_id,
        round_number=round_num,
        status="completed",
        exchanges=exchanges,
        round_summary={
            "total_exchanges": len(exchanges),
            "total_evidence_cited": 0,
            "unique_sources": 0,
            "key_points_debated": []
        },
        judge_evaluation=round_scores
    )


# ===========================================
# POST /api/v1/debate/judge/evaluate
# ===========================================
@router.post("/judge/evaluate", response_model=JudgeEvaluationResponse)
async def trigger_judge_evaluation(request: JudgeEvaluationRequest):
    """
    Trigger judge evaluation after a round or final evaluation.
    
    Judge scores:
    - Argument strength (1-10)
    - Evidence quality (1-10)
    - Logical consistency (1-10)
    - Source reliability (1-10)
    """
    debate = await debate_service.get_session(request.session_id)
    if not debate:
        raise HTTPException(status_code=404, detail="Debate session not found")
    
    logger.info(f"Judge evaluation for {request.session_id} - {request.evaluation_type}")
    
    # Get scores from completed rounds
    for_total = debate.final_scores.get("for", 0) if debate.final_scores else 0
    against_total = debate.final_scores.get("against", 0) if debate.final_scores else 0
    
    return JudgeEvaluationResponse(
        session_id=request.session_id,
        evaluation_type=request.evaluation_type,
        round_number=request.round_number,
        scores=debate.rounds[-1].get("round_scores", {}) if debate.rounds else {},
        round_verdict={
            "winner": debate.winner or "",
            "margin": "narrow",
            "key_factors": []
        },
        cumulative_status={
            "rounds_completed": len(debate.rounds),
            "for_total_score": for_total,
            "against_total_score": against_total,
            "leaning": "for" if for_total > against_total else "against",
            "confidence_so_far": 0.5
        },
        continue_debate=len(debate.rounds) < debate.config.max_rounds,
        next_round_focus=[]
    )


# ===========================================
# GET /api/v1/debate/transcript/{session_id}
# ===========================================
@router.get("/transcript/{session_id}", response_model=DebateTranscript)
async def get_debate_transcript(session_id: str):
    """
    Get the full debate transcript with all rounds and final verdict.
    """
    debate = await debate_service.get_session(session_id)
    if not debate:
        raise HTTPException(status_code=404, detail="Debate session not found")
    
    # Calculate stats
    total_exchanges = sum(
        len(r.get("exchanges", [])) if isinstance(r, dict) else len(r.exchanges)
        for r in debate.rounds
    )
    
    duration = 0
    if debate.completed_at and debate.started_at:
        duration = int((debate.completed_at - debate.started_at).total_seconds())
    
    return DebateTranscript(
        session_id=session_id,
        verification_id=debate.verification_id,
        claim=debate.claim,
        status=debate.status.value if hasattr(debate.status, 'value') else debate.status,
        debate_summary={
            "total_rounds": len(debate.rounds),
            "total_exchanges": total_exchanges,
            "total_evidence_cited": debate.total_evidence_cited,
            "unique_sources": debate.unique_sources,
            "debate_duration_seconds": duration
        },
        rounds=[
            {
                "round_number": i + 1,
                "exchanges": r.get("exchanges", []) if isinstance(r, dict) else r.exchanges,
                "scores": r.get("round_scores", {}) if isinstance(r, dict) else r.round_scores
            }
            for i, r in enumerate(debate.rounds)
        ],
        final_verdict=debate.final_verdict or {
            "verdict": "UNVERIFIED",
            "confidence": 0,
            "reasoning": "",
            "key_evidence": [],
            "dissenting_points": [],
            "agent_scores_final": debate.final_scores or {}
        },
        created_at=debate.created_at.isoformat(),
        completed_at=debate.completed_at.isoformat() if debate.completed_at else ""
    )


# ===========================================
# GET /api/v1/debate/agents
# ===========================================
@router.get("/agents")
async def get_available_agents():
    """
    Get available agent configurations.
    """
    return {
        "agents": [
            {
                "id": "for_agent",
                "name": "Truth Advocate",
                "role": "Arguments in favor of the claim being TRUE",
                "model": settings.GEMINI_MODEL,
                "temperature": 0.7
            },
            {
                "id": "against_agent",
                "name": "Skeptic Challenger",
                "role": "Arguments against the claim, finds contradictions",
                "model": settings.GEMINI_MODEL,
                "temperature": 0.7
            },
            {
                "id": "neutral_agent",
                "name": "Evidence Analyst",
                "role": "Balanced analysis, identifies gaps, synthesizes evidence",
                "model": settings.GEMINI_MODEL,
                "temperature": 0.5
            },
            {
                "id": "judge_agent",
                "name": "Final Arbiter",
                "role": "Evaluates arguments, scores rounds, renders verdict",
                "model": settings.GEMINI_MODEL,
                "temperature": 0.3
            }
        ],
        "debate_settings": {
            "max_rounds": settings.MAX_DEBATE_ROUNDS,
            "exchanges_per_round": settings.EXCHANGES_PER_ROUND,
            "timeout_seconds": settings.DEBATE_TIMEOUT_SECONDS
        }
    }
