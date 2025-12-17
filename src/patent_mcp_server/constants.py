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


class PTABTrialTypes:
    """PTAB trial type codes."""
    IPR = "IPR"  # Inter Partes Review
    PGR = "PGR"  # Post Grant Review
    CBM = "CBM"  # Covered Business Method
    DER = "DER"  # Derivation proceeding

    ALL = [IPR, PGR, CBM, DER]


class PTABProceedingStatus:
    """PTAB proceeding status values."""
    PENDING = "Pending"
    INSTITUTED = "Instituted"
    TERMINATED = "Terminated"
    FWD_ENTERED = "FWD Entered"  # Final Written Decision


class PatentsViewEndpoints:
    """PatentsView API endpoint paths."""
    # Core patent endpoints
    PATENT = "/api/v1/patent/"
    PUBLICATION = "/api/v1/publication/"

    # Entity endpoints
    ASSIGNEE = "/api/v1/assignee/"
    INVENTOR = "/api/v1/inventor/"
    ATTORNEY = "/api/v1/patent/attorney/"

    # Classification endpoints
    CPC_CLASS = "/api/v1/cpc_class/"
    CPC_SUBCLASS = "/api/v1/cpc_subclass/"
    CPC_GROUP = "/api/v1/cpc_group/"
    IPC = "/api/v1/ipc/"

    # Patent text endpoints (granted patents)
    CLAIMS = "/api/v1/g_claim/"
    BRIEF_SUMMARY = "/api/v1/g_brf_sum_text/"
    DESCRIPTION = "/api/v1/g_detail_desc_text/"
    DRAWING_DESC = "/api/v1/g_draw_desc_text/"

    # Publication text endpoints (pregrant)
    PG_CLAIMS = "/api/v1/pg_claim/"
    PG_BRIEF_SUMMARY = "/api/v1/pg_brf_sum_text/"
    PG_DESCRIPTION = "/api/v1/pg_detail_desc_text/"
    PG_DRAWING_DESC = "/api/v1/pg_draw_desc_text/"

    # Citation endpoints
    FOREIGN_CITATION = "/api/v1/patent/foreign_citation/"
    US_PATENT_CITATION = "/api/v1/patent/us_patent_citation/"
    US_APPLICATION_CITATION = "/api/v1/patent/us_application_citation/"


class OfficeActionTypes:
    """Office Action types."""
    NON_FINAL = "Non-Final Rejection"
    FINAL = "Final Rejection"
    ALLOWANCE = "Notice of Allowance"
    RESTRICTION = "Restriction Requirement"
    ADVISORY = "Advisory Action"
