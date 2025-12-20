"""
AURA Services Package
Core services for the fact-checking pipeline
"""

from app.services.claim_service import claim_service, ClaimService
from app.services.verification_service import verification_service, VerificationService
from app.services.user_service import user_service, UserService
from app.services.llm_service import (
    get_gemini_llm, get_groq_llm, get_llm,
    analyze_claim, synthesize_evidence, generate_verdict
)
from app.services.evidence_service import evidence_service, EvidenceRetrievalService
from app.services.classification_service import classification_service, ClassificationService
from app.services.knowledge_graph_service import knowledge_graph_service, KnowledgeGraphService
from app.services.fact_ingestion_service import fact_ingestion_service, FactIngestionService
from app.services.websocket_service import (
    connection_manager, handle_websocket,
    notify_status_update, notify_debate_exchange, notify_verdict
)
from app.services.debate_service import debate_service, DebateService
from app.services.output import (
    response_generator, ResponseGenerator,
    audio_service, AudioService,
    share_service, ShareService
)

__all__ = [
    # Claim Service
    "claim_service", "ClaimService",
    # Verification Service
    "verification_service", "VerificationService",
    # User Service
    "user_service", "UserService",
    # LLM Service
    "get_gemini_llm", "get_groq_llm", "get_llm",
    "analyze_claim", "synthesize_evidence", "generate_verdict",
    # Evidence Service
    "evidence_service", "EvidenceRetrievalService",
    # Classification Service
    "classification_service", "ClassificationService",
    # Knowledge Graph Service
    "knowledge_graph_service", "KnowledgeGraphService",
    # Fact Ingestion Service
    "fact_ingestion_service", "FactIngestionService",
    # WebSocket Service
    "connection_manager", "handle_websocket",
    "notify_status_update", "notify_debate_exchange", "notify_verdict",
    # Debate Service
    "debate_service", "DebateService",
    # Output Services
    "response_generator", "ResponseGenerator",
    "audio_service", "AudioService",
    "share_service", "ShareService"
]

