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
    # File-wrapper listings: a wrapper can hold 200+ documents at ~450
    # characters each, so page through them.
    DOCUMENT_LIST_LIMIT = 50
    # Cap on binary (PDF) payloads returned through MCP as base64. Office
    # actions are usually well under 1 MB; a full specification with
    # drawings can be several.
    MAX_BINARY_BYTES = 4_000_000
    # ODP office-action and petition-decision searches refuse a page over
    # 100 with a 400 (verified live 2026-10-14); the tools clamp instead.
    ODP_SEARCH_MAX_LIMIT = 100
    # odp_download_document(format="text") pages long papers. 24k
    # characters is ~6k tokens, inside MAX_RESPONSE_TOKENS' default of
    # 8000 with room for the envelope; a typical office action is
    # 10-20k characters, so most fit in one page.
    DOCUMENT_TEXT_PAGE_CHARS = 24_000
    REQUEST_TIMEOUT = 30.0
    RETRY_DELAY = 1.0
    MAX_RETRIES = 3
    SESSION_EXPIRY_MINUTES = 30
    RATE_LIMIT_RETRY_DELAY = 5


class CpcDefaults:
    """Defaults for CPC scheme lookups."""
    # A subclass page changes only when USPTO publishes a new CPC version
    # (a few times a year), so a day-long in-process cache is safe.
    CACHE_SECONDS = 24 * 60 * 60
    # ~700 subclasses exist; cap the cache well above any one session's use.
    CACHE_MAX_SUBCLASSES = 200


class DocumentSections:
    """Named parts of a PPUBS full-text document (ppubs_get_* ``sections``).

    A whole document runs 20-40k tokens, most of it descriptionHtml. Callers
    that only need the claims or the front page can ask for those alone.
    """
    BIBLIO = "biblio"
    ABSTRACT = "abstract"
    CLAIMS = "claims"
    DESCRIPTION = "description"
    ALL = [BIBLIO, ABSTRACT, CLAIMS, DESCRIPTION]
    # Raw *Html fields that carry each text section.
    HTML_FIELDS = {
        ABSTRACT: ("abstractHtml",),
        CLAIMS: ("claimsHtml",),
        DESCRIPTION: ("descriptionHtml", "briefHtml", "backgroundTextHtml"),
    }
    # Always kept, so a claims-only response still says which patent it is.
    IDENTITY_FIELDS = (
        "guid", "type", "inventionTitle", "datePublished",
        "applicationNumber", "publicationReferenceDocumentNumber",
    )


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


class OfficeActionFields:
    """ODP Office Action Search `q=` field names (verified live 2026-10-14).

    Endpoint: POST /api/v1/patent/office-action/search (19.9M records,
    earliest submissionDate 2007-07-27). officeActionText is indexed in
    full but returned cut at 500 characters.
    """
    RECORD_ID = "officeActionRecordIdentifier"
    APPLICATION_NUMBER = "applicationNumberText"
    DOCUMENT_CODE = "documentCode"
    REJECTION_TYPE = "rejectionTypeBag"
    ART_UNIT = "groupArtUnitNumber"
    SUBMISSION_DATE = "submissionDate"
    TEXT = "officeActionText"
    FACETS = ("documentCode", "rejectionTypeBag")
    # Values rejectionTypeBag holds, keyed by lower case for lookup.
    REJECTION_TYPES = {
        v.lower(): v for v in ("101", "102", "103", "112", "DoublePatent", "Other")
    }


class PetitionDecisionFields:
    """ODP Petition Decisions `q=` field names (verified live 2026-10-14).

    Endpoint: POST /api/v1/petition/decisions/search (1.1M records,
    earliest decisionDate 1991-01-10).
    """
    RECORD_ID = "petitionDecisionRecordIdentifier"
    APPLICATION_NUMBER = "applicationNumberText"
    PATENT_NUMBER = "patentNumber"
    PETITION_TYPE_CODE = "decisionPetitionTypeCode"
    PETITION_TYPE_TEXT = "decisionPetitionTypeCodeDescriptionText"
    # The description field is analyzed text, so "GRANTED" also matches
    # GRANTED-IN-PART; the one-letter code is exact.
    OUTCOME_CODE = "decidedPetitionTypeCode"
    OUTCOME_TEXT = "decidedPetitionTypeCodeDescriptionText"
    DECIDING_OFFICE = "finalDecidingOfficeName"
    TECHNOLOGY_CENTER = "technologyCenter"
    DECISION_DATE = "decisionDate"
    FINAL = "finalPetitionDecisionIndicator"
    TEXT = "ocrSearchText"
    FACETS = (OUTCOME_TEXT, DECIDING_OFFICE, PETITION_TYPE_CODE)
    OUTCOME_CODES = {
        "GRANTED": "A",
        "GRANTED-IN-PART": "B",
        "DENIED": "C",
        "DISMISSED": "D",
    }


