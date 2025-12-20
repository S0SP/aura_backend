"""
AURA Service - Claim Management
CRUD operations for claims in MongoDB
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId

from app.core.logging import logger
from app.db.mongodb import get_collection, Collections
from app.models.claim import ClaimCreate, ClaimInDB, ClaimStatus
from app.utils.id_generator import generate_claim_id


class ClaimService:
    """Service for managing claims in MongoDB."""
    
    def __init__(self):
        self.collection_name = Collections.CLAIMS
    
    @property
    def collection(self):
        return get_collection(self.collection_name)
    
    async def create(self, claim_data: ClaimCreate) -> ClaimInDB:
        """
        Create a new claim.
        
        Args:
            claim_data: Claim creation data
            
        Returns:
            Created claim with ID
        """
        claim_id = generate_claim_id()
        
        claim_doc = ClaimInDB(
            claim_id=claim_id,
            claim_text=claim_data.claim_text,
            language=claim_data.language,
            source_context=claim_data.source_context,
            priority=claim_data.priority,
            source=claim_data.source,
            metadata=claim_data.metadata,
            user_id=claim_data.user_id,
            whatsapp_from=claim_data.whatsapp_from,
            status=ClaimStatus.PENDING,
            created_at=datetime.utcnow()
        )
        
        doc_dict = claim_doc.model_dump(by_alias=True, exclude={"id"})
        result = await self.collection.insert_one(doc_dict)
        
        claim_doc.id = str(result.inserted_id)
        
        logger.info(f"Created claim: {claim_id}")
        return claim_doc
    
    async def get_by_id(self, claim_id: str) -> Optional[ClaimInDB]:
        """Get a claim by its claim_id."""
        doc = await self.collection.find_one({"claim_id": claim_id})
        if doc:
            doc["_id"] = str(doc["_id"])
            return ClaimInDB(**doc)
        return None
    
    async def get_by_mongo_id(self, mongo_id: str) -> Optional[ClaimInDB]:
        """Get a claim by MongoDB ObjectId."""
        doc = await self.collection.find_one({"_id": ObjectId(mongo_id)})
        if doc:
            doc["_id"] = str(doc["_id"])
            return ClaimInDB(**doc)
        return None
    
    async def update_status(
        self, 
        claim_id: str, 
        status: ClaimStatus,
        verification_id: Optional[str] = None
    ) -> bool:
        """Update claim status."""
        update_data = {
            "status": status.value,
            "updated_at": datetime.utcnow()
        }
        if verification_id:
            update_data["verification_id"] = verification_id
        
        result = await self.collection.update_one(
            {"claim_id": claim_id},
            {"$set": update_data}
        )
        return result.modified_count > 0
    
    async def set_classification(
        self, 
        claim_id: str, 
        classification: Dict[str, Any]
    ) -> bool:
        """Set quick classification result."""
        result = await self.collection.update_one(
            {"claim_id": claim_id},
            {"$set": {
                "quick_classification": classification,
                "updated_at": datetime.utcnow()
            }}
        )
        return result.modified_count > 0
    
    async def get_pending(self, limit: int = 100) -> List[ClaimInDB]:
        """Get pending claims for processing."""
        cursor = self.collection.find(
            {"status": ClaimStatus.PENDING.value}
        ).sort("created_at", 1).limit(limit)
        
        claims = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            claims.append(ClaimInDB(**doc))
        return claims
    
    async def get_by_user(
        self, 
        user_id: str, 
        limit: int = 50, 
        skip: int = 0
    ) -> List[ClaimInDB]:
        """Get claims by user ID."""
        cursor = self.collection.find(
            {"user_id": user_id}
        ).sort("created_at", -1).skip(skip).limit(limit)
        
        claims = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            claims.append(ClaimInDB(**doc))
        return claims
    
    async def search(
        self, 
        query: str, 
        limit: int = 20
    ) -> List[ClaimInDB]:
        """Search claims by text (basic text search)."""
        cursor = self.collection.find(
            {"$text": {"$search": query}}
        ).limit(limit)
        
        claims = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            claims.append(ClaimInDB(**doc))
        return claims
    
    async def count_by_status(self, status: ClaimStatus) -> int:
        """Count claims by status."""
        return await self.collection.count_documents({"status": status.value})
    
    async def delete(self, claim_id: str) -> bool:
        """Delete a claim."""
        result = await self.collection.delete_one({"claim_id": claim_id})
        return result.deleted_count > 0


# Global service instance
claim_service = ClaimService()
