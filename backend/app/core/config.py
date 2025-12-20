"""
AURA Configuration Settings
Using Pydantic Settings for type-safe configuration
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # === App Settings ===
    APP_NAME: str = "AURA Fact-Checker"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    API_V1_PREFIX: str = "/api/v1"
    
    # === CORS ===
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"]
    )
    
    # === Security ===
    SECRET_KEY: str = Field(default="your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # === MongoDB ===
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "aura_factchecker"
    
    # === Redis ===
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_DB: int = 0
    
    # === Neo4j ===
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    
    # === Pinecone ===
    PINECONE_API_KEY: str = ""
    PINECONE_ENVIRONMENT: str = "gcp-starter"
    PINECONE_INDEX_NAME: str = "aura-facts"
    
    # === Embeddings (Best Free Options) ===
    # Using sentence-transformers for local embeddings
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"  # Fast & good
    EMBEDDING_MODEL_DIMENSION: int = 384
    # Alternative: "BAAI/bge-small-en-v1.5" (dim: 384, better quality)
    # Alternative: "sentence-transformers/all-mpnet-base-v2" (dim: 768, best quality)
    
    # === Chunking Settings (Optimized for RAG) ===
    CHUNK_SIZE: int = 512  # Optimal for semantic search
    CHUNK_OVERLAP: int = 50  # 10% overlap
    CHUNK_STRATEGY: str = "recursive"  # recursive, semantic, or fixed
    
    # === LLM Providers (Free Tiers) ===
    # Google Gemini (Primary - Free)
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    
    # Groq (Backup - Free, Very Fast)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-70b-versatile"
    
    # === Search & Scraping ===
    SERP_API_KEY: str = ""
    FIRECRAWL_API_KEY: str = ""
    
    # === HuggingFace (XLM-RoBERTa Model) ===
    HUGGINGFACE_API_KEY: str = ""
    XLM_ROBERTA_ENDPOINT: str = ""  # Your deployed model endpoint
    
    # === ElevenLabs (TTS) ===
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_VOICE_ID: str = "21m00Tcm4TlvDq8ikWAM"  # Rachel - Default voice
    
    # === Facebook/WhatsApp Business API ===
    FB_APP_ID: str = ""
    FB_APP_SECRET: str = ""
    FB_ACCESS_TOKEN: str = ""
    FB_PHONE_NUMBER_ID: str = ""
    FB_BUSINESS_ACCOUNT_ID: str = ""
    FB_WEBHOOK_VERIFY_TOKEN: str = "aura_webhook_verify_token"
    FB_API_VERSION: str = "v18.0"
    
    # === Queue Settings ===
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # === Debate Engine Settings ===
    MAX_DEBATE_ROUNDS: int = 4
    EXCHANGES_PER_ROUND: int = 4
    DEBATE_TIMEOUT_SECONDS: int = 300
    
    # === WebSocket Settings ===
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_MAX_CONNECTIONS: int = 1000
    
    # === Logging ===
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or text
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
