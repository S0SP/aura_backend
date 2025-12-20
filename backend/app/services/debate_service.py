"""
AURA Debate Engine - Main Debate Service
Orchestrates the multi-agent debate process
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio

from app.core.logging import logger
from app.core.config import settings
from app.db.mongodb import get_collection, Collections
from app.models.debate import DebateInDB, DebateCreate, DebateStatus, DebateRound, Exchange, DebateConfig
from app.models.verification import VerdictType
from app.services.llm_service import get_llm
from app.services.websocket_service import notify_status_update, notify_debate_exchange, notify_verdict
from app.agents.prompts import (
    get_for_agent_prompt, get_against_agent_prompt,
    get_neutral_agent_prompt, get_round_scoring_prompt,
    get_final_verdict_prompt
)
from app.utils.id_generator import generate_debate_session_id


class DebateService:
    """
    Main service for orchestrating multi-agent debates.
    
    Flow:
    1. Initialize debate session with claim and evidence
    2. Run 4 rounds, each with FOR/AGAINST/NEUTRAL exchanges
    3. Judge scores each round
    4. Judge renders final verdict
    """
    
    def __init__(self):
        self.collection_name = Collections.DEBATE_SESSIONS
    
    @property
    def collection(self):
        return get_collection(self.collection_name)
    
    async def create_session(
        self,
        verification_id: str,
        claim: str,
        initial_evidence: List[Dict[str, Any]],
        quick_classification: Dict[str, Any] = None,
        config: DebateConfig = None
    ) -> DebateInDB:
        """
        Create a new debate session.
        
        Args:
            verification_id: Parent verification ID
            claim: The claim to debate
            initial_evidence: Evidence gathered before debate
            quick_classification: Quick ML classification result
            config: Debate configuration
            
        Returns:
            Created debate session
        """
        session_id = generate_debate_session_id()
        
        debate = DebateInDB(
            session_id=session_id,
            verification_id=verification_id,
            claim=claim,
            status=DebateStatus.INITIATED,
            config=config or DebateConfig(),
            initial_evidence=initial_evidence,
            quick_classification=quick_classification,
            created_at=datetime.utcnow()
        )
        
        doc_dict = debate.model_dump(by_alias=True, exclude={"id"})
        result = await self.collection.insert_one(doc_dict)
        debate.id = str(result.inserted_id)
        
        logger.info(f"Created debate session: {session_id}")
        return debate
    
    async def run_debate(
        self,
        session_id: str,
        verification_id: str = None
    ) -> Dict[str, Any]:
        """
        Run the full debate process.
        
        Args:
            session_id: Debate session ID
            verification_id: For WebSocket notifications
            
        Returns:
            Final verdict and debate summary
        """
        debate = await self.get_session(session_id)
        if not debate:
            raise ValueError(f"Debate session not found: {session_id}")
        
        verification_id = verification_id or debate.verification_id
        
        try:
            # Update status
            await self._update_status(session_id, DebateStatus.IN_PROGRESS)
            await notify_status_update(verification_id, "debating", 30, "Starting multi-agent debate")
            
            # Initialize rounds storage
            all_rounds = []
            round_scores = []
            
            # Run 4 rounds
            for round_num in range(1, debate.config.max_rounds + 1):
                logger.info(f"Starting round {round_num}")
                
                round_result = await self._run_round(
                    debate, round_num, all_rounds
                )
                
                all_rounds.append(round_result)
                
                # Judge scores the round
                score = await self._score_round(debate, round_num, round_result)
                round_scores.append(score)
                
                # Notify progress
                progress = 30 + (round_num * 12)
                await notify_status_update(
                    verification_id, "debating", progress,
                    f"Completed round {round_num} of {debate.config.max_rounds}"
                )
                
                # Save round to DB
                await self._save_round(session_id, round_result, score)
            
            # Calculate totals
            for_total = sum(
                r.get("scores", {}).get("for_agent", {}).get("weighted_total", 0)
                for r in round_scores
            )
            against_total = sum(
                r.get("scores", {}).get("against_agent", {}).get("weighted_total", 0)
                for r in round_scores
            )
            
            # Generate final verdict
            await notify_status_update(verification_id, "judging", 85, "Judge rendering final verdict")
            
            final_verdict = await self._generate_verdict(
                debate, round_scores, for_total, against_total
            )
            
            # Save final results
            await self._complete_session(
                session_id,
                final_verdict,
                {"for": for_total, "against": against_total}
            )
            
            # Notify completion
            await notify_verdict(
                verification_id,
                final_verdict.get("verdict", "UNVERIFIABLE"),
                final_verdict.get("confidence", 0.5),
                final_verdict.get("reasoning_summary", "")
            )
            
            return {
                "session_id": session_id,
                "verdict": final_verdict,
                "round_scores": round_scores,
                "totals": {"for": for_total, "against": against_total},
                "winner": final_verdict.get("winner", "tie")
            }
            
        except Exception as e:
            logger.error(f"Debate failed: {e}")
            await self._update_status(session_id, DebateStatus.FAILED)
            raise
    
    async def _run_round(
        self,
        debate: DebateInDB,
        round_number: int,
        previous_rounds: List[Dict]
    ) -> Dict[str, Any]:
        """Run a single debate round."""
        llm = get_llm()
        if not llm:
            raise RuntimeError("No LLM available for debate")
        
        exchanges = []
        
        # Collect previous exchanges for context
        previous_exchanges = []
        for r in previous_rounds:
            previous_exchanges.extend(r.get("exchanges", []))
        
        # FOR agent first
        for_prompt = get_for_agent_prompt(
            claim=debate.claim,
            round_number=round_number,
            exchange_number=1,
            previous_exchanges=previous_exchanges,
            evidence=debate.initial_evidence
        )
        
        for_response = await llm.ainvoke(for_prompt)
        for_argument = for_response.content if hasattr(for_response, 'content') else str(for_response)
        
        exchanges.append({
            "agent": "for_agent",
            "agent_name": "Truth Advocate",
            "argument": for_argument,
            "timestamp": datetime.utcnow().isoformat()
        })
        previous_exchanges.append(exchanges[-1])
        
        await notify_debate_exchange(
            debate.verification_id, debate.session_id,
            round_number, "Truth Advocate", for_argument[:200]
        )
        
        # AGAINST agent responds
        against_prompt = get_against_agent_prompt(
            claim=debate.claim,
            round_number=round_number,
            exchange_number=2,
            previous_exchanges=previous_exchanges,
            evidence=debate.initial_evidence
        )
        
        against_response = await llm.ainvoke(against_prompt)
        against_argument = against_response.content if hasattr(against_response, 'content') else str(against_response)
        
        exchanges.append({
            "agent": "against_agent",
            "agent_name": "Skeptic Challenger",
            "argument": against_argument,
            "timestamp": datetime.utcnow().isoformat()
        })
        previous_exchanges.append(exchanges[-1])
        
        await notify_debate_exchange(
            debate.verification_id, debate.session_id,
            round_number, "Skeptic Challenger", against_argument[:200]
        )
        
        # NEUTRAL agent synthesizes
        neutral_prompt = get_neutral_agent_prompt(
            claim=debate.claim,
            round_number=round_number,
            exchange_number=3,
            for_arguments=[e for e in exchanges if e["agent"] == "for_agent"],
            against_arguments=[e for e in exchanges if e["agent"] == "against_agent"]
        )
        
        neutral_response = await llm.ainvoke(neutral_prompt)
        neutral_argument = neutral_response.content if hasattr(neutral_response, 'content') else str(neutral_response)
        
        exchanges.append({
            "agent": "neutral_agent",
            "agent_name": "Evidence Analyst",
            "argument": neutral_argument,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return {
            "round_number": round_number,
            "exchanges": exchanges,
            "completed_at": datetime.utcnow().isoformat()
        }
    
    async def _score_round(
        self,
        debate: DebateInDB,
        round_number: int,
        round_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Have the judge score a round."""
        llm = get_llm()
        
        for_args = [e for e in round_result["exchanges"] if e["agent"] == "for_agent"]
        against_args = [e for e in round_result["exchanges"] if e["agent"] == "against_agent"]
        neutral_analysis = next(
            (e["argument"] for e in round_result["exchanges"] if e["agent"] == "neutral_agent"),
            ""
        )
        
        score_prompt = get_round_scoring_prompt(
            round_number=round_number,
            for_arguments=for_args,
            against_arguments=against_args,
            neutral_analysis=neutral_analysis
        )
        
        try:
            score_response = await llm.ainvoke(score_prompt)
            score_text = score_response.content if hasattr(score_response, 'content') else str(score_response)
            
            # Parse JSON from response
            import json
            try:
                score = json.loads(score_text)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\{[\s\S]*\}', score_text)
                if json_match:
                    score = json.loads(json_match.group())
                else:
                    score = self._default_score(round_number)
                    
        except Exception as e:
            logger.error(f"Scoring failed: {e}")
            score = self._default_score(round_number)
        
        return score
    
    def _default_score(self, round_number: int) -> Dict[str, Any]:
        """Return default score if parsing fails."""
        return {
            "round_number": round_number,
            "scores": {
                "for_agent": {"weighted_total": 5.0},
                "against_agent": {"weighted_total": 5.0},
                "neutral_agent": {"weighted_total": 7.0}
            },
            "round_winner": "tie",
            "margin": "marginal",
            "key_factors": ["Unable to determine"]
        }
    
    async def _generate_verdict(
        self,
        debate: DebateInDB,
        round_scores: List[Dict],
        for_total: float,
        against_total: float
    ) -> Dict[str, Any]:
        """Generate final verdict from judge."""
        llm = get_llm()
        
        verdict_prompt = get_final_verdict_prompt(
            claim=debate.claim,
            quick_classification=debate.quick_classification or {},
            round_scores=round_scores,
            for_total=for_total,
            against_total=against_total,
            key_evidence=debate.initial_evidence[:5]
        )
        
        try:
            verdict_response = await llm.ainvoke(verdict_prompt)
            verdict_text = verdict_response.content if hasattr(verdict_response, 'content') else str(verdict_response)
            
            import json
            try:
                verdict = json.loads(verdict_text)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\{[\s\S]*\}', verdict_text)
                if json_match:
                    verdict = json.loads(json_match.group())
                else:
                    verdict = self._default_verdict(for_total, against_total)
                    
        except Exception as e:
            logger.error(f"Verdict generation failed: {e}")
            verdict = self._default_verdict(for_total, against_total)
        
        return verdict
    
    def _default_verdict(
        self,
        for_total: float,
        against_total: float
    ) -> Dict[str, Any]:
        """Return default verdict if generation fails."""
        winner = "for_agent" if for_total > against_total else "against_agent"
        verdict = "TRUE" if winner == "for_agent" else "FALSE"
        
        return {
            "verdict": verdict,
            "confidence": 0.5,
            "confidence_level": "low",
            "reasoning_summary": "Verdict based on debate scores.",
            "reasoning_detailed": f"FOR agent scored {for_total:.1f}, AGAINST scored {against_total:.1f}.",
            "key_points": ["Based on debate scoring"],
            "dissenting_points": [],
            "winner": winner
        }
    
    async def get_session(self, session_id: str) -> Optional[DebateInDB]:
        """Get a debate session by ID."""
        doc = await self.collection.find_one({"session_id": session_id})
        if doc:
            doc["_id"] = str(doc["_id"])
            return DebateInDB(**doc)
        return None
    
    async def _update_status(
        self,
        session_id: str,
        status: DebateStatus
    ) -> bool:
        """Update debate session status."""
        update = {"status": status.value}
        if status == DebateStatus.IN_PROGRESS:
            update["started_at"] = datetime.utcnow()
        
        result = await self.collection.update_one(
            {"session_id": session_id},
            {"$set": update}
        )
        return result.modified_count > 0
    
    async def _save_round(
        self,
        session_id: str,
        round_result: Dict,
        score: Dict
    ) -> bool:
        """Save a round to the database."""
        round_data = {
            **round_result,
            "round_scores": score.get("scores", {}),
            "judge_feedback": score.get("feedback", ""),
            "next_round_focus": score.get("next_round_focus", [])
        }
        
        result = await self.collection.update_one(
            {"session_id": session_id},
            {
                "$push": {"rounds": round_data},
                "$inc": {"total_exchanges": len(round_result.get("exchanges", []))}
            }
        )
        return result.modified_count > 0
    
    async def _complete_session(
        self,
        session_id: str,
        final_verdict: Dict,
        final_scores: Dict
    ) -> bool:
        """Complete the debate session."""
        result = await self.collection.update_one(
            {"session_id": session_id},
            {"$set": {
                "status": DebateStatus.COMPLETED.value,
                "final_verdict": final_verdict,
                "final_scores": final_scores,
                "winner": final_verdict.get("winner"),
                "completed_at": datetime.utcnow()
            }}
        )
        return result.modified_count > 0


# Global service instance
debate_service = DebateService()
