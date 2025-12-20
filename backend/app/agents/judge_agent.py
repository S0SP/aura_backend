"""
AURA JUDGE Agent
CrewAI agent that evaluates debates and renders verdicts
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from crewai import Agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

from app.core.logging import logger
from app.core.config import settings
from app.agents.prompts.judge_agent_prompts import (
    JUDGE_AGENT_SYSTEM,
    get_round_scoring_prompt,
    get_final_verdict_prompt
)
from app.agents.tools.knowledge_tools import get_all_agent_tools


class JudgeAgent:
    """
    JUDGE Agent - Evaluates debate rounds and renders final verdicts.
    Scores arguments, assesses evidence quality, and determines truth.
    """
    
    VERDICTS = ["TRUE", "FALSE", "MISLEADING", "UNVERIFIABLE"]
    
    def __init__(self, claim_category: str = "general"):
        self.category = claim_category
        self.agent = None
        self._initialize_agent()
    
    def _initialize_agent(self):
        """Initialize the CrewAI agent."""
        llm = self._get_llm()
        tools = get_all_agent_tools()
        system_prompt = JUDGE_AGENT_SYSTEM
        
        self.agent = Agent(
            role="Judge",
            goal=(
                "Fairly evaluate debate arguments, score evidence quality, "
                "and render accurate verdicts based on the preponderance of evidence."
            ),
            backstory=system_prompt,
            llm=llm,
            tools=tools,
            verbose=True,
            allow_delegation=False,
            max_iter=2
        )
    
    def _get_llm(self):
        """Get LLM instance with lower temperature for consistency."""
        try:
            if settings.GOOGLE_API_KEY:
                return ChatGoogleGenerativeAI(
                    model=settings.GEMINI_MODEL,
                    google_api_key=settings.GOOGLE_API_KEY,
                    temperature=0.3,  # Low temp for consistency
                    max_output_tokens=1500
                )
        except Exception as e:
            logger.warning(f"Gemini unavailable: {e}")
        
        try:
            if settings.GROQ_API_KEY:
                return ChatGroq(
                    model=settings.GROQ_MODEL,
                    groq_api_key=settings.GROQ_API_KEY,
                    temperature=0.3
                )
        except Exception as e:
            logger.error(f"Groq unavailable: {e}")
        
        raise RuntimeError("No LLM available")
    
    async def evaluate_round(
        self,
        claim: str,
        round_number: int,
        exchanges: List[Dict],
        evidence_cited: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a single debate round and score each agent.
        """
        start_time = datetime.utcnow()
        
        context = self._build_round_context(
            claim=claim,
            round_number=round_number,
            exchanges=exchanges,
            evidence_cited=evidence_cited
        )
        
        try:
            # Extract arguments from exchanges
            for_args = [ex for ex in exchanges if ex.get('agent') == 'for']
            against_args = [ex for ex in exchanges if ex.get('agent') == 'against']
            neutral_analysis = next((ex.get('analysis', '') for ex in exchanges if ex.get('agent') == 'neutral'), '')
            
            prompt = get_round_scoring_prompt(
                round_number=round_number,
                for_arguments=for_args,
                against_arguments=against_args,
                neutral_analysis=neutral_analysis
            )
            
            response = await self._execute_agent(prompt)
            scores = self._parse_scores(response.get("output", ""))
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                "round": round_number,
                "scores": scores,
                "round_winner": self._determine_round_winner(scores),
                "key_evidence": self._extract_key_evidence(response.get("output", "")),
                "areas_for_next_round": self._extract_focus_areas(response.get("output", "")),
                "judge_notes": response.get("output", "")[:500],
                "processing_time_seconds": round(processing_time, 2),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Judge round evaluation failed: {e}")
            return {
                "round": round_number,
                "error": True,
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def render_final_verdict(
        self,
        claim: str,
        all_rounds: List[Dict],
        quick_classification: Dict = None
    ) -> Dict[str, Any]:
        """
        Render the final verdict after all debate rounds.
        """
        start_time = datetime.utcnow()
        
        context = self._build_final_context(
            claim=claim,
            all_rounds=all_rounds,
            quick_classification=quick_classification
        )
        
        try:
            # Calculate totals
            for_total = sum(
                rd.get('scores', {}).get('for_agent', {}).get('weighted_total', 0)
                for rd in all_rounds
            )
            against_total = sum(
                rd.get('scores', {}).get('against_agent', {}).get('weighted_total', 0)
                for rd in all_rounds
            )
            
            prompt = get_final_verdict_prompt(
                claim=claim,
                quick_classification=quick_classification or {},
                round_scores=all_rounds,
                for_total=for_total,
                against_total=against_total,
                key_evidence=[]
            )
            
            response = await self._execute_agent(prompt)
            verdict_data = self._parse_final_verdict(response.get("output", ""))
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                "verdict": verdict_data.get("verdict", "UNVERIFIABLE"),
                "confidence": verdict_data.get("confidence", 0.5),
                "confidence_level": self._get_confidence_level(verdict_data.get("confidence", 0.5)),
                "reasoning_summary": verdict_data.get("reasoning", ""),
                "reasoning_detailed": response.get("output", ""),
                "key_evidence": verdict_data.get("key_evidence", []),
                "agent_scores_final": self._calculate_final_scores(all_rounds),
                "dissenting_points": verdict_data.get("dissenting", []),
                "processing_time_seconds": round(processing_time, 2),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Judge final verdict failed: {e}")
            return {
                "verdict": "UNVERIFIABLE",
                "confidence": 0.0,
                "error": True,
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _execute_agent(self, prompt: str) -> Dict[str, Any]:
        """Execute agent with the given prompt."""
        llm = self._get_llm()
        response = await llm.ainvoke(prompt)
        return {"output": response.content}
    
    def _build_round_context(
        self,
        claim: str,
        round_number: int,
        exchanges: List[Dict],
        evidence_cited: List[Dict] = None
    ) -> str:
        """Build context for round evaluation."""
        context_parts = [f"CLAIM: {claim}", f"ROUND: {round_number}\n"]
        
        context_parts.append("EXCHANGES THIS ROUND:")
        for ex in exchanges:
            agent = ex.get("agent", "unknown")
            role = ex.get("role", agent)
            argument = ex.get("argument", ex.get("analysis", ""))[:400]
            context_parts.append(f"\n{role.upper()} ({agent}):\n{argument}")
        
        return "\n".join(context_parts)
    
    def _build_final_context(
        self,
        claim: str,
        all_rounds: List[Dict],
        quick_classification: Dict = None
    ) -> str:
        """Build context for final verdict."""
        context_parts = [f"CLAIM: {claim}\n"]
        
        if quick_classification:
            context_parts.append(
                f"QUICK CLASSIFICATION: {quick_classification.get('verdict', 'N/A')} "
                f"(confidence: {quick_classification.get('confidence', 0):.0%})\n"
            )
        
        context_parts.append("ROUND SUMMARIES:")
        for rd in all_rounds:
            round_num = rd.get("round", "?")
            winner = rd.get("round_winner", "tie")
            notes = rd.get("judge_notes", "")[:200]
            context_parts.append(f"\nRound {round_num} Winner: {winner}\nNotes: {notes}")
        
        return "\n".join(context_parts)
    
    def _parse_scores(self, output: str) -> Dict[str, Dict]:
        """Parse agent scores from judge output."""
        scores = {
            "for_agent": {"argument_strength": 5, "evidence_quality": 5, "weighted_total": 5},
            "against_agent": {"argument_strength": 5, "evidence_quality": 5, "weighted_total": 5},
            "neutral_agent": {"analysis_quality": 5, "objectivity": 5, "weighted_total": 5}
        }
        
        output_lower = output.lower()
        
        # Simple parsing based on keywords
        if "against" in output_lower and ("stronger" in output_lower or "better" in output_lower):
            scores["against_agent"]["weighted_total"] = 7
            scores["for_agent"]["weighted_total"] = 4
        elif "for" in output_lower and ("stronger" in output_lower or "better" in output_lower):
            scores["for_agent"]["weighted_total"] = 7
            scores["against_agent"]["weighted_total"] = 4
        
        return scores
    
    def _parse_final_verdict(self, output: str) -> Dict[str, Any]:
        """Parse final verdict from judge output."""
        output_lower = output.lower()
        
        # Determine verdict
        if "false" in output_lower:
            verdict = "FALSE"
            confidence = 0.85
        elif "true" in output_lower and "not true" not in output_lower:
            verdict = "TRUE"
            confidence = 0.75
        elif "misleading" in output_lower:
            verdict = "MISLEADING"
            confidence = 0.70
        else:
            verdict = "UNVERIFIABLE"
            confidence = 0.50
        
        # Extract reasoning
        reasoning = output[:300] if output else "Insufficient evidence"
        
        return {
            "verdict": verdict,
            "confidence": confidence,
            "reasoning": reasoning,
            "key_evidence": [],
            "dissenting": []
        }
    
    def _determine_round_winner(self, scores: Dict) -> str:
        """Determine round winner from scores."""
        for_score = scores.get("for_agent", {}).get("weighted_total", 5)
        against_score = scores.get("against_agent", {}).get("weighted_total", 5)
        
        if against_score > for_score + 1:
            return "against"
        elif for_score > against_score + 1:
            return "for"
        return "tie"
    
    def _extract_key_evidence(self, output: str) -> List[str]:
        """Extract key evidence mentioned."""
        evidence = []
        keywords = ["who", "cdc", "reuters", "evidence", "source", "according"]
        for kw in keywords:
            if kw in output.lower():
                # Find the sentence containing the keyword
                for sentence in output.split("."):
                    if kw in sentence.lower():
                        evidence.append(sentence.strip()[:100])
                        break
        return evidence[:3]
    
    def _extract_focus_areas(self, output: str) -> List[str]:
        """Extract focus areas for next round."""
        areas = []
        if "need" in output.lower() or "should" in output.lower():
            for sentence in output.split("."):
                if "need" in sentence.lower() or "should" in sentence.lower():
                    areas.append(sentence.strip()[:100])
        return areas[:2]
    
    def _calculate_final_scores(self, all_rounds: List[Dict]) -> Dict[str, float]:
        """Calculate final cumulative scores."""
        for_total = 0
        against_total = 0
        neutral_total = 0
        
        for rd in all_rounds:
            scores = rd.get("scores", {})
            for_total += scores.get("for_agent", {}).get("weighted_total", 5)
            against_total += scores.get("against_agent", {}).get("weighted_total", 5)
            neutral_total += scores.get("neutral_agent", {}).get("weighted_total", 5)
        
        return {
            "for": round(for_total, 1),
            "against": round(against_total, 1),
            "neutral": round(neutral_total, 1)
        }
    
    def _get_confidence_level(self, confidence: float) -> str:
        """Convert confidence score to level."""
        if confidence >= 0.9:
            return "definitive"
        elif confidence >= 0.75:
            return "high"
        elif confidence >= 0.5:
            return "medium"
        return "low"


def create_judge_agent(claim_category: str = "general") -> JudgeAgent:
    """Factory function to create JUDGE agent."""
    return JudgeAgent(claim_category=claim_category)
