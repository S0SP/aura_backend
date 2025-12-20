"""
AURA CrewAI Crew Definition
Defines the fact-checking debate crew with all agents
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from crewai import Crew, Task, Process

from app.core.logging import logger
from app.core.config import settings
from app.agents.for_agent import create_for_agent, ForAgent
from app.agents.against_agent import create_against_agent, AgainstAgent
from app.agents.neutral_agent import create_neutral_agent, NeutralAgent
from app.agents.judge_agent import create_judge_agent, JudgeAgent


class FactCheckCrew:
    """
    AURA Fact-Checking Crew
    Orchestrates the debate between FOR, AGAINST, NEUTRAL agents
    evaluated by the JUDGE agent.
    """
    
    def __init__(self, claim_category: str = "general"):
        self.category = claim_category
        self.for_agent: ForAgent = None
        self.against_agent: AgainstAgent = None
        self.neutral_agent: NeutralAgent = None
        self.judge_agent: JudgeAgent = None
        self._initialized = False
    
    def initialize_agents(self):
        """Initialize all agents for the crew."""
        logger.info(f"Initializing fact-check crew for category: {self.category}")
        
        self.for_agent = create_for_agent(self.category)
        self.against_agent = create_against_agent(self.category)
        self.neutral_agent = create_neutral_agent(self.category)
        self.judge_agent = create_judge_agent(self.category)
        
        self._initialized = True
        logger.info("All agents initialized successfully")
    
    async def run_debate(
        self,
        claim: str,
        initial_evidence: List[Dict] = None,
        quick_classification: Dict = None,
        max_rounds: int = 4,
        exchanges_per_round: int = 4
    ) -> Dict[str, Any]:
        """
        Run a full debate on a claim.
        
        Args:
            claim: The claim to debate
            initial_evidence: Pre-fetched evidence
            quick_classification: XLM-RoBERTa classification result
            max_rounds: Number of debate rounds (default 4)
            exchanges_per_round: Exchanges per round (default 4)
        
        Returns:
            Complete debate results with final verdict
        """
        if not self._initialized:
            self.initialize_agents()
        
        start_time = datetime.utcnow()
        all_exchanges = []
        round_evaluations = []
        
        logger.info(f"Starting debate on claim: {claim[:100]}...")
        
        for round_num in range(1, max_rounds + 1):
            logger.info(f"=== ROUND {round_num} ===")
            
            round_exchanges = await self._run_round(
                claim=claim,
                round_number=round_num,
                all_exchanges=all_exchanges,
                evidence=initial_evidence,
                focus_areas=round_evaluations[-1].get("areas_for_next_round") if round_evaluations else None
            )
            
            all_exchanges.extend(round_exchanges)
            
            # Judge evaluates the round
            round_eval = await self.judge_agent.evaluate_round(
                claim=claim,
                round_number=round_num,
                exchanges=round_exchanges,
                evidence_cited=initial_evidence
            )
            round_evaluations.append(round_eval)
            
            logger.info(f"Round {round_num} winner: {round_eval.get('round_winner', 'tie')}")
        
        # Final verdict
        logger.info("=== FINAL VERDICT ===")
        final_verdict = await self.judge_agent.render_final_verdict(
            claim=claim,
            all_rounds=round_evaluations,
            quick_classification=quick_classification
        )
        
        total_time = (datetime.utcnow() - start_time).total_seconds()
        
        return {
            "claim": claim,
            "category": self.category,
            "quick_classification": quick_classification,
            "debate_summary": {
                "total_rounds": len(round_evaluations),
                "total_exchanges": len(all_exchanges),
                "debate_duration_seconds": round(total_time, 2)
            },
            "rounds": round_evaluations,
            "all_exchanges": all_exchanges,
            "final_verdict": final_verdict,
            "completed_at": datetime.utcnow().isoformat()
        }
    
    async def _run_round(
        self,
        claim: str,
        round_number: int,
        all_exchanges: List[Dict],
        evidence: List[Dict] = None,
        focus_areas: List[str] = None
    ) -> List[Dict]:
        """Run a single debate round."""
        round_exchanges = []
        
        # Exchange 1: FOR Agent opens
        for_arg = await self.for_agent.generate_argument(
            claim=claim,
            round_number=round_number,
            previous_exchanges=all_exchanges,
            evidence=evidence,
            focus_areas=focus_areas
        )
        round_exchanges.append(for_arg)
        
        # Exchange 2: AGAINST Agent responds
        against_arg = await self.against_agent.generate_argument(
            claim=claim,
            round_number=round_number,
            previous_exchanges=all_exchanges + round_exchanges,
            evidence=evidence,
            for_agent_argument=for_arg.get("argument", ""),
            focus_areas=focus_areas
        )
        round_exchanges.append(against_arg)
        
        # Exchange 3: NEUTRAL Agent analyzes
        neutral_analysis = await self.neutral_agent.generate_analysis(
            claim=claim,
            round_number=round_number,
            for_argument=for_arg.get("argument", ""),
            against_argument=against_arg.get("argument", ""),
            previous_exchanges=all_exchanges + round_exchanges,
            evidence=evidence
        )
        round_exchanges.append(neutral_analysis)
        
        # Exchange 4: FOR Agent rebuts
        for_rebuttal = await self.for_agent.generate_argument(
            claim=claim,
            round_number=round_number,
            previous_exchanges=all_exchanges + round_exchanges,
            evidence=evidence,
            focus_areas=[
                neutral_analysis.get("synthesis", ""),
                against_arg.get("argument", "")[:200]
            ]
        )
        round_exchanges.append(for_rebuttal)
        
        return round_exchanges
    
    def get_agent_status(self) -> Dict[str, str]:
        """Get status of all agents."""
        return {
            "for_agent": "ready" if self.for_agent else "not_initialized",
            "against_agent": "ready" if self.against_agent else "not_initialized",
            "neutral_agent": "ready" if self.neutral_agent else "not_initialized",
            "judge_agent": "ready" if self.judge_agent else "not_initialized"
        }


def create_fact_check_crew(claim_category: str = "general") -> FactCheckCrew:
    """Factory function to create a fact-checking crew."""
    crew = FactCheckCrew(claim_category=claim_category)
    crew.initialize_agents()
    return crew
