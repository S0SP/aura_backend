"""
AURA Service - Verification Management
CRUD operations for verifications in MongoDB
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId

from app.core.logging import logger
from app.db.mongodb import get_collection, Collections
from app.db.redis_db import set_verification_status, get_verification_status
from app.models.verification import (
    VerificationCreate, VerificationInDB, VerificationUpdate,
    VerificationStatus, QuickClassificationResult, FinalVerdict
)
from app.utils.id_generator import generate_verification_id


class VerificationService:
    """Service for managing verifications in MongoDB."""
    
    def __init__(self):
        self.collection_name = Collections.VERIFICATIONS
    
    @property
    def collection(self):
        return get_collection(self.collection_name)
    
    async def create(self, data: VerificationCreate) -> VerificationInDB:
        """
        Create a new verification.
        
        Args:
            data: Verification creation data
            
        Returns:
            Created verification with ID
        """
        verification_id = generate_verification_id()
        
        verification = VerificationInDB(
            verification_id=verification_id,
            claim_id=data.claim_id,
            claim=data.claim,
            language=data.language,
            user_id=data.user_id,
            status=VerificationStatus.QUEUED,
            created_at=datetime.utcnow()
        )
        
        doc_dict = verification.model_dump(by_alias=True, exclude={"id"})
        result = await self.collection.insert_one(doc_dict)
        
        verification.id = str(result.inserted_id)
        
        # Cache initial status in Redis
        await set_verification_status(verification_id, {
            "status": "queued",
            "progress_percent": 0,
            "current_step": None
        })
        
        logger.info(f"Created verification: {verification_id}")
        return verification
    
    async def get_by_id(self, verification_id: str) -> Optional[VerificationInDB]:
        """Get a verification by its ID."""
        doc = await self.collection.find_one({"verification_id": verification_id})
        if doc:
            doc["_id"] = str(doc["_id"])
            return VerificationInDB(**doc)
        return None
    
    async def update_status(
        self,
        verification_id: str,
        status: VerificationStatus,
        current_step: Optional[str] = None,
        progress_percent: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """Update verification status."""
        update_data = {
            "status": status.value,
            "updated_at": datetime.utcnow()
        }
        
        if current_step is not None:
            update_data["current_step"] = current_step
        if progress_percent is not None:
            update_data["progress_percent"] = progress_percent
        if error_message is not None:
            update_data["error_message"] = error_message
        
        if status == VerificationStatus.COMPLETED:
            update_data["completed_at"] = datetime.utcnow()
        
        result = await self.collection.update_one(
            {"verification_id": verification_id},
            {"$set": update_data}
        )
        
        # Update Redis cache
        await set_verification_status(verification_id, {
            "status": status.value,
            "progress_percent": progress_percent or 0,
            "current_step": current_step
        })
        
        return result.modified_count > 0
    
    async def set_quick_classification(
        self,
        verification_id: str,
        classification: QuickClassificationResult
    ) -> bool:
        """Set quick classification result."""
        result = await self.collection.update_one(
            {"verification_id": verification_id},
            {"$set": {
                "quick_classification": classification.model_dump(),
                "updated_at": datetime.utcnow()
            }}
        )
        return result.modified_count > 0
    
    async def set_debate_summary(
        self,
        verification_id: str,
        debate_summary: Dict[str, Any]
    ) -> bool:
        """Set debate summary."""
        result = await self.collection.update_one(
            {"verification_id": verification_id},
            {"$set": {
                "debate_summary": debate_summary,
                "updated_at": datetime.utcnow()
            }}
        )
        return result.modified_count > 0
    
    async def set_final_verdict(
        self,
        verification_id: str,
        verdict: FinalVerdict,
        processing_time: float
    ) -> bool:
        """Set final verdict and complete the verification."""
        result = await self.collection.update_one(
            {"verification_id": verification_id},
            {"$set": {
                "final_verdict": verdict.model_dump(),
                "status": VerificationStatus.COMPLETED.value,
                "processing_time_seconds": processing_time,
                "completed_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }}
        )
        return result.modified_count > 0
    
    async def add_evidence(
        self,
        verification_id: str,
        evidence_items: List[Dict[str, Any]]
    ) -> bool:
        """Add evidence items to verification."""
        result = await self.collection.update_one(
            {"verification_id": verification_id},
            {
                "$push": {"evidence_items": {"$each": evidence_items}},
                "$inc": {"total_evidence_count": len(evidence_items)},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        return result.modified_count > 0
    
    async def get_recent(
        self,
        limit: int = 20,
        status: Optional[VerificationStatus] = None
    ) -> List[VerificationInDB]:
        """Get recent verifications."""
        query = {}
        if status:
            query["status"] = status.value
        
        cursor = self.collection.find(query).sort("created_at", -1).limit(limit)
        
        verifications = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            verifications.append(VerificationInDB(**doc))
        return verifications
    
    async def get_by_user(
        self,
        user_id: str,
        limit: int = 50,
        skip: int = 0
    ) -> List[VerificationInDB]:
        """Get verifications by user ID."""
        cursor = self.collection.find(
            {"user_id": user_id}
        ).sort("created_at", -1).skip(skip).limit(limit)
        
        verifications = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            verifications.append(VerificationInDB(**doc))
        return verifications
    
    async def get_status_from_cache(
        self,
        verification_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get real-time status from Redis cache."""
        return await get_verification_status(verification_id)
    
    async def count_by_verdict(self, days: int = 30) -> Dict[str, int]:
        """Count verifications by verdict in last N days."""
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        pipeline = [
            {"$match": {
                "status": "completed",
                "created_at": {"$gte": cutoff}
            }},
            {"$group": {
                "_id": "$final_verdict.verdict",
                "count": {"$sum": 1}
            }}
        ]
        
        result = {}
        async for doc in self.collection.aggregate(pipeline):
            result[doc["_id"]] = doc["count"]
        
        return result


# Global service instance
verification_service = VerificationService()
