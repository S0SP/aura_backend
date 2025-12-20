"""
AURA Service - LLM Provider
LangChain integration with Google Gemini and Groq
"""

from typing import Optional, List, Dict, Any
from functools import lru_cache

from app.core.config import settings
from app.core.logging import logger


# ===========================================
# LLM Providers
# ===========================================

_gemini_llm = None
_groq_llm = None


def get_gemini_llm():
    """
    Get Google Gemini LLM instance.
    
    Returns:
        ChatGoogleGenerativeAI instance
    """
    global _gemini_llm
    
    if _gemini_llm is None:
        if not settings.GOOGLE_API_KEY:
            logger.warning("Google API key not configured")
            return None
        
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            
            _gemini_llm = ChatGoogleGenerativeAI(
                model=settings.GEMINI_MODEL,
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=0.7,
                max_output_tokens=2048,
                convert_system_message_to_human=True
            )
            logger.info(f"✅ Gemini LLM initialized: {settings.GEMINI_MODEL}")
        except ImportError:
            logger.error("langchain-google-genai not installed")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
    
    return _gemini_llm


def get_groq_llm():
    """
    Get Groq LLM instance (backup).
    
    Returns:
        ChatGroq instance
    """
    global _groq_llm
    
    if _groq_llm is None:
        if not settings.GROQ_API_KEY:
            logger.warning("Groq API key not configured")
            return None
        
        try:
            from langchain_groq import ChatGroq
            
            _groq_llm = ChatGroq(
                model=settings.GROQ_MODEL,
                groq_api_key=settings.GROQ_API_KEY,
                temperature=0.7,
                max_tokens=2048
            )
            logger.info(f"✅ Groq LLM initialized: {settings.GROQ_MODEL}")
        except ImportError:
            logger.error("langchain-groq not installed")
        except Exception as e:
            logger.error(f"Failed to initialize Groq: {e}")
    
    return _groq_llm


def get_llm(prefer_fast: bool = False):
    """
    Get the best available LLM.
    
    Args:
        prefer_fast: If True, prefer faster model (Groq)
        
    Returns:
        LLM instance
    """
    if prefer_fast:
        llm = get_groq_llm()
        if llm:
            return llm
    
    llm = get_gemini_llm()
    if llm:
        return llm
    
    return get_groq_llm()


# ===========================================
# LangChain Chains
# ===========================================

def create_claim_analysis_chain():
    """
    Create a chain for analyzing claims.
    
    Returns:
        LangChain chain for claim analysis
    """
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import JsonOutputParser
    
    llm = get_llm()
    if not llm:
        raise RuntimeError("No LLM available")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert fact-checker. Analyze the given claim and identify:
1. The main assertion being made
2. Key entities (people, organizations, places)
3. Time references if any
4. Category (health, political, financial, science, social, disaster)
5. Potential search queries to verify this claim

Respond in JSON format with these fields:
- main_assertion: string
- entities: list of strings
- time_references: list of strings
- category: string
- search_queries: list of 3-5 search queries
- requires_expertise: boolean
- language: detected language code"""),
        ("human", "Claim: {claim}")
    ])
    
    chain = prompt | llm | JsonOutputParser()
    return chain


def create_evidence_synthesis_chain():
    """
    Create a chain for synthesizing evidence.
    
    Returns:
        LangChain chain for evidence synthesis
    """
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import JsonOutputParser
    
    llm = get_llm()
    if not llm:
        raise RuntimeError("No LLM available")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert fact-checker. Given a claim and evidence from multiple sources,
synthesize the evidence and provide a preliminary assessment.

Analyze:
1. How well does the evidence support or refute the claim?
2. Are the sources credible?
3. Is there consensus among sources?
4. What gaps exist in the evidence?

Respond in JSON format:
- supports_claim: boolean or null if unclear
- confidence: float 0-1
- key_supporting_evidence: list of strings
- key_refuting_evidence: list of strings
- evidence_gaps: list of strings
- source_agreement: "strong", "moderate", "weak", or "conflicting"
- preliminary_verdict: "TRUE", "FALSE", "MISLEADING", "PARTIALLY_TRUE", or "UNVERIFIABLE" """),
        ("human", """Claim: {claim}

Evidence:
{evidence}""")
    ])
    
    chain = prompt | llm | JsonOutputParser()
    return chain


