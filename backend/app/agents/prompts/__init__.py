"""
AURA Agent Prompts Package
Exports all agent prompts
"""

from app.agents.prompts.base_prompts import (
    get_base_prompt,
    get_scoring_criteria,
    get_response_format,
    SYSTEM_CONTEXT,
    EVIDENCE_GUIDELINES,
    INDIAN_CONTEXT,
    VERDICT_DEFINITIONS,
    SCORING_CRITERIA
)
from app.agents.prompts.for_agent_prompts import (
    get_for_agent_prompt,
    get_quick_for_prompt,
    FOR_AGENT_SYSTEM
)
from app.agents.prompts.against_agent_prompts import (
    get_against_agent_prompt,
    get_quick_against_prompt,
    AGAINST_AGENT_SYSTEM
)
from app.agents.prompts.neutral_agent_prompts import (
    get_neutral_agent_prompt,
    NEUTRAL_AGENT_SYSTEM
)
from app.agents.prompts.judge_agent_prompts import (
    get_round_scoring_prompt,
    get_final_verdict_prompt,
    get_quick_verdict_prompt,
    JUDGE_AGENT_SYSTEM
)

__all__ = [
    # Base
    "get_base_prompt", "get_scoring_criteria", "get_response_format",
    "SYSTEM_CONTEXT", "EVIDENCE_GUIDELINES", "INDIAN_CONTEXT",
    "VERDICT_DEFINITIONS", "SCORING_CRITERIA",
    # FOR Agent
    "get_for_agent_prompt", "get_quick_for_prompt", "FOR_AGENT_SYSTEM",
    # AGAINST Agent
    "get_against_agent_prompt", "get_quick_against_prompt", "AGAINST_AGENT_SYSTEM",
    # NEUTRAL Agent
    "get_neutral_agent_prompt", "NEUTRAL_AGENT_SYSTEM",
    # JUDGE Agent
    "get_round_scoring_prompt", "get_final_verdict_prompt",
    "get_quick_verdict_prompt", "JUDGE_AGENT_SYSTEM"
]
