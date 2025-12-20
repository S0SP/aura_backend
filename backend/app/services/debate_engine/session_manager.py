"""
AURA Session Manager
Manages debate sessions and verification state
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import asyncio
from uuid import uuid4

from app.core.logging import logger
from app.core.config import settings


class SessionManager:
    """
    Manages debate sessions and verification state.
    Tracks active sessions, handles timeouts, and stores results.
    """
    
    def __init__(self):
        self.sessions: Dict[str, Dict] = {}
        self.verifications: Dict[str, Dict] = {}
        self.timeout_seconds = getattr(settings, 'DEBATE_TIMEOUT_SECONDS', 300)
    
    def create_session(
        self,
        verification_id: str,
        claim: str,
        config: Dict = None
    ) -> Dict[str, Any]:
        """Create a new debate session."""
        session_id = f"dbt_{uuid4().hex[:12]}"
        
        now = datetime.utcnow()
        
        session = {
            "session_id": session_id,
            "verification_id": verification_id,
            "claim": claim,
            "status": "initiated",
            "current_round": 0,
            "total_rounds": config.get("max_rounds", 4) if config else 4,
            "exchanges": [],
            "round_evaluations": [],
            "config": config or {},
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=self.timeout_seconds)).isoformat()
        }
        
        self.sessions[session_id] = session
        
        # Link verification to session
        self.verifications[verification_id] = {
            "verification_id": verification_id,
            "session_id": session_id,
            "claim": claim,
            "status": "initiated",
            "created_at": now.isoformat()
        }
        
        logger.info(f"Created session {session_id} for verification {verification_id}")
        
        return session
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session by ID."""
        return self.sessions.get(session_id)
    
    def get_session_by_verification(self, verification_id: str) -> Optional[Dict]:
        """Get session by verification ID."""
        ver = self.verifications.get(verification_id)
        if ver:
            return self.sessions.get(ver.get("session_id"))
        return None
    
    def update_session(
        self,
        session_id: str,
        status: str = None,
        current_round: int = None,
        exchange: Dict = None,
        round_evaluation: Dict = None
    ) -> Optional[Dict]:
        """Update session state."""
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        if status:
            session["status"] = status
        
        if current_round is not None:
            session["current_round"] = current_round
        
        if exchange:
            session["exchanges"].append(exchange)
        
        if round_evaluation:
            session["round_evaluations"].append(round_evaluation)
        
        session["updated_at"] = datetime.utcnow().isoformat()
        
        # Update linked verification
        ver_id = session.get("verification_id")
        if ver_id in self.verifications:
            self.verifications[ver_id]["status"] = session["status"]
        
        return session
    
    def complete_session(
        self,
        session_id: str,
        final_verdict: Dict
    ) -> Optional[Dict]:
        """Mark session as completed with final verdict."""
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        session["status"] = "completed"
        session["final_verdict"] = final_verdict
        session["completed_at"] = datetime.utcnow().isoformat()
        
        ver_id = session.get("verification_id")
        if ver_id in self.verifications:
            self.verifications[ver_id]["status"] = "completed"
            self.verifications[ver_id]["verdict"] = final_verdict.get("verdict")
            self.verifications[ver_id]["completed_at"] = session["completed_at"]
        
        logger.info(f"Session {session_id} completed with verdict: {final_verdict.get('verdict')}")
        
        return session
    
    def fail_session(
        self,
        session_id: str,
        error: str
    ) -> Optional[Dict]:
        """Mark session as failed."""
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        session["status"] = "failed"
        session["error"] = error
        session["failed_at"] = datetime.utcnow().isoformat()
        
        ver_id = session.get("verification_id")
        if ver_id in self.verifications:
            self.verifications[ver_id]["status"] = "failed"
            self.verifications[ver_id]["error"] = error
        
        logger.error(f"Session {session_id} failed: {error}")
        
        return session
    
    def get_verification_status(self, verification_id: str) -> Optional[Dict]:
        """Get verification status."""
        ver = self.verifications.get(verification_id)
        if not ver:
            return None
        
        session = self.sessions.get(ver.get("session_id"))
        if session:
            return {
                "verification_id": verification_id,
                "session_id": session.get("session_id"),
                "status": session.get("status"),
                "current_round": session.get("current_round"),
                "total_rounds": session.get("total_rounds"),
                "exchanges_count": len(session.get("exchanges", [])),
                "created_at": ver.get("created_at"),
                "updated_at": session.get("updated_at")
            }
        
        return ver
    
    def cleanup_expired_sessions(self):
        """Remove expired sessions."""
        now = datetime.utcnow()
        expired = []
        
        for session_id, session in self.sessions.items():
            expires_at = session.get("expires_at")
            if expires_at:
                exp_time = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if now > exp_time and session.get("status") not in ["completed", "failed"]:
                    expired.append(session_id)
        
        for session_id in expired:
            self.fail_session(session_id, "Session timeout")
            logger.warning(f"Session {session_id} expired and cleaned up")
        
        return len(expired)
    
    def get_active_sessions_count(self) -> int:
        """Get count of active sessions."""
        return sum(
            1 for s in self.sessions.values()
            if s.get("status") not in ["completed", "failed"]
        )


# Global instance
session_manager = SessionManager()
