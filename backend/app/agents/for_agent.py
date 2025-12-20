"""
AURA FOR Agent (Advocate)
CrewAI agent that argues in support of claims
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from crewai import Agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

from app.core.logging import logger
from app.core.config import settings
from app.agents.prompts.for_agent_prompts import (
    get_for_agent_prompt,
    FOR_AGENT_SYSTEM
)
from app.agents.tools.knowledge_tools import get_all_agent_tools


class ForAgent:
    """
    FOR Agent (Advocate) - Argues in support of the claim's validity.
    Uses evidence to build the strongest possible case for the claim.
    """
    
    def __init__(self, claim_category: str = "general"):
        self.category = claim_category
        self.agent = None
        self._initialize_agent()
    
    def _initialize_agent(self):
        """Initialize the CrewAI agent with LLM and tools."""
        # Get LLM
        llm = self._get_llm()
        
        # Get tools
        tools = get_all_agent_tools()
        
        # Get system prompt based on claim category
        system_prompt = FOR_AGENT_SYSTEM
        
        self.agent = Agent(
            role="Advocate",
            goal=(
                "Build the strongest possible argument supporting the claim. "
                "Find and present evidence that suggests the claim could be true."
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
        focus_areas: List[str] = None
    ) -> Dict[str, Any]:
        """
        Generate an argument supporting the claim.
        
        Args:
            claim: The claim being debated
            round_number: Current round (1-4)
            previous_exchanges: Previous arguments in this debate
            evidence: Available evidence
            focus_areas: Specific areas to address (from judge feedback)
        """
        start_time = datetime.utcnow()
        
        # Build context
        context = self._build_context(
            claim=claim,
            round_number=round_number,
            previous_exchanges=previous_exchanges,
            evidence=evidence,
            focus_areas=focus_areas
        )
        
        try:
            # Get round-specific prompt
            prompt = get_for_agent_prompt(
                claim=claim,
                round_number=round_number,
                exchange_number=1,
                previous_exchanges=previous_exchanges,
                evidence=evidence
            )
            
            # Use CrewAI agent (simplified execution)
            response = await self._execute_agent(prompt)
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                "agent": "for",
                "role": "Advocate",
                "round": round_number,
                "argument": response.get("output", ""),
                "main_points": self._extract_main_points(response.get("output", "")),
                "evidence_cited": response.get("evidence_cited", []),
                "confidence": self._calculate_confidence(response),
                "processing_time_seconds": round(processing_time, 2),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"FOR agent argument generation failed: {e}")
            return {
                "agent": "for",
                "role": "Advocate",
                "round": round_number,
                "argument": f"Unable to generate argument: {str(e)}",
                "error": True,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _execute_agent(self, prompt: str) -> Dict[str, Any]:
        """Execute agent with the given prompt."""
        # Simplified execution - in production use CrewAI Task
        llm = self._get_llm()
        response = await llm.ainvoke(prompt)
        
        return {
            "output": response.content,
            "evidence_cited": []
        }
    
    def _build_context(
        self,
        claim: str,
        round_number: int,
        previous_exchanges: List[Dict] = None,
        evidence: List[Dict] = None,
        focus_areas: List[str] = None
    ) -> str:
        """Build context string for the agent."""
        context_parts = [f"CLAIM: {claim}"]
        
        if evidence:
            context_parts.append("\nAVAILABLE EVIDENCE:")
            for i, e in enumerate(evidence[:5], 1):
                context_parts.append(f"{i}. {e.get('title', e.get('claim', 'Unknown'))}")
        
        if previous_exchanges:
            context_parts.append("\nPREVIOUS EXCHANGES:")
            for ex in previous_exchanges[-3:]:  # Last 3 exchanges
                context_parts.append(f"- {ex.get('agent', 'Unknown')}: {ex.get('argument', '')[:200]}...")
        
        if focus_areas:
            context_parts.append(f"\nFOCUS AREAS: {', '.join(focus_areas)}")
        
        return "\n".join(context_parts)
    
    def _extract_main_points(self, argument: str) -> List[str]:
        """Extract main points from argument."""
        points = []
        lines = argument.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith(("-", "*", "1", "2", "3")):
                points.append(line[:100])
        return points[:3]
    
    def _calculate_confidence(self, response: Dict) -> float:
        """Calculate confidence score based on response quality."""
        # Basic confidence calculation
        output = response.get("output", "")
        evidence = response.get("evidence_cited", [])
        
        confidence = 0.5
        if len(output) > 200:
            confidence += 0.1
        if len(evidence) > 0:
            confidence += 0.2
        if "source" in output.lower() or "according to" in output.lower():
            confidence += 0.1
        
        return min(confidence, 1.0)


def create_for_agent(claim_category: str = "general") -> ForAgent:
    """Factory function to create FOR agent."""
    return ForAgent(claim_category=claim_category)
