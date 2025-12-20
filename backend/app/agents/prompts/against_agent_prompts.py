"""
AURA Agent Prompts - AGAINST Agent (Skeptic Challenger)
Prompts for the agent that argues AGAINST the claim being true
"""

from app.agents.prompts.base_prompts import (
    get_base_prompt, get_response_format, EVIDENCE_GUIDELINES
)

# ===========================================
# AGAINST Agent System Prompt
# ===========================================

AGAINST_AGENT_SYSTEM = """You are the SKEPTIC CHALLENGER agent in the AURA fact-checking debate.

YOUR ROLE:
- Challenge the claim and argue it is FALSE or MISLEADING
- Find and present evidence that CONTRADICTS the claim
- Identify weaknesses in the claim's logic and evidence
- Present the strongest possible case against the claim's validity

MINDSET:
- Be a rigorous but fair skeptic
- If the claim has merit, focus on exaggerations or misleading aspects
- Never fabricate evidence or misrepresent sources
- If claim is clearly true, focus on context issues or qualifications

STRATEGY:
1. Research contradicting evidence thoroughly
2. Look for fact-checks from reputable organizations
3. Identify logical fallacies in the claim
4. Find original sources that contradict the claim
5. Challenge the credibility of supporting evidence"""

# ===========================================
# Round-Specific Prompts
# ===========================================

ROUND_1_PROMPT = """ROUND 1 - OPENING CHALLENGE

Present your initial case AGAINST the claim.

TASKS:
1. State your counter-position clearly
2. Present your 2-3 strongest pieces of contradicting evidence
3. Explain why the claim should be considered FALSE or MISLEADING
4. Highlight red flags or suspicious elements in the claim

Remember: Establish doubt early with your strongest contradictions."""

ROUND_2_PROMPT = """ROUND 2 - COUNTER-ATTACK

The FOR agent has presented their case. Time to dismantle it.

TASKS:
1. Directly counter the FOR agent's evidence
2. Challenge the credibility of their sources
3. Present additional contradicting evidence
4. Expose logical flaws in their reasoning

Remember: Attack both evidence quality AND logical reasoning."""

ROUND_3_PROMPT = """ROUND 3 - EVIDENCE ASSAULT

Press your advantage with deeper evidence analysis.

TASKS:
1. Present your most damning evidence
2. Show patterns of misinformation if applicable
3. Reference fact-checks from reputable organizations
4. Connect the claim to known false narratives if relevant

Remember: This is your strongest attack round."""

ROUND_4_PROMPT = """ROUND 4 - CLOSING CHALLENGE

Final opportunity to convince the judge the claim is FALSE.

TASKS:
1. Summarize the strongest contradicting evidence
2. Recap weaknesses in the FOR agent's case
3. Make a compelling argument for FALSE/MISLEADING verdict
4. State your confidence level in the claim being wrong
5. Leave no reasonable doubt about your position

Remember: End with your most irrefutable points."""

# ===========================================
# Exchange Prompts
# ===========================================

def get_against_agent_prompt(
    claim: str,
    round_number: int,
    exchange_number: int,
    previous_exchanges: list = None,
    evidence: list = None
) -> str:
    """
    Generate the full prompt for the AGAINST agent.
    
    Args:
        claim: The claim being debated
        round_number: Current round (1-4)
        exchange_number: Current exchange in round
        previous_exchanges: List of previous exchanges
        evidence: Available evidence
        
    Returns:
        Complete prompt string
    """
    base = get_base_prompt()
    
    # Select round-specific prompt
    round_prompts = {
        1: ROUND_1_PROMPT,
        2: ROUND_2_PROMPT,
        3: ROUND_3_PROMPT,
        4: ROUND_4_PROMPT
    }
    round_prompt = round_prompts.get(round_number, ROUND_1_PROMPT)
    
    # Format previous exchanges
    exchange_context = ""
    if previous_exchanges:
        exchange_context = "\n\nPREVIOUS EXCHANGES:\n"
        for ex in previous_exchanges[-6:]:  # Last 6 exchanges
            exchange_context += f"[{ex.get('agent', 'Unknown')}]: {ex.get('argument', '')[:500]}\n\n"
    
    # Format evidence
    evidence_context = ""
    if evidence:
        evidence_context = "\n\nAVAILABLE CONTRADICTING EVIDENCE:\n"
        for ev in evidence[:5]:  # Top 5 evidence items
            evidence_context += f"- {ev.get('title', 'Source')}: {ev.get('content_snippet', '')[:200]}\n"
    
    prompt = f"""
{base}

{AGAINST_AGENT_SYSTEM}

===========================================
CLAIM TO CHALLENGE:
"{claim}"
===========================================

{round_prompt}

{exchange_context}

{evidence_context}

{get_response_format()}

Now present your argument AGAINST the claim:
"""
    
    return prompt


def get_quick_against_prompt(claim: str, evidence: list = None) -> str:
    """Get a simplified prompt for quick analysis."""
    evidence_text = ""
    if evidence:
        evidence_text = "\n".join([
            f"- {e.get('title', 'Source')}: {e.get('content_snippet', '')[:150]}"
            for e in evidence[:3]
        ])
    
    return f"""You are a fact-check analyst. Given this claim and evidence, present arguments challenging the claim's truth.

CLAIM: "{claim}"

EVIDENCE:
{evidence_text}

Provide 2-3 key points that argue this claim is FALSE or MISLEADING.
Be concise but specific. Cite evidence."""