class OfficeActionRejectionFields:
    """ODP office action rejection dataset `criteria` fields (verified live
    2026-10-15).

    Endpoint: POST /api/v1/patent/oa/oa_rejections/v2/records (93.4M rows
    from 2012 on). One row per claim group and statute, machine-extracted;
    an office action has several. obsoleteDocumentIdentifier is the
    file-wrapper documentIdentifier.
    """
    APPLICATION_NUMBER = "patentApplicationNumber"
    DOCUMENT_ID = "obsoleteDocumentIdentifier"
    DOCUMENT_CODE = "legacyDocumentCodeIdentifier"
    SUBMISSION_DATE = "submissionDate"
    ART_UNIT = "groupArtUnitNumber"
    # 0/1 flags, one per statute; legalSectionCode is often blank, so the
    # flags are the reliable filter.
    STATUTE_FLAGS = {
        "101": "hasRej101",
        "102": "hasRej102",
        "103": "hasRej103",
        "112": "hasRej112",
        "DP": "hasRejDP",
    }
    # Boolean flags for the case law an action cites.
    CASE_LAW_FLAGS = {
        "alice": "aliceIndicator",
        "mayo": "mayoIndicator",
        "myriad": "myriadIndicator",
        "bilski": "bilskiIndicator",
    }


class OfficeActionCitationFields:
    """ODP office action citation dataset `criteria` fields (verified live
    2026-10-15).

    Endpoint: POST /api/v1/patent/oa/oa_citations/v2/records. One row per
    reference an office action cites; rows carry no mail date.
    parsedReferenceIdentifier holds the digits of a US patent or
    publication number ("6750970", "20180292319") and is blank for foreign
    and non-patent references.
    """
    APPLICATION_NUMBER = "patentApplicationNumber"
    DOCUMENT_ID = "obsoleteDocumentIdentifier"
    REFERENCE = "parsedReferenceIdentifier"
    REFERENCE_TEXT = "referenceIdentifier"
    LEGAL_SECTION = "legalSectionCode"
    ART_UNIT = "groupArtUnitNumber"
    TECH_CENTER = "techCenter"
    EXAMINER_CITED = "examinerCitedReferenceIndicator"


class OfficeActionDatasetDefaults:
    """Paging for the rejection and citation datasets, which do not cap rows."""
    LIMIT = 50
    LIMIT_MAX = 200


class TrademarkDefaults:
    """Default values for trademark operations."""
    SEARCH_LIMIT = 25
    SEARCH_LIMIT_MAX = 100
    # TSDR enforced limits (per API key): 60 req/min general, 4 req/min PDF/ZIP
    TSDR_RATE_LIMIT_PER_MIN = 60
    TSDR_PDF_RATE_LIMIT_PER_MIN = 4
    # Cap on binary (PDF/image) payloads returned through MCP. Full file
    # wrappers can exceed 10 MB (NIKE's is 13 MB); base64 of that would
    # overwhelm the response. Filtered bundles stay well under this.
    MAX_BINARY_BYTES = 4_000_000


class TmSearchFields:
    """Field names for the tmsearch.uspto.gov internal search index.

    VERIFIED LIVE 2026-06-10 against POST /prod-stage-v1-0-0/tmsearch.
    tmsearch.uspto.gov is the undocumented internal API behind the USPTO
    trademark search web app (TESS replacement); it may still change
    without notice. This class is the single place to fix names.

    Notes from live verification:
      - The index stores serial numbers in "id" (also echoed as the hit id).
      - internationalClass values are stored as "IC 025"-style tokens, so
        term filters must use zero-padded 3-digit class numbers ("025").
      - Responses use {"hits": {"totalValue": N, "hits": [{"source": ...}]}}
        (not the standard Elasticsearch total.value/_source envelope).
    """
    WORDMARK = "wordmark"
    OWNER = "ownerFullText"
    SERIAL_NUMBER = "id"
    REGISTRATION_NUMBER = "registrationId"
    INTERNATIONAL_CLASS = "internationalClass"
    ALIVE = "alive"
    GOODS_AND_SERVICES = "goodsAndServices"
    MARK_TYPE = "markType"
    REGISTRATION_DATE = "registrationDate"
    ABANDON_DATE = "abandonDate"
    STATUS_CODE = "statusCode"
    STATUS_DESCRIPTION = "statusDescription"


class OfficeActionTypes:
    """Office Action types."""
    NON_FINAL = "Non-Final Rejection"
    FINAL = "Final Rejection"
    ALLOWANCE = "Notice of Allowance"
    RESTRICTION = "Restriction Requirement"
    ADVISORY = "Advisory Action"
