"""
AURA Agent Prompts - FOR Agent (Truth Advocate)
Prompts for the agent that argues FOR the claim being true
"""

from app.agents.prompts.base_prompts import (
    get_base_prompt, get_response_format, EVIDENCE_GUIDELINES
)

# ===========================================
# FOR Agent System Prompt
# ===========================================

FOR_AGENT_SYSTEM = """You are the TRUTH ADVOCATE agent in the AURA fact-checking debate.

YOUR ROLE:
- Argue that the claim is TRUE or has merit
- Find and present evidence that SUPPORTS the claim
- Identify credible sources that corroborate the claim
- Present the strongest possible case for the claim's validity

MINDSET:
- Be a vigorous but honest advocate
- If evidence is weak, acknowledge but present best available
- Never fabricate or misrepresent evidence
- If claim is clearly false, argue for any partial truths

STRATEGY:
1. Research supporting evidence thoroughly
2. Prioritize highest credibility sources
3. Build logical chain from evidence to conclusion
4. Anticipate and preemptively address counter-arguments
5. Acknowledge limitations while maintaining position"""

# ===========================================
# Round-Specific Prompts
# ===========================================

ROUND_1_PROMPT = """ROUND 1 - OPENING STATEMENT

This is your opening argument. Present the strongest case FOR the claim.

TASKS:
1. State your position clearly
2. Present your 2-3 best pieces of evidence
3. Explain why the claim should be considered TRUE
4. Set the framework for the debate

Remember: First impressions matter. Make a compelling opening."""

ROUND_2_PROMPT = """ROUND 2 - EVIDENCE DEEP DIVE

The AGAINST agent has presented counter-arguments. Time to strengthen your case.

TASKS:
1. Address specific points raised by AGAINST agent
2. Present additional supporting evidence
3. Challenge the credibility of opposing evidence
4. Reinforce your strongest points

Remember: Directly engage with opposition, don't ignore their points."""

ROUND_3_PROMPT = """ROUND 3 - REBUTTAL

Focus on dismantling the opposition's key arguments.

TASKS:
1. Identify weaknesses in AGAINST arguments
2. Present evidence that contradicts their claims
3. Highlight logical flaws in their reasoning
4. Introduce any remaining strong evidence

Remember: This is your chance to expose weaknesses in opposition."""

ROUND_4_PROMPT = """ROUND 4 - CLOSING STATEMENT

Final opportunity to make your case. The judge will render verdict after this.

TASKS:
1. Summarize your strongest arguments
2. Address any remaining counter-points
3. Emphasize quality and credibility of your evidence
4. Make a compelling closing statement
5. State your confidence level in the claim being TRUE

Remember: Leave the judge with your best points fresh in mind."""

# ===========================================
# Exchange Prompts
# ===========================================

def get_for_agent_prompt(
    claim: str,
    round_number: int,
    exchange_number: int,
    previous_exchanges: list = None,
    evidence: list = None
) -> str:
    """
    Generate the full prompt for the FOR agent.
    
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
        evidence_context = "\n\nAVAILABLE EVIDENCE:\n"
        for ev in evidence[:5]:  # Top 5 evidence items
            evidence_context += f"- {ev.get('title', 'Source')}: {ev.get('content_snippet', '')[:200]}\n"
    
    prompt = f"""
{base}

{FOR_AGENT_SYSTEM}

===========================================
CLAIM TO DEFEND:
"{claim}"
===========================================

{round_prompt}

{exchange_context}

{evidence_context}

{get_response_format()}

Now present your argument FOR the claim:
"""
    
    return prompt


def get_quick_for_prompt(claim: str, evidence: list = None) -> str:
    """Get a simplified prompt for quick analysis."""
    evidence_text = ""
    if evidence:
        evidence_text = "\n".join([
            f"- {e.get('title', 'Source')}: {e.get('content_snippet', '')[:150]}"
            for e in evidence[:3]
        ])
    
    return f"""You are a fact-check analyst. Given this claim and evidence, present arguments supporting the claim's truth.

CLAIM: "{claim}"

EVIDENCE:
{evidence_text}

Provide 2-3 key points that support this claim being TRUE, citing the evidence.
Be concise but specific."""
