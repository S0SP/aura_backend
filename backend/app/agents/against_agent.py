"""
AURA AGAINST Agent (Skeptic)
CrewAI agent that challenges and refutes claims
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from crewai import Agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

from app.core.logging import logger
from app.core.config import settings
from app.agents.prompts.against_agent_prompts import (
    get_against_system_prompt,
    get_against_round_prompt
)
from app.agents.tools.knowledge_tools import get_all_agent_tools


class AgainstAgent:
    """
    AGAINST Agent (Skeptic) - Challenges the claim's validity.
    Uses evidence to build the strongest possible case against the claim.
    """
    
    def __init__(self, claim_category: str = "general"):
        self.category = claim_category
        self.agent = None
        self._initialize_agent()
    
    def _initialize_agent(self):
        """Initialize the CrewAI agent with LLM and tools."""
        llm = self._get_llm()
        tools = get_all_agent_tools()
        system_prompt = get_against_system_prompt(self.category)
        
        self.agent = Agent(
            role="Skeptic",
            goal=(
                "Challenge the claim with critical analysis. "
                "Find and present evidence that suggests the claim is false or misleading."
            ),
            backstory=system_prompt,
            llm=llm,
            tools=tools,
            verbose=True,
            allow_delegation=False,
            max_iter=3
        )
    
    def _get_llm(self):
        """Get LLM instance (Gemini primary, Groq backup)."""
        try:
            if settings.GOOGLE_API_KEY:
                return ChatGoogleGenerativeAI(
                    model=settings.GEMINI_MODEL,
                    google_api_key=settings.GOOGLE_API_KEY,
                    temperature=0.7,
                    max_output_tokens=1024
                )
        except Exception as e:
            logger.warning(f"Gemini unavailable: {e}")
        
        try:
            if settings.GROQ_API_KEY:
                return ChatGroq(
                    model=settings.GROQ_MODEL,
                    groq_api_key=settings.GROQ_API_KEY,
                    temperature=0.7
                )
        except Exception as e:
            logger.error(f"Groq unavailable: {e}")
        
        raise RuntimeError("No LLM available")
    
    async def generate_argument(
        self,
        claim: str,
        round_number: int,
        previous_exchanges: List[Dict] = None,
        evidence: List[Dict] = None,
        for_agent_argument: str = None,
        focus_areas: List[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a counter-argument challenging the claim.
        """
        start_time = datetime.utcnow()
        
        context = self._build_context(
            claim=claim,
            round_number=round_number,
            previous_exchanges=previous_exchanges,
            evidence=evidence,
            for_agent_argument=for_agent_argument,
            focus_areas=focus_areas
        )
        
        try:
            prompt = get_against_round_prompt(
                round_number=round_number,
                claim=claim,
                context=context
            )
            
            response = await self._execute_agent(prompt)
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                "agent": "against",
                "role": "Skeptic",
                "round": round_number,
                "argument": response.get("output", ""),
                "counter_points": self._extract_counter_points(response.get("output", "")),
                "evidence_cited": response.get("evidence_cited", []),
                "confidence": self._calculate_confidence(response),
                "processing_time_seconds": round(processing_time, 2),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"AGAINST agent argument generation failed: {e}")
            return {
                "agent": "against",
                "role": "Skeptic",
                "round": round_number,
                "argument": f"Unable to generate counter-argument: {str(e)}",
                "error": True,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _execute_agent(self, prompt: str) -> Dict[str, Any]:
        """Execute agent with the given prompt."""
        llm = self._get_llm()
        response = await llm.ainvoke(prompt)
        return {"output": response.content, "evidence_cited": []}
    
    def _build_context(
        self,
        claim: str,
        round_number: int,
        previous_exchanges: List[Dict] = None,
        evidence: List[Dict] = None,
        for_agent_argument: str = None,
        focus_areas: List[str] = None
    ) -> str:
        """Build context string for the agent."""
        context_parts = [f"CLAIM TO CHALLENGE: {claim}"]
        
        if for_agent_argument:
            context_parts.append(f"\nFOR AGENT'S ARGUMENT TO COUNTER:\n{for_agent_argument[:500]}")
        
        if evidence:
            context_parts.append("\nAVAILABLE EVIDENCE:")
            for i, e in enumerate(evidence[:5], 1):
                context_parts.append(f"{i}. {e.get('title', e.get('claim', 'Unknown'))}")
        
        if previous_exchanges:
            context_parts.append("\nPREVIOUS EXCHANGES:")
            for ex in previous_exchanges[-3:]:
                context_parts.append(f"- {ex.get('agent', 'Unknown')}: {ex.get('argument', '')[:200]}...")
        
        if focus_areas:
            context_parts.append(f"\nFOCUS AREAS: {', '.join(focus_areas)}")
        
        return "\n".join(context_parts)
    
    def _extract_counter_points(self, argument: str) -> List[str]:
        """Extract counter points from argument."""
        points = []
        lines = argument.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith(("-", "*", "1", "2", "3")) or "however" in line.lower():
                points.append(line[:100])
        return points[:3]
    
    def _calculate_confidence(self, response: Dict) -> float:
        """Calculate confidence score."""
        output = response.get("output", "")
        evidence = response.get("evidence_cited", [])
        
        confidence = 0.5
        if len(output) > 200:
            confidence += 0.1
        if len(evidence) > 0:
            confidence += 0.2
        if "false" in output.lower() or "misleading" in output.lower():
            confidence += 0.1
        if "who" in output.lower() or "cdc" in output.lower():
            confidence += 0.1
        
        return min(confidence, 1.0)


def create_against_agent(claim_category: str = "general") -> AgainstAgent:
    """Factory function to create AGAINST agent."""
    return AgainstAgent(claim_category=claim_category)