def create_verdict_generation_chain():
    """
    Create a chain for generating final verdict.
    
    Returns:
        LangChain chain for verdict generation
    """
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import JsonOutputParser
    
    llm = get_llm()
    if not llm:
        raise RuntimeError("No LLM available")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are the final arbiter in a fact-checking system. Based on the debate between
agents and the evidence presented, generate a final verdict.

Consider:
1. Quick classification result
2. Debate scores and arguments
3. Quality and quantity of evidence
4. Source credibility

Generate a comprehensive verdict with clear reasoning.

Respond in JSON format:
- verdict: "TRUE", "FALSE", "MISLEADING", "PARTIALLY_TRUE", or "UNVERIFIABLE"
- confidence: float 0-1
- confidence_level: "low" (<0.4), "medium" (0.4-0.7), "high" (0.7-0.9), or "definitive" (>0.9)
- reasoning_summary: 1-2 sentence summary
- reasoning_detailed: detailed explanation
- key_points: list of key points that led to this verdict
- dissenting_points: any valid points from the opposing view"""),
        ("human", """Claim: {claim}

Quick Classification: {quick_classification}

Debate Summary: {debate_summary}

For Agent Score: {for_score}
Against Agent Score: {against_score}

Key Evidence: {evidence}""")
    ])
    
    chain = prompt | llm | JsonOutputParser()
    return chain


# ===========================================
# Direct LLM Calls
# ===========================================

async def analyze_claim(claim: str) -> Dict[str, Any]:
    """
    Analyze a claim using LLM.
    
    Args:
        claim: The claim text to analyze
        
    Returns:
        Analysis results
    """
    try:
        chain = create_claim_analysis_chain()
        result = await chain.ainvoke({"claim": claim})
        return result
    except Exception as e:
        logger.error(f"Claim analysis failed: {e}")
        return {
            "main_assertion": claim,
            "entities": [],
            "time_references": [],
            "category": "other",
            "search_queries": [claim],
            "requires_expertise": False,
            "language": "en"
        }


async def synthesize_evidence(
    claim: str, 
    evidence: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Synthesize evidence for a claim.
    
    Args:
        claim: The claim being verified
        evidence: List of evidence items
        
    Returns:
        Synthesis results
    """
    try:
        chain = create_evidence_synthesis_chain()
        
        # Format evidence for prompt
        evidence_text = "\n".join([
            f"- Source: {e.get('source', 'Unknown')}\n  "
            f"Title: {e.get('title', 'N/A')}\n  "
            f"Content: {e.get('content_snippet', '')[:300]}"
            for e in evidence[:10]  # Limit to 10 items
        ])
        
        result = await chain.ainvoke({
            "claim": claim,
            "evidence": evidence_text
        })
        return result
    except Exception as e:
        logger.error(f"Evidence synthesis failed: {e}")
        return {
            "supports_claim": None,
            "confidence": 0.5,
            "key_supporting_evidence": [],
            "key_refuting_evidence": [],
            "evidence_gaps": ["Analysis failed"],
            "source_agreement": "unknown",
            "preliminary_verdict": "UNVERIFIABLE"
        }


async def generate_verdict(
    claim: str,
    quick_classification: Dict[str, Any],
    debate_summary: Dict[str, Any],
    for_score: float,
    against_score: float,
    evidence: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Generate final verdict.
    
    Args:
        claim: The claim being verified
        quick_classification: Quick classification result
        debate_summary: Summary of debate
        for_score: For agent's total score
        against_score: Against agent's total score
        evidence: Key evidence items
        
    Returns:
        Final verdict
    """
    try:
        chain = create_verdict_generation_chain()
        
        evidence_text = "\n".join([
            f"- {e.get('title', 'Source')}: {e.get('content_snippet', '')[:200]}"
            for e in evidence[:5]
        ])
        
        result = await chain.ainvoke({
            "claim": claim,
            "quick_classification": str(quick_classification),
            "debate_summary": str(debate_summary),
            "for_score": for_score,
            "against_score": against_score,
            "evidence": evidence_text
        })
        return result
    except Exception as e:
        logger.error(f"Verdict generation failed: {e}")
        return {
            "verdict": "UNVERIFIABLE",
            "confidence": 0.5,
            "confidence_level": "low",
            "reasoning_summary": "Unable to determine verdict due to processing error.",
            "reasoning_detailed": str(e),
            "key_points": [],
            "dissenting_points": []
        }
