"""
AURA Logging Configuration
Production-ready structured logging with loguru
"""

import sys
import os
from pathlib import Path
from loguru import logger

from app.core.config import settings


def setup_logging() -> None:
    """Configure application logging."""
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Remove default handler
    logger.remove()
    
    # Console format based on LOG_FORMAT setting
    if settings.LOG_FORMAT == "json":
        log_format = (
            '{{"timestamp":"{time:YYYY-MM-DDTHH:mm:ss.SSSZ}",'
            '"level":"{level}",'
            '"message":"{message}",'
            '"module":"{module}",'
            '"function":"{function}",'
            '"line":{line}}}'
        )
        colorize = False
    else:
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{module}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
        colorize = True
    
    # Add console handler
    logger.add(
        sys.stdout,
        format=log_format,
        level=settings.LOG_LEVEL,
        colorize=colorize,
        backtrace=True,
        diagnose=settings.DEBUG
    )
    
    # Add file handler for errors
    logger.add(
        "logs/error.log",
        format=log_format,
        level="ERROR",
        rotation="10 MB",
        retention="30 days",
        compression="gz",
        backtrace=True,
        diagnose=True
    )
    
    # Add file handler for all logs
    logger.add(
        "logs/app.log",
        format=log_format,
        level="INFO",
        rotation="50 MB",
        retention="7 days",
        compression="gz"
    )
    
    # Add file handler for debug logs (only in DEBUG mode)
    if settings.DEBUG:
        logger.add(
            "logs/debug.log",
            format=log_format,
            level="DEBUG",
            rotation="100 MB",
            retention="3 days"
        )
    
    logger.info(f"Logging initialized - Level: {settings.LOG_LEVEL}, Format: {settings.LOG_FORMAT}")


class LoggerContextManager:
    """Context manager for adding context to log messages."""
    
    def __init__(self, **context):
        self.context = context
        self._token = None
    
    def __enter__(self):
        self._token = logger.bind(**self.context)
        return self._token
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def get_logger(name: str = None):
    """Get a logger instance with optional name binding."""
    if name:
        return logger.bind(service=name)
    return logger


# Export logger instance
__all__ = ["logger", "setup_logging", "get_logger", "LoggerContextManager"]
