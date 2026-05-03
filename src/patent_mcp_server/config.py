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

    # PatentsView API - shut down March 20, 2026; data migrated to ODP bulk datasets
    PATENTSVIEW_API_KEY: Optional[str] = os.getenv("PATENTSVIEW_API_KEY")  # Legacy - shut down March 2026
    PATENTSVIEW_BASE_URL: str = os.getenv("PATENTSVIEW_BASE_URL", "https://search.patentsview.org")  # Legacy - shut down March 2026
    PATENTSVIEW_RATE_LIMIT: int = int(os.getenv("PATENTSVIEW_RATE_LIMIT", "45"))  # Legacy - shut down March 2026

    # Office Action API
    OFFICE_ACTION_BASE_URL: str = os.getenv("OFFICE_ACTION_BASE_URL", "https://developer.uspto.gov")  # Legacy - decommissioned early 2026, pending ODP migration

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # HTTP Settings
    USER_AGENT: str = os.getenv("USER_AGENT", "patent-mcp-server/0.9.1")
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

    # Response Size Management (for LLM context windows)
    MAX_RESPONSE_TOKENS: int = int(os.getenv("MAX_RESPONSE_TOKENS", "8000"))
    TRUNCATE_LARGE_RESPONSES: bool = os.getenv("TRUNCATE_LARGE_RESPONSES", "true").lower() == "true"
    DEFAULT_TRUNCATE_RESULTS: int = int(os.getenv("DEFAULT_TRUNCATE_RESULTS", "20"))

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
                "USPTO_API_KEY not set. ODP API tools (api.uspto.gov) will return 403. "
                "Register at https://data.uspto.gov and visit 'My ODP' to get your API key. "
                "Note: PTAB and Litigation tools do not require an API key — they are "
                "unavailable on ODP entirely (see issue #16)."
            )

        # PatentsView API was shut down March 20, 2026 - no longer warn about missing key

        logger.info(f"Configuration loaded: LOG_LEVEL={cls.LOG_LEVEL}, "
                   f"TIMEOUT={cls.REQUEST_TIMEOUT}s, "
                   f"CACHING={'enabled' if cls.ENABLE_CACHING else 'disabled'}")


# Create singleton instance
config = Config()
