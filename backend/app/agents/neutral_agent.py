"""
AURA NEUTRAL Agent (Analyst)
CrewAI agent that provides balanced analysis
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from crewai import Agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

from app.core.logging import logger
from app.core.config import settings
from app.agents.prompts.neutral_agent_prompts import (
    get_neutral_system_prompt,
    get_neutral_round_prompt
)
from app.agents.tools.knowledge_tools import get_all_agent_tools


class NeutralAgent:
    """
    NEUTRAL Agent (Analyst) - Provides balanced, objective analysis.
    Identifies gaps, asks questions, and synthesizes both perspectives.
    """
    
    def __init__(self, claim_category: str = "general"):
        self.category = claim_category
        self.agent = None
        self._initialize_agent()
    
    def _initialize_agent(self):
        """Initialize the CrewAI agent."""
        llm = self._get_llm()
        tools = get_all_agent_tools()
        system_prompt = get_neutral_system_prompt(self.category)
        
        self.agent = Agent(
            role="Analyst",
            goal=(
                "Provide objective, balanced analysis of both perspectives. "
                "Identify gaps in arguments, ask clarifying questions, and synthesize evidence."
            ),
            backstory=system_prompt,
            llm=llm,
            tools=tools,
            verbose=True,
            allow_delegation=False,
            max_iter=3
        )
    
    def _get_llm(self):
        """Get LLM instance."""
        try:
            if settings.GOOGLE_API_KEY:
                return ChatGoogleGenerativeAI(
                    model=settings.GEMINI_MODEL,
                    google_api_key=settings.GOOGLE_API_KEY,
                    temperature=0.5,  # Lower temp for objectivity
                    max_output_tokens=1024
                )
        except Exception as e:
            logger.warning(f"Gemini unavailable: {e}")
        
        try:
            if settings.GROQ_API_KEY:
                return ChatGroq(
                    model=settings.GROQ_MODEL,
                    groq_api_key=settings.GROQ_API_KEY,
                    temperature=0.5
                )
        except Exception as e:
            logger.error(f"Groq unavailable: {e}")
        
        raise RuntimeError("No LLM available")
    
    async def generate_analysis(
        self,
        claim: str,
        round_number: int,
        for_argument: str,
        against_argument: str,
        previous_exchanges: List[Dict] = None,
        evidence: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Generate balanced analysis of both perspectives.
        """
        start_time = datetime.utcnow()
        
        context = self._build_context(
            claim=claim,
            round_number=round_number,
            for_argument=for_argument,
            against_argument=against_argument,
            previous_exchanges=previous_exchanges,
            evidence=evidence
        )
        
        try:
            prompt = get_neutral_round_prompt(
                round_number=round_number,
                claim=claim,
                context=context
            )
            
            response = await self._execute_agent(prompt)
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                "agent": "neutral",
                "role": "Analyst",
                "round": round_number,
                "analysis": response.get("output", ""),
                "gaps_identified": self._extract_gaps(response.get("output", "")),
                "questions_raised": self._extract_questions(response.get("output", "")),
                "synthesis": self._extract_synthesis(response.get("output", "")),
                "balance_assessment": self._assess_balance(for_argument, against_argument),
                "processing_time_seconds": round(processing_time, 2),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"NEUTRAL agent analysis failed: {e}")
            return {
                "agent": "neutral",
                "role": "Analyst",
                "round": round_number,
                "analysis": f"Unable to generate analysis: {str(e)}",
                "error": True,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _execute_agent(self, prompt: str) -> Dict[str, Any]:
        """Execute agent with the given prompt."""
        llm = self._get_llm()
        response = await llm.ainvoke(prompt)
        return {"output": response.content}
    
    def _build_context(
        self,
        claim: str,
        round_number: int,
        for_argument: str,
        against_argument: str,
        previous_exchanges: List[Dict] = None,
        evidence: List[Dict] = None
    ) -> str:
        """Build context string for the agent."""
        context_parts = [
            f"CLAIM: {claim}",
            f"\nFOR AGENT (ADVOCATE) ARGUMENT:\n{for_argument[:600]}",
            f"\nAGAINST AGENT (SKEPTIC) ARGUMENT:\n{against_argument[:600]}"
        ]
        
        if evidence:
            context_parts.append("\nAVAILABLE EVIDENCE:")
            for i, e in enumerate(evidence[:3], 1):
                context_parts.append(f"{i}. {e.get('title', e.get('claim', 'Unknown'))}")
        
        return "\n".join(context_parts)
    
    def _extract_gaps(self, analysis: str) -> List[str]:
        """Extract identified gaps from analysis."""
        gaps = []
        lines = analysis.lower().split("\n")
        for line in lines:
            if "gap" in line or "missing" in line or "lack" in line:
                gaps.append(line.strip()[:100])
        return gaps[:3]
    
    def _extract_questions(self, analysis: str) -> List[str]:
        """Extract questions raised from analysis."""
        questions = []
        lines = analysis.split("\n")
        for line in lines:
            if "?" in line:
                questions.append(line.strip()[:100])
        return questions[:3]
    
    def _extract_synthesis(self, analysis: str) -> str:
        """Extract synthesis or summary from analysis."""
        lines = analysis.split("\n")
        for line in lines:
            if "overall" in line.lower() or "conclusion" in line.lower() or "summary" in line.lower():
                return line.strip()[:200]
        return analysis[:200] if analysis else ""
    
    def _assess_balance(self, for_arg: str, against_arg: str) -> Dict[str, Any]:
        """Assess the balance between the two arguments."""
        for_strength = len(for_arg) / 100
        against_strength = len(against_arg) / 100
        
        if against_strength > for_strength * 1.5:
            leaning = "AGAINST (Skeptic stronger)"
        elif for_strength > against_strength * 1.5:
            leaning = "FOR (Advocate stronger)"
        else:
            leaning = "BALANCED"
        
        return {
            "for_strength": min(for_strength, 10),
            "against_strength": min(against_strength, 10),
            "leaning": leaning
        }


def create_neutral_agent(claim_category: str = "general") -> NeutralAgent:
    """Factory function to create NEUTRAL agent."""
    return NeutralAgent(claim_category=claim_category)
