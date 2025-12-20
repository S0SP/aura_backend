"""
AURA Database Module
Database connections and utilities
"""

from app.db.mongodb import (
    connect_mongodb,
    close_mongodb,
    get_database,
    get_collection,
    Collections
)
from app.db.redis_db import (
    connect_redis,
    close_redis,
    get_redis,
    cache_set,
    cache_get,
    cache_delete
)
from app.db.pinecone_db import (
    connect_pinecone,
    close_pinecone,
    search_vectors,
    upsert_vectors,
    generate_embedding,
    chunk_text
)
from app.db.neo4j_db import (
    connect_neo4j,
    close_neo4j,
    create_node,
    create_relationship,
    find_related_entities
)

__all__ = [
    # MongoDB
    "connect_mongodb",
    "close_mongodb",
    "get_database",
    "get_collection",
    "Collections",
    # Redis
    "connect_redis",
    "close_redis",
    "get_redis",
    "cache_set",
    "cache_get",
    "cache_delete",
    # Pinecone
    "connect_pinecone",
    "close_pinecone",
    "search_vectors",
    "upsert_vectors",
    "generate_embedding",
    "chunk_text",
    # Neo4j
    "connect_neo4j",
    "close_neo4j",
    "create_node",
    "create_relationship",
    "find_related_entities"
]
