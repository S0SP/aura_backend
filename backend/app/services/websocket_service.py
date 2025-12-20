"""
AURA Service - WebSocket Notifications
Real-time notifications via WebSocket and Redis Pub/Sub
"""

from typing import Dict, Set, Any, Optional
from datetime import datetime
import json
import asyncio

from fastapi import WebSocket, WebSocketDisconnect
from app.core.logging import logger
from app.core.config import settings
from app.db.redis_db import publish, subscribe, get_redis


class ConnectionManager:
    """Manages WebSocket connections for verification updates."""
    
    def __init__(self):
        # verification_id -> set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # WebSocket -> verification_id mapping for cleanup
        self.connection_map: Dict[WebSocket, str] = {}
    
    async def connect(
        self, 
        websocket: WebSocket, 
        verification_id: str
    ) -> None:
        """
        Accept a WebSocket connection and subscribe to updates.
        
        Args:
            websocket: The WebSocket connection
            verification_id: Verification ID to subscribe to
        """
        await websocket.accept()
        
        # Add to active connections
        if verification_id not in self.active_connections:
            self.active_connections[verification_id] = set()
        
        self.active_connections[verification_id].add(websocket)
        self.connection_map[websocket] = verification_id
        
        logger.info(f"WebSocket connected for {verification_id}")
        
        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "verification_id": verification_id,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def disconnect(self, websocket: WebSocket) -> None:
        """
        Remove a WebSocket connection.
        
        Args:
            websocket: The WebSocket connection to remove
        """
        verification_id = self.connection_map.pop(websocket, None)
        
        if verification_id and verification_id in self.active_connections:
            self.active_connections[verification_id].discard(websocket)
            
            # Clean up empty sets
            if not self.active_connections[verification_id]:
                del self.active_connections[verification_id]
        
        logger.info(f"WebSocket disconnected for {verification_id}")
    
    async def send_to_verification(
        self, 
        verification_id: str, 
        message: Dict[str, Any]
    ) -> int:
        """
        Send a message to all connections for a verification.
        
        Args:
            verification_id: Target verification ID
            message: Message to send
            
        Returns:
            Number of connections message was sent to
        """
        connections = self.active_connections.get(verification_id, set())
        
        if not connections:
            return 0
        
        sent_count = 0
        dead_connections = []
        
        for websocket in connections:
            try:
                await websocket.send_json(message)
                sent_count += 1
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket: {e}")
                dead_connections.append(websocket)
        
        # Clean up dead connections
        for ws in dead_connections:
            self.disconnect(ws)
        
        return sent_count
    
    async def broadcast_status_update(
        self,
        verification_id: str,
        status: str,
        progress_percent: int = 0,
        current_step: str = None,
        data: Dict[str, Any] = None
    ) -> int:
        """
        Broadcast a status update to all subscribers.
        
        Args:
            verification_id: Verification ID
            status: Current status
            progress_percent: Progress percentage
            current_step: Current processing step
            data: Additional data
            
        Returns:
            Number of connections notified
        """
        message = {
            "type": "status_update",
            "verification_id": verification_id,
            "status": status,
            "progress_percent": progress_percent,
            "current_step": current_step,
            "data": data or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send to WebSocket connections
        ws_count = await self.send_to_verification(verification_id, message)
        
        # Also publish to Redis for other instances
        await publish(f"verification:{verification_id}", message)
        
        return ws_count
    
    async def broadcast_debate_update(
        self,
        session_id: str,
        verification_id: str,
        round_number: int,
        exchange: Dict[str, Any]
    ) -> int:
        """
        Broadcast a debate exchange update.
        
        Args:
            session_id: Debate session ID
            verification_id: Verification ID
            round_number: Current round number
            exchange: Exchange details
            
        Returns:
            Number of connections notified
        """
        message = {
            "type": "debate_exchange",
            "verification_id": verification_id,
            "session_id": session_id,
            "round_number": round_number,
            "exchange": exchange,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return await self.send_to_verification(verification_id, message)
    
    async def broadcast_verdict(
        self,
        verification_id: str,
        verdict: Dict[str, Any]
    ) -> int:
        """
        Broadcast the final verdict.
        
        Args:
            verification_id: Verification ID
            verdict: Final verdict data
            
        Returns:
            Number of connections notified
        """
        message = {
            "type": "verdict",
            "verification_id": verification_id,
            "verdict": verdict,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return await self.send_to_verification(verification_id, message)


# Global connection manager
connection_manager = ConnectionManager()


async def handle_websocket(
    websocket: WebSocket,
    verification_id: str
) -> None:
    """
    Handle a WebSocket connection for verification updates.
    
    Args:
        websocket: The WebSocket connection
        verification_id: Verification ID to subscribe to
    """
    await connection_manager.connect(websocket, verification_id)
    
    try:
        while True:
            # Keep connection alive and handle any client messages
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=settings.WS_HEARTBEAT_INTERVAL
                )
                
                # Handle ping/pong for keep-alive
                if data == "ping":
                    await websocket.send_text("pong")
                    
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        connection_manager.disconnect(websocket)


async def start_redis_listener(verification_id: str) -> None:
    """
    Start listening to Redis pub/sub for a verification.
    Useful for multi-instance deployments.
    
    Args:
        verification_id: Verification ID to listen for
    """
    try:
        pubsub = await subscribe(f"verification:{verification_id}")
        
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                await connection_manager.send_to_verification(
                    verification_id, data
                )
                
    except Exception as e:
        logger.error(f"Redis listener error: {e}")


# ===========================================
# Notification Functions
# ===========================================

async def notify_status_update(
    verification_id: str,
    status: str,
    progress_percent: int = 0,
    current_step: str = None
) -> None:
    """
    Notify all subscribers of a status update.
    
    Args:
        verification_id: Verification ID
        status: New status
        progress_percent: Progress percentage
        current_step: Current processing step
    """
    await connection_manager.broadcast_status_update(
        verification_id=verification_id,
        status=status,
        progress_percent=progress_percent,
        current_step=current_step
    )


async def notify_debate_exchange(
    verification_id: str,
    session_id: str,
    round_number: int,
    agent: str,
    argument: str
) -> None:
    """
    Notify subscribers of a debate exchange.
    
    Args:
        verification_id: Verification ID
        session_id: Debate session ID
        round_number: Round number
        agent: Agent name
        argument: Agent's argument
    """
    exchange = {
        "agent": agent,
        "argument": argument,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    await connection_manager.broadcast_debate_update(
        session_id=session_id,
        verification_id=verification_id,
        round_number=round_number,
        exchange=exchange
    )


async def notify_verdict(
    verification_id: str,
    verdict: str,
    confidence: float,
    reasoning: str
) -> None:
    """
    Notify subscribers of the final verdict.
    
    Args:
        verification_id: Verification ID
        verdict: Final verdict
        confidence: Confidence score
        reasoning: Reasoning summary
    """
    verdict_data = {
        "verdict": verdict,
        "confidence": confidence,
        "reasoning": reasoning
    }
    
    await connection_manager.broadcast_verdict(verification_id, verdict_data)
