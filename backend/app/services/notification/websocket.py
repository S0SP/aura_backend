"""
AURA WebSocket Manager
Real-time updates for verification progress and debate
"""

from typing import Dict, Any, List, Set
from datetime import datetime
import asyncio
import json

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.core.logging import logger
from app.core.config import settings


class WebSocketManager:
    """
    WebSocket connection manager for real-time updates.
    Handles verification progress and debate updates.
    """
    
    def __init__(self):
        # Active connections: {verification_id: {websocket}}
        self.verification_connections: Dict[str, Set[WebSocket]] = {}
        # Debate connections: {session_id: {websocket}}
        self.debate_connections: Dict[str, Set[WebSocket]] = {}
        # Connection metadata
        self.connection_info: Dict[WebSocket, Dict] = {}
    
    async def connect_verification(
        self,
        websocket: WebSocket,
        verification_id: str
    ):
        """Connect a client to verification updates."""
        await websocket.accept()
        
        if verification_id not in self.verification_connections:
            self.verification_connections[verification_id] = set()
        
        self.verification_connections[verification_id].add(websocket)
        self.connection_info[websocket] = {
            "type": "verification",
            "id": verification_id,
            "connected_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"WS connected: verification {verification_id}")
        
        # Send initial connection message
        await self._send_to_websocket(websocket, {
            "type": "connected",
            "verification_id": verification_id,
            "message": "Connected to verification updates"
        })
    
    async def connect_debate(
        self,
        websocket: WebSocket,
        session_id: str
    ):
        """Connect a client to debate updates."""
        await websocket.accept()
        
        if session_id not in self.debate_connections:
            self.debate_connections[session_id] = set()
        
        self.debate_connections[session_id].add(websocket)
        self.connection_info[websocket] = {
            "type": "debate",
            "id": session_id,
            "connected_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"WS connected: debate {session_id}")
        
        await self._send_to_websocket(websocket, {
            "type": "connected",
            "debate_session_id": session_id,
            "message": "Connected to debate updates"
        })
    
    def disconnect(self, websocket: WebSocket):
        """Disconnect a client."""
        info = self.connection_info.get(websocket)
        
        if info:
            conn_type = info.get("type")
            conn_id = info.get("id")
            
            if conn_type == "verification":
                if conn_id in self.verification_connections:
                    self.verification_connections[conn_id].discard(websocket)
                    if not self.verification_connections[conn_id]:
                        del self.verification_connections[conn_id]
            
            elif conn_type == "debate":
                if conn_id in self.debate_connections:
                    self.debate_connections[conn_id].discard(websocket)
                    if not self.debate_connections[conn_id]:
                        del self.debate_connections[conn_id]
            
            del self.connection_info[websocket]
            logger.info(f"WS disconnected: {conn_type} {conn_id}")
    
    async def send_verification_update(
        self,
        verification_id: str,
        status: str,
        progress: int = None,
        current_step: str = None,
        data: Dict = None
    ):
        """Send update to all clients watching a verification."""
        if verification_id not in self.verification_connections:
            return
        
        message = {
            "type": "verification_update",
            "verification_id": verification_id,
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if progress is not None:
            message["progress_percent"] = progress
        if current_step:
            message["current_step"] = current_step
        if data:
            message["data"] = data
        
        await self._broadcast_to_connections(
            self.verification_connections[verification_id],
            message
        )
    
    async def send_debate_exchange(
        self,
        session_id: str,
        agent: str,
        exchange_number: int,
        round_number: int,
        argument: str
    ):
        """Send debate exchange to all clients watching."""
        if session_id not in self.debate_connections:
            return
        
        message = {
            "type": "debate_exchange",
            "session_id": session_id,
            "agent": agent,
            "round": round_number,
            "exchange": exchange_number,
            "argument_preview": argument[:300] if argument else "",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self._broadcast_to_connections(
            self.debate_connections[session_id],
            message
        )
    
    async def send_debate_round_complete(
        self,
        session_id: str,
        round_number: int,
        round_winner: str,
        scores: Dict
    ):
        """Send round completion update."""
        if session_id not in self.debate_connections:
            return
        
        message = {
            "type": "round_complete",
            "session_id": session_id,
            "round": round_number,
            "winner": round_winner,
            "scores": scores,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self._broadcast_to_connections(
            self.debate_connections[session_id],
            message
        )
    
    async def send_verdict(
        self,
        verification_id: str,
        verdict: str,
        confidence: float,
        summary: str
    ):
        """Send final verdict to all watching clients."""
        connections = set()
        
        if verification_id in self.verification_connections:
            connections.update(self.verification_connections[verification_id])
        
        if not connections:
            return
        
        message = {
            "type": "verdict",
            "verification_id": verification_id,
            "verdict": verdict,
            "confidence": confidence,
            "summary": summary[:500],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self._broadcast_to_connections(connections, message)
    
    async def _broadcast_to_connections(
        self,
        connections: Set[WebSocket],
        message: Dict
    ):
        """Broadcast message to a set of connections."""
        dead_connections = set()
        
        for websocket in connections:
            try:
                await self._send_to_websocket(websocket, message)
            except Exception as e:
                logger.warning(f"Failed to send to websocket: {e}")
                dead_connections.add(websocket)
        
        # Clean up dead connections
        for websocket in dead_connections:
            self.disconnect(websocket)
    
    async def _send_to_websocket(
        self,
        websocket: WebSocket,
        message: Dict
    ):
        """Send message to a single websocket."""
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_json(message)
    
    def get_connection_count(self) -> Dict[str, int]:
        """Get count of active connections."""
        return {
            "verification_connections": sum(
                len(conns) for conns in self.verification_connections.values()
            ),
            "debate_connections": sum(
                len(conns) for conns in self.debate_connections.values()
            ),
            "total": len(self.connection_info)
        }


# Global instance
websocket_manager = WebSocketManager()


# Convenience functions for use throughout the app
async def notify_status_update(
    verification_id: str,
    status: str,
    progress: int = None,
    current_step: str = None
):
    """Notify clients of verification status update."""
    await websocket_manager.send_verification_update(
        verification_id=verification_id,
        status=status,
        progress=progress,
        current_step=current_step
    )


async def notify_debate_exchange(
    session_id: str,
    agent: str,
    exchange: int,
    round_num: int,
    argument: str
):
    """Notify clients of debate exchange."""
    await websocket_manager.send_debate_exchange(
        session_id=session_id,
        agent=agent,
        exchange_number=exchange,
        round_number=round_num,
        argument=argument
    )


async def notify_verdict(
    verification_id: str,
    verdict: str,
    confidence: float,
    summary: str
):
    """Notify clients of final verdict."""
    await websocket_manager.send_verdict(
        verification_id=verification_id,
        verdict=verdict,
        confidence=confidence,
        summary=summary
    )
