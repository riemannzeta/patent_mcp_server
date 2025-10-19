"""
Configuration management for USPTO Patent MCP Server.

This module provides centralized configuration loading from environment
variables with sensible defaults.
"""

from dotenv import load_dotenv
import os
from typing import Optional
import logging

# Load environment variables from .env file
load_dotenv()


class Config:
    """Centralized configuration class."""

    # API Keys
    USPTO_API_KEY: Optional[str] = os.getenv("USPTO_API_KEY")

    # API Endpoints
    PPUBS_BASE_URL: str = os.getenv("PPUBS_BASE_URL", "https://ppubs.uspto.gov")
    API_BASE_URL: str = os.getenv("API_BASE_URL", "https://api.uspto.gov")

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # HTTP Settings
    USER_AGENT: str = os.getenv("USER_AGENT", "patent-mcp-server/0.2.2")
    REQUEST_TIMEOUT: float = float(os.getenv("REQUEST_TIMEOUT", "30.0"))

    # Rate Limiting & Retry
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY: float = float(os.getenv("RETRY_DELAY", "1.0"))
    RETRY_MIN_WAIT: int = int(os.getenv("RETRY_MIN_WAIT", "2"))
    RETRY_MAX_WAIT: int = int(os.getenv("RETRY_MAX_WAIT", "10"))

    # Session Management
    SESSION_EXPIRY_MINUTES: int = int(os.getenv("SESSION_EXPIRY_MINUTES", "30"))

    # Caching
    ENABLE_CACHING: bool = os.getenv("ENABLE_CACHING", "true").lower() == "true"

    @classmethod
    def get_log_level(cls) -> int:
        """Convert LOG_LEVEL string to logging constant."""
        levels = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        return levels.get(cls.LOG_LEVEL.upper(), logging.INFO)

    @classmethod
    def validate(cls) -> None:
        """Validate configuration and log warnings for missing optional settings."""
        logger = logging.getLogger(__name__)

        if not cls.USPTO_API_KEY:
            logger.warning(
                "USPTO_API_KEY not set. API tools (api.uspto.gov) may not work. "
                "See README.md for instructions on obtaining an API key."
            )

        logger.info(f"Configuration loaded: LOG_LEVEL={cls.LOG_LEVEL}, "
                   f"TIMEOUT={cls.REQUEST_TIMEOUT}s, "
                   f"CACHING={'enabled' if cls.ENABLE_CACHING else 'disabled'}")


# Create singleton instance
config = Config()
