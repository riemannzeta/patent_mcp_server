"""
Input validation models for USPTO Patent MCP Server.

This module provides Pydantic models for validating input parameters
to ensure data integrity and provide clear error messages.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional


class PatentNumberInput(BaseModel):
    """Validation model for patent numbers."""

    patent_number: str = Field(..., min_length=1, description="Patent number")

    @field_validator('patent_number')
    @classmethod
    def validate_patent_number(cls, v: str) -> str:
        """Validate and clean patent number."""
        # Remove any non-numeric characters
        cleaned = ''.join(c for c in str(v) if c.isdigit())
        if not cleaned:
            raise ValueError("Patent number must contain at least one digit")
        return cleaned


class ApplicationNumberInput(BaseModel):
    """Validation model for application numbers."""

    app_num: str = Field(..., min_length=1, description="Application number")

    @field_validator('app_num')
    @classmethod
    def validate_app_num(cls, v: str) -> str:
        """Validate and clean application number."""
        # Remove slashes, commas, and spaces
        cleaned = ''.join(c for c in str(v) if c.isdigit())
        if not cleaned:
            raise ValueError("Application number must contain at least one digit")
        if len(cleaned) < 6:
            raise ValueError("Application number must be at least 6 digits")
        return cleaned


class TrademarkSerialInput(BaseModel):
    """Validation model for trademark application serial numbers."""

    serial_number: str = Field(..., min_length=1, description="Trademark serial number")

    @field_validator('serial_number')
    @classmethod
    def validate_serial_number(cls, v: str) -> str:
        """Validate and clean trademark serial number."""
        # Remove slashes, commas, and spaces
        cleaned = ''.join(c for c in str(v) if c.isdigit())
        if not cleaned:
            raise ValueError("Serial number must contain at least one digit")
        if len(cleaned) != 8:
            raise ValueError("Trademark serial number must be exactly 8 digits")
        return cleaned


class TrademarkRegistrationInput(BaseModel):
    """Validation model for trademark registration numbers."""

    registration_number: str = Field(..., min_length=1, description="Trademark registration number")

    @field_validator('registration_number')
    @classmethod
    def validate_registration_number(cls, v: str) -> str:
        """Validate and clean trademark registration number."""
        cleaned = ''.join(c for c in str(v) if c.isdigit())
        if not cleaned:
            raise ValueError("Registration number must contain at least one digit")
        if len(cleaned) > 8:
            raise ValueError("Trademark registration number must be at most 8 digits")
        return cleaned


class SearchQueryInput(BaseModel):
    """Validation model for search queries."""

    query: str = Field(..., min_length=1, description="Search query string")
    start: int = Field(default=0, ge=0, description="Starting position")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum results")

    @field_validator('query')
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate query string."""
        v = v.strip()
        if not v:
            raise ValueError("Query cannot be empty or whitespace only")
        return v


class GuidInput(BaseModel):
    """Validation model for document GUIDs."""

    guid: str = Field(..., min_length=1, description="Document GUID")
    source_type: str = Field(..., min_length=1, description="Source type")

    @field_validator('guid')
    @classmethod
    def validate_guid(cls, v: str) -> str:
        """Validate GUID format."""
        v = v.strip()
        if not v:
            raise ValueError("GUID cannot be empty")
        return v

    @field_validator('source_type')
    @classmethod
    def validate_source_type(cls, v: str) -> str:
        """Validate source type."""
        v = v.strip()
        valid_sources = ["USPAT", "US-PGPUB", "USOCR"]
        if v not in valid_sources:
            raise ValueError(f"Source type must be one of: {', '.join(valid_sources)}")
        return v


class PaginationInput(BaseModel):
    """Validation model for pagination parameters."""

    offset: int = Field(default=0, ge=0, description="Number of records to skip")
    limit: int = Field(default=25, ge=1, le=1000, description="Number of records to return")


def validate_patent_number(patent_number: str) -> str:
    """
    Validate and clean a patent number.

    Args:
        patent_number: Raw patent number input

    Returns:
        Cleaned patent number string

    Raises:
        ValueError: If patent number is invalid
    """
    try:
        validated = PatentNumberInput(patent_number=patent_number)
        return validated.patent_number
    except Exception as e:
        raise ValueError(f"Invalid patent number: {str(e)}")


def validate_app_number(app_num: str) -> str:
    """
    Validate and clean an application number.

    Args:
        app_num: Raw application number input

    Returns:
        Cleaned application number string

    Raises:
        ValueError: If application number is invalid
    """
    try:
        validated = ApplicationNumberInput(app_num=app_num)
        return validated.app_num
    except Exception as e:
        raise ValueError(f"Invalid application number: {str(e)}")


def validate_serial_number(serial_number: str) -> str:
    """
    Validate and clean a trademark serial number.

    Args:
        serial_number: Raw serial number input

    Returns:
        Cleaned 8-digit serial number string

    Raises:
        ValueError: If serial number is invalid
    """
    try:
        validated = TrademarkSerialInput(serial_number=serial_number)
        return validated.serial_number
    except Exception as e:
        raise ValueError(f"Invalid trademark serial number: {str(e)}")


def validate_registration_number(registration_number: str) -> str:
    """
    Validate and clean a trademark registration number.

    Args:
        registration_number: Raw registration number input

    Returns:
        Cleaned registration number string

    Raises:
        ValueError: If registration number is invalid
    """
    try:
        validated = TrademarkRegistrationInput(registration_number=registration_number)
        return validated.registration_number
    except Exception as e:
        raise ValueError(f"Invalid trademark registration number: {str(e)}")
