"""
AURA MongoDB Database Connection
Async MongoDB client using Motor
"""

from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from app.core.config import settings
from app.core.logging import logger

# Global database client and database instances
mongodb_client: Optional[AsyncIOMotorClient] = None
mongodb_db: Optional[AsyncIOMotorDatabase] = None


async def connect_mongodb() -> None:
    """
    Connect to MongoDB.
    Creates a global client and database instance.
    """
    global mongodb_client, mongodb_db
    
    try:
        logger.info(f"Connecting to MongoDB at {settings.MONGODB_URL}...")
        
        mongodb_client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=5000,
            maxPoolSize=50,
            minPoolSize=10
        )
        
        # Verify connection
        await mongodb_client.admin.command('ping')
        
        # Get database
        mongodb_db = mongodb_client[settings.MONGODB_DB_NAME]
        
        logger.info(f"✅ Connected to MongoDB database: {settings.MONGODB_DB_NAME}")
        
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        logger.error(f"❌ Failed to connect to MongoDB: {e}")
        mongodb_client = None
        mongodb_db = None
        raise


async def close_mongodb() -> None:
    """Close MongoDB connection."""
    global mongodb_client, mongodb_db
    
    if mongodb_client:
        mongodb_client.close()
        mongodb_client = None
        mongodb_db = None
        logger.info("MongoDB connection closed")


def get_database() -> AsyncIOMotorDatabase:
    """
    Get the MongoDB database instance.
    
    Returns:
        AsyncIOMotorDatabase instance
        
    Raises:
        RuntimeError if database is not connected
    """
    if mongodb_db is None:
        raise RuntimeError("MongoDB is not connected. Call connect_mongodb() first.")
    return mongodb_db


def get_collection(collection_name: str):
    """
    Get a MongoDB collection.
    
    Args:
        collection_name: Name of the collection
        
    Returns:
        AsyncIOMotorCollection instance
    """
    db = get_database()
    return db[collection_name]


# Collection name constants
class Collections:
    """MongoDB collection names."""
    CLAIMS = "claims"
    VERIFICATIONS = "verifications"
    DEBATE_SESSIONS = "debate_sessions"
    EVIDENCE = "evidence"
    USERS = "users"
    AUDIT_LOGS = "audit_logs"
    FACTS = "facts"
    TRENDS = "trends"


async def init_collections() -> None:
    """
    Initialize MongoDB collections with indexes.
    Called during application startup.
    """
    db = get_database()
    
    # Claims collection indexes
    await db[Collections.CLAIMS].create_index("created_at")
    await db[Collections.CLAIMS].create_index("status")
    await db[Collections.CLAIMS].create_index("user_id")
    
    # Verifications collection indexes
    await db[Collections.VERIFICATIONS].create_index("verification_id", unique=True)
    await db[Collections.VERIFICATIONS].create_index("status")
    await db[Collections.VERIFICATIONS].create_index("created_at")
    
    # Debate sessions indexes
    await db[Collections.DEBATE_SESSIONS].create_index("session_id", unique=True)
    await db[Collections.DEBATE_SESSIONS].create_index("verification_id")
    
    # Users indexes
    await db[Collections.USERS].create_index("email", unique=True, sparse=True)
    await db[Collections.USERS].create_index("phone", sparse=True)
    
    logger.info("✅ MongoDB collections and indexes initialized")


# Helper functions for common operations
async def insert_document(collection_name: str, document: dict) -> str:
    """Insert a document and return its ID."""
    collection = get_collection(collection_name)
    result = await collection.insert_one(document)
    return str(result.inserted_id)


async def find_document(collection_name: str, query: dict) -> Optional[dict]:
    """Find a single document."""
    collection = get_collection(collection_name)
    return await collection.find_one(query)


async def update_document(collection_name: str, query: dict, update: dict) -> bool:
    """Update a document. Returns True if updated."""
    collection = get_collection(collection_name)
    result = await collection.update_one(query, {"$set": update})
    return result.modified_count > 0


async def delete_document(collection_name: str, query: dict) -> bool:
    """Delete a document. Returns True if deleted."""
    collection = get_collection(collection_name)
    result = await collection.delete_one(query)
    return result.deleted_count > 0
