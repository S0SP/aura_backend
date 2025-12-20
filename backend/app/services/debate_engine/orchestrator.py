"""
AURA Debate Orchestrator
Main debate flow orchestration using CrewAI agents
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio

from app.core.logging import logger
from app.core.config import settings
from app.agents.crew import create_fact_check_crew, FactCheckCrew
from app.services.classification.classifier import classifier
from app.services.classification.claim_categorizer import claim_categorizer
from app.services.knowledge_core.aggregator import evidence_aggregator
from app.services.notification.websocket import (
    notify_status_update,
    notify_debate_exchange,
    notify_verdict
)


class DebateOrchestrator:
    """
    Orchestrates the full fact-checking debate process.
    Coordinates classification, evidence retrieval, debate, and verdict.
    """
    
    def __init__(self):
        self.max_rounds = getattr(settings, 'MAX_DEBATE_ROUNDS', 4)
        self.exchanges_per_round = getattr(settings, 'EXCHANGES_PER_ROUND', 4)
        self.active_debates: Dict[str, FactCheckCrew] = {}
    
    async def run_full_verification(
        self,
        verification_id: str,
        claim: str,
        source_context: str = None,
        quick_only: bool = False
    ) -> Dict[str, Any]:
        """
        Run the complete fact-checking pipeline.
        
        1. Quick classification with XLM-RoBERTa
        2. Claim categorization for prompt switching
        3. Evidence retrieval
        4. Multi-agent debate
        5. Final verdict
        """
        start_time = datetime.utcnow()
        
        try:
            # Step 1: Quick Classification
            await notify_status_update(
                verification_id, "classifying", 10, "Running XLM-RoBERTa classification"
            )
            
            quick_result = await classifier.classify(claim)
            logger.info(f"Quick classification: {quick_result.get('verdict')} ({quick_result.get('confidence'):.0%})")
            
            if quick_only:
                return {
                    "verification_id": verification_id,
                    "claim": claim,
                    "quick_classification": quick_result,
                    "completed_at": datetime.utcnow().isoformat()
                }
            
            # Step 2: Categorize claim for prompt switching
            await notify_status_update(
                verification_id, "categorizing", 15, "Categorizing claim"
            )
            
            category_result = claim_categorizer.categorize(claim)
            claim_category = category_result.get("category", "general")
            logger.info(f"Claim category: {claim_category}")
            
            # Step 3: Retrieve evidence
            await notify_status_update(
                verification_id, "retrieving_evidence", 25, "Searching evidence sources"
            )
            
            evidence_result = await evidence_aggregator.search_all(
                query=claim,
                sources=["serp", "pinecone", "neo4j"],
                limit_per_source=5
            )
            initial_evidence = evidence_result.get("results", [])[:10]
            logger.info(f"Retrieved {len(initial_evidence)} evidence items")
            
            # Step 4: Initialize debate crew with category-specific prompts
            await notify_status_update(
                verification_id, "initiating_debate", 30, "Initializing debate agents"
            )
            
            crew = create_fact_check_crew(claim_category)
            self.active_debates[verification_id] = crew
            
            # Step 5: Run debate
            debate_result = await self._run_debate_with_updates(
                verification_id=verification_id,
                crew=crew,
                claim=claim,
                initial_evidence=initial_evidence,
                quick_classification=quick_result
            )
            
            # Step 6: Compile final result
            await notify_status_update(
                verification_id, "completed", 100, "Verification complete"
            )
            
            final_verdict = debate_result.get("final_verdict", {})
            
            await notify_verdict(
                verification_id=verification_id,
                verdict=final_verdict.get("verdict", "UNVERIFIABLE"),
                confidence=final_verdict.get("confidence", 0.5),
                summary=final_verdict.get("reasoning_summary", "")
            )
            
            total_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Cleanup
            if verification_id in self.active_debates:
                del self.active_debates[verification_id]
            
            return {
                "verification_id": verification_id,
                "claim": claim,
                "category": claim_category,
                "quick_classification": quick_result,
                "evidence_count": len(initial_evidence),
                "debate_summary": debate_result.get("debate_summary", {}),
                "verdict": final_verdict,
                "processing_time_seconds": round(total_time, 2),
                "completed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            await notify_status_update(
                verification_id, "failed", 0, f"Error: {str(e)}"
            )
            
            return {
                "verification_id": verification_id,
                "claim": claim,
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _run_debate_with_updates(
        self,
        verification_id: str,
        crew: FactCheckCrew,
        claim: str,
        initial_evidence: List[Dict],
        quick_classification: Dict
    ) -> Dict[str, Any]:
        """Run debate with real-time WebSocket updates."""
        all_exchanges = []
        round_evaluations = []
        
        for round_num in range(1, self.max_rounds + 1):
            progress = 30 + (round_num * 15)  # 45%, 60%, 75%, 90%
            
            await notify_status_update(
                verification_id, "debating", progress,
                f"Round {round_num}: Agents debating"
            )
            
            # Run round
            round_exchanges = await crew._run_round(
                claim=claim,
                round_number=round_num,
                all_exchanges=all_exchanges,
                evidence=initial_evidence,
                focus_areas=round_evaluations[-1].get("areas_for_next_round") if round_evaluations else None
            )
            
            # Send exchange updates
            for i, ex in enumerate(round_exchanges, 1):
                await notify_debate_exchange(
                    session_id=verification_id,
                    agent=ex.get("agent", "unknown"),
                    exchange=i,
                    round_num=round_num,
                    argument=ex.get("argument", ex.get("analysis", ""))
                )
            
            all_exchanges.extend(round_exchanges)
            
            # Judge evaluates
            await notify_status_update(
                verification_id, "judging_round", progress + 5,
                f"Judge evaluating round {round_num}"
            )
            
            round_eval = await crew.judge_agent.evaluate_round(
                claim=claim,
                round_number=round_num,
                exchanges=round_exchanges,
                evidence_cited=initial_evidence
            )
            round_evaluations.append(round_eval)
        
        # Final verdict
        await notify_status_update(
            verification_id, "rendering_verdict", 95,
            "Judge rendering final verdict"
        )
        
        final_verdict = await crew.judge_agent.render_final_verdict(
            claim=claim,
            all_rounds=round_evaluations,
            quick_classification=quick_classification
        )
        
        return {
            "debate_summary": {
                "total_rounds": len(round_evaluations),
                "total_exchanges": len(all_exchanges)
            },
            "rounds": round_evaluations,
            "all_exchanges": all_exchanges,
            "final_verdict": final_verdict
        }
    
    def get_debate_status(self, verification_id: str) -> Optional[Dict]:
        """Get status of an active debate."""
        crew = self.active_debates.get(verification_id)
        if crew:
            return crew.get_agent_status()
        return None


# Global instance
debate_orchestrator = DebateOrchestrator()
