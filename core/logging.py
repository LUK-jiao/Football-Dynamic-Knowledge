"""
Logging configuration and utilities.
Uses loguru for structured logging.
"""

import sys
from pathlib import Path

from loguru import logger

from core.config import get_settings


def setup_logging() -> None:
    """
    Configure application logging.
    """
    settings = get_settings()
    
    # Remove default handler
    logger.remove()
    
    # Add console handler
    logger.add(
        sys.stdout,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
    )
    
    # Add file handler
    log_path = Path(settings.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.add(
        settings.log_file,
        level=settings.log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="100 MB",
        retention="30 days",
        compression="zip",
    )
    
    logger.info("Logging configured successfully")


def get_logger(name: str):
    """Get a logger instance for a specific module."""
    return logger.bind(name=name)
