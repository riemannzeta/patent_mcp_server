"""
Constants used throughout the USPTO Patent MCP Server.

This module defines all constants, magic strings, and enumerations used
across the application to avoid duplication and improve maintainability.
"""

class Sources:
    """Patent data source types."""
    GRANTED_PATENTS = "USPAT"
    PUBLISHED_APPLICATIONS = "US-PGPUB"
    OCR = "USOCR"
    ALL = [GRANTED_PATENTS, PUBLISHED_APPLICATIONS, OCR]


class Fields:
    """Common field names in API responses."""
    GUID = "guid"
    TYPE = "type"
    IMAGE_LOCATION = "imageLocation"
    PAGE_COUNT = "pageCount"
    DOCUMENT_STRUCTURE = "document_structure"
    PATENTS = "patents"
    DOCS = "docs"
    ERROR = "error"
    MESSAGE = "message"
    STATUS_CODE = "status_code"
    ERROR_CODE = "errorCode"
    ERROR_MESSAGE = "errorMessage"
    NUM_FOUND = "numFound"
    RESULTS = "results"
    TOTAL = "total"


class SortOrders:
    """Common sort order strings."""
    DATE_DESC = "date_publ desc"
    DATE_ASC = "date_publ asc"


class Operators:
    """Query operators."""
    AND = "AND"
    OR = "OR"


class PrintStatus:
    """PDF print job status values."""
    COMPLETED = "COMPLETED"
    PENDING = "PENDING"
    FAILED = "FAILED"


class HTTPMethods:
    """HTTP methods."""
    GET = "GET"
    POST = "POST"


class Defaults:
    """Default values for various operations."""
    SEARCH_START = 0
    SEARCH_LIMIT = 100
    SEARCH_LIMIT_MAX = 500
    API_LIMIT = 25
    DATASET_LIMIT = 10
    REQUEST_TIMEOUT = 30.0
    RETRY_DELAY = 1.0
    MAX_RETRIES = 3
    SESSION_EXPIRY_MINUTES = 30
    RATE_LIMIT_RETRY_DELAY = 5


class GooglePatentsTables:
    """Google Patents Public Datasets BigQuery table names."""
    PUBLICATIONS = "publications"
    PUBLICATIONS_CLAIMS = "publications_claims"
    PUBLICATIONS_DESCRIPTION = "publications_description"
    CLASSIFICATIONS = "classifications"
    CITATIONS = "citations"


class GooglePatentsCountries:
    """Country codes for Google Patents searches."""
    US = "US"  # United States
    EP = "EP"  # European Patent Office
    WO = "WO"  # World Intellectual Property Organization (PCT)
    JP = "JP"  # Japan
    CN = "CN"  # China
    KR = "KR"  # South Korea
    GB = "GB"  # Great Britain
    DE = "DE"  # Germany
    FR = "FR"  # France
    CA = "CA"  # Canada
    AU = "AU"  # Australia

    ALL = [US, EP, WO, JP, CN, KR, GB, DE, FR, CA, AU]
