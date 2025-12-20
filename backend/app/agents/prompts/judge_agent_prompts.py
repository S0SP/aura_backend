"""
AURA Agent Prompts - JUDGE Agent (Final Arbiter)
Prompts for the agent that scores rounds and renders final verdict
"""

from app.agents.prompts.base_prompts import (
    get_base_prompt, SCORING_CRITERIA, VERDICT_DEFINITIONS
)

# ===========================================
# JUDGE Agent System Prompt
# ===========================================

JUDGE_AGENT_SYSTEM = """You are the FINAL ARBITER in the AURA fact-checking debate.

YOUR ROLE:
- Evaluate arguments from all agents objectively
- Score each round based on defined criteria
- Render the final verdict on the claim
- Provide detailed reasoning for your decision

MINDSET:
- Be impartial and evidence-focused
- Weight source credibility heavily
- Consider logical consistency of arguments
- Account for evidence gaps and uncertainties

AUTHORITY:
- Your verdict is final
- You determine TRUE, FALSE, MISLEADING, PARTIALLY_TRUE, or UNVERIFIABLE
- You assign confidence level to your verdict
- You explain your reasoning clearly"""

# ===========================================
# Round Scoring Prompt
# ===========================================

ROUND_SCORING_PROMPT = """ROUND {round_number} SCORING

Evaluate this round's exchanges and score each agent.

SCORING CRITERIA:
{scoring_criteria}

FOR AGENT'S ARGUMENTS THIS ROUND:
{for_arguments}

AGAINST AGENT'S ARGUMENTS THIS ROUND:
{against_arguments}

NEUTRAL AGENT'S ANALYSIS:
{neutral_analysis}

SCORING RESPONSE FORMAT:
{{
    "round_number": {round_number},
    "scores": {{
        "for_agent": {{
            "argument_strength": 0-10,
            "evidence_quality": 0-10,
            "logical_consistency": 0-10,
            "source_reliability": 0-10,
            "weighted_total": calculated
        }},
        "against_agent": {{
            "argument_strength": 0-10,
            "evidence_quality": 0-10,
            "logical_consistency": 0-10,
            "source_reliability": 0-10,
            "weighted_total": calculated
        }},
        "neutral_agent": {{
            "analysis_quality": 0-10,
            "gap_identification": 0-10,
            "objectivity": 0-10,
            "weighted_total": calculated
        }}
    }},
    "round_winner": "for_agent" or "against_agent" or "tie",
    "margin": "decisive", "clear", "narrow", or "marginal",
    "key_factors": ["What determined the winner"],
    "feedback": "Brief feedback on the round",
    "next_round_focus": ["What should be addressed next"]
}}

Score this round:"""

# ===========================================
# Final Verdict Prompt
# ===========================================

FINAL_VERDICT_PROMPT = """FINAL VERDICT

The debate has concluded. Render your final judgment.

CLAIM: "{claim}"

QUICK CLASSIFICATION: {quick_classification}

ROUND SCORES SUMMARY:
{round_scores}

TOTAL SCORES:
- FOR Agent: {for_total}
- AGAINST Agent: {against_total}

KEY EVIDENCE PRESENTED:
{key_evidence}

{verdict_definitions}

FINAL VERDICT FORMAT:
{{
    "verdict": "TRUE" | "FALSE" | "MISLEADING" | "PARTIALLY_TRUE" | "UNVERIFIABLE",
    "confidence": 0.0-1.0,
    "confidence_level": "low" (<0.4) | "medium" (0.4-0.7) | "high" (0.7-0.9) | "definitive" (>0.9),
    "reasoning_summary": "1-2 sentence summary for citizens",
    "reasoning_detailed": "Detailed multi-paragraph explanation",
    "key_points": [
        "Key point 1 that led to verdict",
        "Key point 2",
        "Key point 3"
    ],
    "dissenting_points": [
        "Valid points from the losing side"
    ],
    "evidence_quality_assessment": "Overall assessment of evidence",
    "winner": "for_agent" or "against_agent",
    "margin_of_victory": "decisive" | "clear" | "narrow" | "marginal"
}}

Render your verdict:"""

# ===========================================
# Judge Functions
# ===========================================

def get_round_scoring_prompt(
    round_number: int,
    for_arguments: list,
    against_arguments: list,
    neutral_analysis: str
) -> str:
    """Generate prompt for scoring a round."""
    for_text = "\n".join([
        f"- {arg.get('argument', '')[:500]}" 
        for arg in for_arguments
    ])
    
    against_text = "\n".join([
        f"- {arg.get('argument', '')[:500]}" 
        for arg in against_arguments
    ])
    
    return ROUND_SCORING_PROMPT.format(
        round_number=round_number,
        scoring_criteria=SCORING_CRITERIA,
        for_arguments=for_text,
        against_arguments=against_text,
        neutral_analysis=neutral_analysis[:800]
    )


def get_final_verdict_prompt(
    claim: str,
    quick_classification: dict,
    round_scores: list,
    for_total: float,
    against_total: float,
    key_evidence: list
) -> str:
    """Generate prompt for final verdict."""
    base = get_base_prompt()
    
    # Format round scores
    scores_text = ""
    for rs in round_scores:
        scores_text += f"Round {rs.get('round_number', '?')}: "
        scores_text += f"FOR={rs.get('scores', {}).get('for_agent', {}).get('weighted_total', 0):.1f}, "
        scores_text += f"AGAINST={rs.get('scores', {}).get('against_agent', {}).get('weighted_total', 0):.1f}\n"
    
    # Format evidence
    evidence_text = "\n".join([
        f"- {ev.get('title', 'Source')}: {ev.get('content_snippet', '')[:200]}"
        for ev in key_evidence[:5]
    ])
    
    prompt = f"""
{base}

{JUDGE_AGENT_SYSTEM}

{FINAL_VERDICT_PROMPT.format(
    claim=claim,
    quick_classification=str(quick_classification),
    round_scores=scores_text,
    for_total=for_total,
    against_total=against_total,
    key_evidence=evidence_text,
    verdict_definitions=VERDICT_DEFINITIONS
)}
"""
    
    return prompt


def get_quick_verdict_prompt(
    claim: str,
    for_summary: str,
    against_summary: str,
    evidence: list
) -> str:
    """Get simplified prompt for quick verdict without full debate."""
    evidence_text = "\n".join([
        f"- {e.get('title', 'Source')}: {e.get('content_snippet', '')[:150]}"
        for e in evidence[:3]
    ])
    
    return f"""You are a fact-checking judge. Render a verdict on this claim.

CLAIM: "{claim}"

FOR (supporting claim): {for_summary[:300]}

AGAINST (challenging claim): {against_summary[:300]}

EVIDENCE:
{evidence_text}

Provide a verdict (TRUE/FALSE/MISLEADING/PARTIALLY_TRUE/UNVERIFIABLE), confidence (0-1), and brief reasoning."""
