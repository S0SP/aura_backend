"""
AURA Service - User Management
CRUD operations for users in MongoDB
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId

from app.core.logging import logger
from app.core.security import hash_password, verify_password, generate_api_key
from app.db.mongodb import get_collection, Collections
from app.models.user import (
    UserCreate, UserInDB, UserUpdate, UserResponse,
    UserRole, UserStatus, UserPreferences, UserStats
)
from app.utils.id_generator import generate_user_id


class UserService:
    """Service for managing users in MongoDB."""
    
    def __init__(self):
        self.collection_name = Collections.USERS
    
    @property
    def collection(self):
        return get_collection(self.collection_name)
    
    async def create(self, user_data: UserCreate) -> UserInDB:
        """
        Create a new user.
        
        Args:
            user_data: User creation data
            
        Returns:
            Created user with ID
        """
        user_id = generate_user_id()
        
        # Hash password if provided
        password_hash = None
        if user_data.password:
            password_hash = hash_password(user_data.password)
        
        user = UserInDB(
            user_id=user_id,
            email=user_data.email,
            password_hash=password_hash,
            phone=user_data.phone,
            name=user_data.name,
            role=user_data.role,
            status=UserStatus.ACTIVE,
            preferences=UserPreferences(),
            stats=UserStats(),
            created_at=datetime.utcnow()
        )
        
        doc_dict = user.model_dump(by_alias=True, exclude={"id"})
        result = await self.collection.insert_one(doc_dict)
        
        user.id = str(result.inserted_id)
        
        logger.info(f"Created user: {user_id}")
        return user
    
    async def get_by_id(self, user_id: str) -> Optional[UserInDB]:
        """Get a user by their user_id."""
        doc = await self.collection.find_one({"user_id": user_id})
        if doc:
            doc["_id"] = str(doc["_id"])
            return UserInDB(**doc)
        return None
    
    async def get_by_email(self, email: str) -> Optional[UserInDB]:
        """Get a user by email."""
        doc = await self.collection.find_one({"email": email})
        if doc:
            doc["_id"] = str(doc["_id"])
            return UserInDB(**doc)
        return None
    
    async def get_by_phone(self, phone: str) -> Optional[UserInDB]:
        """Get a user by phone number."""
        doc = await self.collection.find_one({"phone": phone})
        if doc:
            doc["_id"] = str(doc["_id"])
            return UserInDB(**doc)
        return None
    
    async def authenticate(
        self, 
        email: str, 
        password: str
    ) -> Optional[UserInDB]:
        """
        Authenticate a user by email and password.
        
        Args:
            email: User's email
            password: Plain text password
            
        Returns:
            User if authenticated, None otherwise
        """
        user = await self.get_by_email(email)
        
        if not user or not user.password_hash:
            return None
        
        if not verify_password(password, user.password_hash):
            return None
        
        # Update last login
        await self.collection.update_one(
            {"user_id": user.user_id},
            {"$set": {"last_login_at": datetime.utcnow()}}
        )
        
        return user
    
    async def update(
        self, 
        user_id: str, 
        update_data: UserUpdate
    ) -> bool:
        """Update user profile."""
        update_dict = update_data.model_dump(exclude_none=True)
        update_dict["updated_at"] = datetime.utcnow()
        
        result = await self.collection.update_one(
            {"user_id": user_id},
            {"$set": update_dict}
        )
        return result.modified_count > 0
    
    async def update_password(
        self, 
        user_id: str, 
        new_password: str
    ) -> bool:
        """Update user password."""
        password_hash = hash_password(new_password)
        
        result = await self.collection.update_one(
            {"user_id": user_id},
            {"$set": {
                "password_hash": password_hash,
                "updated_at": datetime.utcnow()
            }}
        )
        return result.modified_count > 0
    
    async def generate_api_key(self, user_id: str) -> Optional[str]:
        """
        Generate a new API key for a user.
        
        Returns the plain API key (store this securely - it won't be shown again).
        """
        api_key = generate_api_key()
        api_key_hash = hash_password(api_key)
        
        result = await self.collection.update_one(
            {"user_id": user_id},
            {"$set": {
                "api_key_hash": api_key_hash,
                "api_key_created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }}
        )
        
        if result.modified_count > 0:
            return api_key
        return None
    
    async def verify_api_key(
        self, 
        user_id: str, 
        api_key: str
    ) -> bool:
        """Verify a user's API key."""
        user = await self.get_by_id(user_id)
        
        if not user or not user.api_key_hash:
            return False
        
        return verify_password(api_key, user.api_key_hash)
    
    async def increment_verification_count(self, user_id: str) -> bool:
        """Increment user's verification count."""
        result = await self.collection.update_one(
            {"user_id": user_id},
            {
                "$inc": {
                    "stats.total_verifications": 1,
                    "stats.verifications_this_month": 1
                },
                "$set": {
                    "stats.last_verification_at": datetime.utcnow()
                }
            }
        )
        return result.modified_count > 0
    
    async def check_rate_limit(self, user_id: str) -> Dict[str, Any]:
        """
        Check if user is within rate limits.
        
        Returns:
            Dict with 'allowed', 'remaining', and 'limit' keys
        """
        user = await self.get_by_id(user_id)
        
        if not user:
            return {"allowed": False, "remaining": 0, "limit": 0}
        
        # Check daily limit
        today_count = user.stats.api_calls_today
        limit = user.daily_limit
        
        return {
            "allowed": today_count < limit,
            "remaining": max(0, limit - today_count),
            "limit": limit
        }
    
    async def increment_api_calls(self, user_id: str) -> bool:
        """Increment today's API call count."""
        result = await self.collection.update_one(
            {"user_id": user_id},
            {"$inc": {"stats.api_calls_today": 1}}
        )
        return result.modified_count > 0
    
    async def reset_daily_counts(self) -> int:
        """
        Reset daily API call counts for all users.
        Should be called daily via a scheduled task.
        """
        result = await self.collection.update_many(
            {},
            {"$set": {"stats.api_calls_today": 0}}
        )
        return result.modified_count
    
    async def set_status(
        self, 
        user_id: str, 
        status: UserStatus
    ) -> bool:
        """Update user status."""
        result = await self.collection.update_one(
            {"user_id": user_id},
            {"$set": {
                "status": status.value,
                "updated_at": datetime.utcnow()
            }}
        )
        return result.modified_count > 0
    
    async def delete(self, user_id: str) -> bool:
        """Delete a user (soft delete - sets status to inactive)."""
        return await self.set_status(user_id, UserStatus.INACTIVE)
    
    async def hard_delete(self, user_id: str) -> bool:
        """Permanently delete a user."""
        result = await self.collection.delete_one({"user_id": user_id})
        return result.deleted_count > 0


# Global service instance
user_service = UserService()
