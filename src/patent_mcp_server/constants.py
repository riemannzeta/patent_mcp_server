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
    """PatentsView API endpoint paths.

    Note: The PatentsView API (search.patentsview.org) was shut down on
    March 20, 2026. These constants are retained for reference only.
    """
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


class PTABFields:
    """Verified ODP PTAB `q=` filter field names.

    Only fields confirmed against the live API are listed here. Verification method:
    compare filtered count against unfiltered baseline for the same endpoint — a strictly
    different (and non-zero for a known-present value) count means the field is real.

    All of the flat candidate names from the original plan (trialTypeCategory,
    proceedingStatusCategory, petitionerPartyName, etc.) were confirmed NOT to exist;
    the real names are nested under trialMetaData.*, regularPetitionerData.*,
    patentOwnerData.*, appellantData.*, and decisionData.*.

    Probed 2026-05-18 against:
      - https://api.uspto.gov/api/v1/patent/trials/proceedings/search (baseline 19263)
      - https://api.uspto.gov/api/v1/patent/trials/decisions/search   (baseline 20517)
      - https://api.uspto.gov/api/v1/patent/appeals/decisions/search  (baseline 163515)
    """
    # Pre-existing verified fields (carried from prior session)
    TRIAL_NUMBER = "trialNumber"
    APPEAL_NUMBER = "appealNumber"
    PATENT_NUMBER = "patentOwnerData.patentNumber"

    # Trial type — works on proceedings and decisions endpoints
    TRIAL_TYPE = "trialMetaData.trialTypeCode"

    # Status — proceedings only
    STATUS = "trialMetaData.trialStatusCategory"

    # Petitioner name — real-party-in-interest; works on proceedings and decisions
    PETITIONER_NAME = "regularPetitionerData.realPartyInInterestName"

    # Patent owner — proceedings and decisions; realPartyInInterestName is broader
    # (e.g. "Apple" returns 26 on proceedings) vs patentOwnerName (exact string, returns 1)
    PATENT_OWNER_NAME = "patentOwnerData.realPartyInInterestName"
    # Exact-match alternative; narrower than realPartyInInterestName
    PATENT_OWNER_NAME_EXACT = "patentOwnerData.patentOwnerName"

    # Application number — proceedings and decisions use patentOwnerData path
    APPLICATION_NUMBER = "patentOwnerData.applicationNumberText"

    # Application number — appeals decisions use appellantData path
    APPEAL_APPLICATION_NUMBER = "appellantData.applicationNumberText"

    # Appeal patent owner name — appeals decisions only
    APPEAL_PATENT_OWNER_NAME = "appellantData.patentOwnerName"

    # Petition/filing dates — proceedings only
    PETITION_FILING_DATE = "trialMetaData.petitionFilingDate"
    ACCORDED_FILING_DATE = "trialMetaData.accordedFilingDate"
    TERMINATION_DATE = "trialMetaData.terminationDate"
    # Proceedings and decisions (verified on both endpoints)
    LATEST_DECISION_DATE = "trialMetaData.latestDecisionDate"

    # Decision issue date — trials/decisions and appeals/decisions
    DECISION_ISSUE_DATE = "decisionData.decisionIssueDate"


class TrademarkDefaults:
    """Default values for trademark operations."""
    SEARCH_LIMIT = 25
    SEARCH_LIMIT_MAX = 100
    # TSDR enforced limits (per API key): 60 req/min general, 4 req/min PDF/ZIP
    TSDR_RATE_LIMIT_PER_MIN = 60
    TSDR_PDF_RATE_LIMIT_PER_MIN = 4


class TmSearchFields:
    """Field names for the tmsearch.uspto.gov internal search index.

    BEST-EFFORT SHAPE — NOT verified live. tmsearch.uspto.gov is the
    undocumented internal API behind the USPTO trademark search web app
    (TESS replacement). These names are drawn from public observations of
    the web app's network calls and may change without notice. Confirm
    against live traffic (browser dev tools on tmsearch.uspto.gov) before
    relying on them; this class is the single place to fix names.
    """
    WORDMARK = "wordmark"
    OWNER = "ownerFullText"
    SERIAL_NUMBER = "id"
    REGISTRATION_NUMBER = "registrationId"
    INTERNATIONAL_CLASS = "internationalClasses"
    ALIVE = "alive"
    GOODS_AND_SERVICES = "goodsAndServices"
    MARK_TYPE = "markType"
    REGISTRATION_DATE = "registrationDate"
    ABANDON_DATE = "abandonDate"


class OfficeActionTypes:
    """Office Action types."""
    NON_FINAL = "Non-Final Rejection"
    FINAL = "Final Rejection"
    ALLOWANCE = "Notice of Allowance"
    RESTRICTION = "Restriction Requirement"
    ADVISORY = "Advisory Action"
