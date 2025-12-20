"""
AURA Fact-Checker API
Main FastAPI Application Entry Point
Production-ready with lifespan management
"""

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time

from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.api.v1.router import api_router
from app.db.mongodb import connect_mongodb, close_mongodb
from app.db.redis_db import connect_redis, close_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler for startup/shutdown events.
    Manages database connections and service initialization.
    """
    # ==================== STARTUP ====================
    setup_logging()
    logger.info("🚀 Starting AURA Fact-Checker API...")
    logger.info(f"📋 Version: {settings.VERSION}")
    logger.info(f"🔧 Debug Mode: {settings.DEBUG}")
    
    # Connect to databases
    try:
        await connect_mongodb()
        logger.info("✅ MongoDB connected")
    except Exception as e:
        logger.warning(f"⚠️ MongoDB connection failed: {e}")
    
    try:
        await connect_redis()
        logger.info("✅ Redis connected")
    except Exception as e:
        logger.warning(f"⚠️ Redis connection failed: {e}")
    
    logger.info("✅ AURA Fact-Checker API started successfully")
    
    yield
    
    # ==================== SHUTDOWN ====================
    logger.info("🔄 Shutting down AURA Fact-Checker API...")
    
    await close_mongodb()
    await close_redis()
    
    logger.info("👋 AURA Fact-Checker API shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="""
## AURA Fact-Checker API

AI-Powered Fact-Checking System with Multi-Agent Debate Engine.

### Features:
- **Multi-source Evidence Retrieval**: SERP, Pinecone Vector DB, Neo4j Knowledge Graph
- **Multi-Agent Debate**: FOR, AGAINST, NEUTRAL, and JUDGE agents
- **Real-time Updates**: WebSocket support for live verification status
- **Multi-modal Input**: Text, URL, WhatsApp messages, Images

### API Modules:
- `/input` - Submit claims for verification
- `/evidence` - Search and retrieve evidence
- `/debate` - Manage debate sessions
- `/output` - Get verification results
- `/trends` - Trend analysis
- `/webhooks` - WhatsApp Business API webhooks
    """,
    version=settings.VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan
)


# ==================== MIDDLEWARE ====================

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip Compression for responses > 1KB
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add X-Process-Time header to all responses."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(round(process_time * 1000, 2)) + "ms"
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions globally."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
            "detail": str(exc) if settings.DEBUG else None
        }
    )


# ==================== ROUTES ====================

# Include API v1 routes
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for load balancers and monitoring.
    
    Returns:
        Health status of the application and its dependencies.
    """
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "debug": settings.DEBUG
    }


@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "message": "Welcome to AURA Fact-Checker API",
        "version": settings.VERSION,
        "docs": "/docs" if settings.DEBUG else "Disabled in production",
        "health": "/health",
        "api_base": settings.API_V1_PREFIX
    }


@app.get("/ready", tags=["Health"])
async def readiness_check():
    """
    Readiness check for Kubernetes/container orchestration.
    Checks if all dependencies are available.
    """
    from app.db.mongodb import mongodb_client
    from app.db.redis_db import redis_client
    
    checks = {
        "mongodb": False,
        "redis": False
    }
    
    # Check MongoDB
    try:
        if mongodb_client:
            await mongodb_client.admin.command('ping')
            checks["mongodb"] = True
    except Exception:
        pass
    
    # Check Redis
    try:
        if redis_client:
            await redis_client.ping()
            checks["redis"] = True
    except Exception:
        pass
    
    all_ready = all(checks.values())
    
    return {
        "ready": all_ready,
        "checks": checks
    }


# ==================== MAIN ====================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=settings.DEBUG
    )
