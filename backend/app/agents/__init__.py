"""
AURA Agents Package
Export all CrewAI agents and tools
"""

from app.agents.for_agent import create_for_agent, ForAgent
from app.agents.against_agent import create_against_agent, AgainstAgent
from app.agents.neutral_agent import create_neutral_agent, NeutralAgent
from app.agents.judge_agent import create_judge_agent, JudgeAgent
from app.agents.crew import create_fact_check_crew, FactCheckCrew

from app.agents.tools.knowledge_tools import (
    get_all_agent_tools,
    create_evidence_search_tool,
    create_fact_lookup_tool,
    create_credibility_tool,
    create_graph_query_tool
)

__all__ = [
    # Agents
    "create_for_agent", "ForAgent",
    "create_against_agent", "AgainstAgent",
    "create_neutral_agent", "NeutralAgent",
    "create_judge_agent", "JudgeAgent",
    # Crew
    "create_fact_check_crew", "FactCheckCrew",
    # Tools
    "get_all_agent_tools",
    "create_evidence_search_tool",
    "create_fact_lookup_tool",
    "create_credibility_tool",
    "create_graph_query_tool"
]
