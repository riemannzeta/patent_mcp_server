"""
USPTO Patent Search MCP Server

This file provides a Model Context Protocol (MCP) server that exposes tools for interacting with multiple USPTO APIs:

1. ppubs.uspto.gov - Provides full text patent documents, PDF downloads, and advanced search
2. api.uspto.gov - Provides metadata, continuity information, transactions, and assignments

The server uses stdio transport for command-line tools, following the MCP standard.
"""
import atexit
import logging
import sys
from typing import Any, Dict, List, Optional, Union

from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError

from patent_mcp_server.config import config
from patent_mcp_server.constants import Sources, Fields, Defaults, GooglePatentsCountries
from patent_mcp_server.util.errors import ApiError, is_error
from patent_mcp_server.util.validation import validate_patent_number, validate_app_number
from patent_mcp_server.uspto.ppubs_uspto_gov import PpubsClient
from patent_mcp_server.uspto.api_uspto_gov import ApiUsptoClient
from patent_mcp_server.google.bigquery_client import GoogleBigQueryClient

# Initialize FastMCP server
mcp = FastMCP("uspto_patent_tools")

# Set up logging with configured level
logging.basicConfig(
    level=config.get_log_level(),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger('uspto_patent_mcp')

# Validate configuration
config.validate()

# Create client instances for each USPTO API
ppubs_client = PpubsClient()
api_client = ApiUsptoClient()

# Create Google Patents BigQuery client
google_bq_client = GoogleBigQueryClient()


# Register cleanup handler
async def cleanup():
    """Clean up resources on shutdown."""
    logger.info("Shutting down USPTO Patent MCP server, cleaning up resources...")
    try:
        await ppubs_client.close()
        await api_client.close()
        await google_bq_client.close()
        logger.info("Cleanup completed successfully")
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")


# Register cleanup with atexit (best effort for stdio shutdown)
def sync_cleanup():
    """Synchronous cleanup wrapper for atexit."""
    import asyncio
    try:
        # Try to get existing event loop
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                loop.create_task(cleanup())
                return
        except RuntimeError:
            pass  # No running loop

        # Create new loop for cleanup
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(cleanup())
        finally:
            loop.close()
    except Exception as e:
        logger.debug(f"Cleanup during shutdown (non-critical): {str(e)}")


atexit.register(sync_cleanup)


# =====================================================================
# Helper Functions
# =====================================================================

async def _search_patent_by_number(patent_number: str) -> Dict[str, Any]:
    """
    Search for a patent by number and return the patent document metadata.

    This is a helper function to avoid code duplication between
    ppubs_get_patent_by_number and ppubs_download_patent_pdf.

    Args:
        patent_number: The patent number to search for

    Returns:
        Dictionary with 'success' and 'patent' keys, or error dictionary
    """
    # First search for the patent using specific field
    query = f'patentNumber:"{patent_number}"'
    logger.info(f"Searching for patent with query: {query}")

    result = await ppubs_client.run_query(
        query=query,
        sources=[Sources.GRANTED_PATENTS],
        limit=1
    )

    if is_error(result):
        return result

    # Handle different response structures
    patents = result.get(Fields.PATENTS, result.get(Fields.DOCS, []))

    if patents and len(patents) > 0:
        logger.info(f"Found patent: {patents[0].get(Fields.GUID)}")
        return {"success": True, "patent": patents[0]}

    # Try alternative query format
    alternative_query = f'"{patent_number}".pn.'
    logger.info(f"No results found, trying alternative query: {alternative_query}")

    result = await ppubs_client.run_query(
        query=alternative_query,
        sources=[Sources.GRANTED_PATENTS],
        limit=1
    )

    if is_error(result):
        return result

    patents = result.get(Fields.PATENTS, result.get(Fields.DOCS, []))

    if not patents or len(patents) == 0:
        return ApiError.not_found("Patent", patent_number)

    logger.info(f"Found patent: {patents[0].get(Fields.GUID)}")
    return {"success": True, "patent": patents[0]}


# =====================================================================
# Tools for ppubs.uspto.gov (full text patents and PDF downloads)
# =====================================================================

@mcp.tool()
async def ppubs_search_patents(
    query: str,
    start: Optional[int] = Defaults.SEARCH_START,
    limit: Optional[int] = Defaults.SEARCH_LIMIT,
    sort: Optional[str] = "date_publ desc",
    default_operator: Optional[str] = "OR",
    expand_plurals: Optional[bool] = True,
    british_equivalents: Optional[bool] = True
) -> Dict[str, Any]:
    """Search for granted patents in USPTO Public Search (ppubs.uspto.gov)

    This tool searches full text patents and provides results that include the
    complete text and sections of patents.

    Args:
        query: The search query string using USPTO search syntax
        start: Starting position for results (default: 0)
        limit: Maximum number of results to return (default: 100)
        sort: Sort order (default: "date_publ desc")
        default_operator: Default operator for query terms (AND/OR, default: OR)
        expand_plurals: Whether to include plural forms (default: True)
        british_equivalents: Whether to include British spelling equivalents (default: True)
    """
    return await ppubs_client.run_query(
        query=query,
        start=start,
        limit=limit,
        sort=sort,
        default_operator=default_operator,
        sources=[Sources.GRANTED_PATENTS],
        expand_plurals=expand_plurals,
        british_equivalents=british_equivalents
    )


@mcp.tool()
async def ppubs_search_applications(
    query: str,
    start: Optional[int] = Defaults.SEARCH_START,
    limit: Optional[int] = Defaults.SEARCH_LIMIT,
    sort: Optional[str] = "date_publ desc",
    default_operator: Optional[str] = "OR",
    expand_plurals: Optional[bool] = True,
    british_equivalents: Optional[bool] = True
) -> Dict[str, Any]:
    """Search for published patent applications in USPTO Public Search (ppubs.uspto.gov)

    This tool searches full text patent applications and provides results that include
    the complete text and sections of applications.

    Args:
        query: The search query string using USPTO search syntax
        start: Starting position for results (default: 0)
        limit: Maximum number of results to return (default: 100)
        sort: Sort order (default: "date_publ desc")
        default_operator: Default operator for query terms (AND/OR, default: OR)
        expand_plurals: Whether to include plural forms (default: True)
        british_equivalents: Whether to include British spelling equivalents (default: True)
    """
    return await ppubs_client.run_query(
        query=query,
        start=start,
        limit=limit,
        sort=sort,
        default_operator=default_operator,
        sources=[Sources.PUBLISHED_APPLICATIONS],
        expand_plurals=expand_plurals,
        british_equivalents=british_equivalents
    )


@mcp.tool()
async def ppubs_get_full_document(guid: str, source_type: str) -> Dict[str, Any]:
    """Get full patent document details by GUID from ppubs.uspto.gov

    This tool retrieves complete document text including claims, description,
    and all document sections.

    Args:
        guid: The unique identifier for the document (e.g., "US-9876543-B2")
        source_type: The document type (e.g., "USPAT" or "US-PGPUB")
    """
    return await ppubs_client.get_document(guid, source_type)


@mcp.tool()
async def ppubs_get_patent_by_number(patent_number: Union[str, int]) -> Dict[str, Any]:
    """Get a granted patent's full text by number from ppubs.uspto.gov

    This tool retrieves the complete patent document including claims, description,
    and all sections of the patent.

    Args:
        patent_number: The patent number (e.g., '7123456')
    """
    # Validate and clean patent number
    try:
        patent_number = validate_patent_number(str(patent_number))
    except ValueError as e:
        return ApiError.validation_error(str(e), "patent_number")

    # Search for the patent
    search_result = await _search_patent_by_number(patent_number)

    if is_error(search_result):
        return search_result

    # Get the full document
    patent = search_result["patent"]
    return await ppubs_client.get_document(patent[Fields.GUID], patent[Fields.TYPE])


@mcp.tool()
async def ppubs_download_patent_pdf(patent_number: Union[str, int]) -> Dict[str, Any]:
    """Download a granted patent as PDF from ppubs.uspto.gov

    This tool provides access to the complete patent document as a PDF.

    Args:
        patent_number: The patent number (e.g., '7123456')
    """
    # Validate and clean patent number
    try:
        patent_number = validate_patent_number(str(patent_number))
    except ValueError as e:
        return ApiError.validation_error(str(e), "patent_number")

    # Search for the patent
    search_result = await _search_patent_by_number(patent_number)

    if is_error(search_result):
        return search_result

    patent = search_result["patent"]

    # Handle different field naming in the response
    image_location = patent.get(
        Fields.IMAGE_LOCATION,
        patent.get(Fields.DOCUMENT_STRUCTURE, {}).get("image_location")
    )
    page_count = patent.get(
        Fields.PAGE_COUNT,
        patent.get(Fields.DOCUMENT_STRUCTURE, {}).get("page_count")
    )

    if not image_location or not page_count:
        return ApiError.create(
            message="Missing image location or page count information",
            error_code="MISSING_DOCUMENT_INFO"
        )

    # Download the PDF
    return await ppubs_client.download_image(
        patent[Fields.GUID],
        image_location,
        page_count,
        patent[Fields.TYPE]
    )


# =====================================================================
# Tools for api.uspto.gov (metadata)
# =====================================================================

USPTO_API_BASE = config.API_BASE_URL


@mcp.tool()
async def get_app(app_num: str) -> Dict[str, Any]:
    """Get patent application data

    Args:
        app_num: U.S. Patent Application Number, no / and no , (e.g. 14412875)
    """
    # Validate application number
    try:
        app_num = validate_app_number(app_num)
    except ValueError as e:
        return ApiError.validation_error(str(e), "app_num")

    url = f"{USPTO_API_BASE}/api/v1/patent/applications/{app_num}"
    return await api_client.make_request(url)


@mcp.tool()
async def search_applications(q: Optional[str] = None,
                            sort: Optional[str] = None,
                            offset: Optional[int] = Defaults.SEARCH_START,
                            limit: Optional[int] = Defaults.API_LIMIT,
                            facets: Optional[str] = None,
                            fields: Optional[str] = None,
                            filters: Optional[str] = None,
                            range_filters: Optional[str] = None) -> Dict[str, Any]:
    """Search patent applications by query parameters

    Args:
        q: Search query string (e.g., "applicationNumberText:14412875")
        sort: Field to sort by (e.g., "applicationMetaData.filingDate asc")
        offset: Position to start from (default: 0)
        limit: Maximum number of results (default: 25)
        facets: Fields to facet upon, comma-separated
        fields: Fields to include in response, comma-separated
        filters: Filter conditions, format: "field value"
        range_filters: Range filter conditions, format: "field from:to"
    """
    params = {
        "q": q,
        "sort": sort,
        "offset": offset,
        "limit": limit,
        "facets": facets,
        "fields": fields,
        "filters": filters,
        "rangeFilters": range_filters
    }

    query_string = api_client.build_query_string(params)
    url = f"{USPTO_API_BASE}/api/v1/patent/applications/search"
    if query_string:
        url = f"{url}?{query_string}"

    return await api_client.make_request(url)


@mcp.tool()
async def search_applications_post(q: Optional[str] = None,
                                 filters: Optional[List[Dict[str, Any]]] = None,
                                 range_filters: Optional[List[Dict[str, Any]]] = None,
                                 sort: Optional[List[Dict[str, Any]]] = None,
                                 fields: Optional[List[str]] = None,
                                 offset: Optional[int] = Defaults.SEARCH_START,
                                 limit: Optional[int] = Defaults.API_LIMIT,
                                 facets: Optional[List[str]] = None) -> Dict[str, Any]:
    """Search patent applications by supplying JSON payload

    Args:
        q: Search query string
        filters: List of filter objects [{"name": "field_name", "value": ["value1", "value2"]}]
        range_filters: List of range filter objects [{"field": "field_name", "valueFrom": "value1", "valueTo": "value2"}]
        sort: List of sort objects [{"field": "field_name", "order": "asc/desc"}]
        fields: List of field names to include
        offset: Position to start from (default: 0)
        limit: Maximum number of results (default: 25)
        facets: List of field names to facet upon
    """
    data = {
        "q": q,
        "filters": filters,
        "rangeFilters": range_filters,
        "sort": sort,
        "fields": fields,
        "pagination": {"offset": offset, "limit": limit},
        "facets": facets
    }

    # Remove None values
    data = {k: v for k, v in data.items() if v is not None}

    url = f"{USPTO_API_BASE}/api/v1/patent/applications/search"
    return await api_client.make_request(url, method="POST", data=data)


@mcp.tool()
async def download_applications(q: Optional[str] = None,
                              sort: Optional[str] = None,
                              offset: Optional[int] = Defaults.SEARCH_START,
                              limit: Optional[int] = Defaults.API_LIMIT,
                              fields: Optional[str] = None,
                              filters: Optional[str] = None,
                              range_filters: Optional[str] = None,
                              format: Optional[str] = "json") -> Dict[str, Any]:
    """Download patent applications by query parameters

    Args:
        q: Search query string
        sort: Field to sort by
        offset: Position to start from (default: 0)
        limit: Maximum number of results (default: 25)
        fields: Fields to include in response, comma-separated
        filters: Filter conditions, format: "field value"
        range_filters: Range filter conditions, format: "field from:to"
        format: Download format (json or csv, default: json)
    """
    params = {
        "q": q,
        "sort": sort,
        "offset": offset,
        "limit": limit,
        "fields": fields,
        "filters": filters,
        "rangeFilters": range_filters,
        "format": format
    }

    query_string = api_client.build_query_string(params)
    url = f"{USPTO_API_BASE}/api/v1/patent/applications/search/download"
    if query_string:
        url = f"{url}?{query_string}"

    return await api_client.make_request(url)


@mcp.tool()
async def download_applications_post(q: Optional[str] = None,
                                   filters: Optional[List[Dict[str, Any]]] = None,
                                   range_filters: Optional[List[Dict[str, Any]]] = None,
                                   sort: Optional[List[Dict[str, Any]]] = None,
                                   fields: Optional[List[str]] = None,
                                   offset: Optional[int] = Defaults.SEARCH_START,
                                   limit: Optional[int] = Defaults.API_LIMIT,
                                   format: Optional[str] = "json") -> Dict[str, Any]:
    """Download patent applications by supplying JSON payload

    Args:
        q: Search query string
        filters: List of filter objects [{"name": "field_name", "value": ["value1", "value2"]}]
        range_filters: List of range filter objects [{"field": "field_name", "valueFrom": "value1", "valueTo": "value2"}]
        sort: List of sort objects [{"field": "field_name", "order": "asc/desc"}]
        fields: List of field names to include
        offset: Position to start from (default: 0)
        limit: Maximum number of results (default: 25)
        format: Download format (json or csv, default: json)
    """
    data = {
        "q": q,
        "filters": filters,
        "rangeFilters": range_filters,
        "sort": sort,
        "fields": fields,
        "pagination": {"offset": offset, "limit": limit},
        "format": format
    }

    # Remove None values
    data = {k: v for k, v in data.items() if v is not None}

    url = f"{USPTO_API_BASE}/api/v1/patent/applications/search/download"
    return await api_client.make_request(url, method="POST", data=data)


@mcp.tool()
async def get_app_metadata(app_num: str) -> Dict[str, Any]:
    """Get patent application metadata

    Args:
        app_num: U.S. Patent Application Number (e.g., 14412875)
    """
    try:
        app_num = validate_app_number(app_num)
    except ValueError as e:
        return ApiError.validation_error(str(e), "app_num")

    url = f"{USPTO_API_BASE}/api/v1/patent/applications/{app_num}/meta-data"
    return await api_client.make_request(url)


@mcp.tool()
async def get_app_adjustment(app_num: str) -> Dict[str, Any]:
    """Get patent term adjustment data for an application

    Args:
        app_num: U.S. Patent Application Number (e.g., 14412875)
    """
    try:
        app_num = validate_app_number(app_num)
    except ValueError as e:
        return ApiError.validation_error(str(e), "app_num")

    url = f"{USPTO_API_BASE}/api/v1/patent/applications/{app_num}/adjustment"
    return await api_client.make_request(url)


@mcp.tool()
async def get_app_assignment(app_num: str) -> Dict[str, Any]:
    """Get patent assignment data for an application

    Args:
        app_num: U.S. Patent Application Number (e.g., 14412875)
    """
    try:
        app_num = validate_app_number(app_num)
    except ValueError as e:
        return ApiError.validation_error(str(e), "app_num")

    url = f"{USPTO_API_BASE}/api/v1/patent/applications/{app_num}/assignment"
    return await api_client.make_request(url)


@mcp.tool()
async def get_app_attorney(app_num: str) -> Dict[str, Any]:
    """Get attorney/agent data for an application

    Args:
        app_num: U.S. Patent Application Number (e.g., 14412875)
    """
    try:
        app_num = validate_app_number(app_num)
    except ValueError as e:
        return ApiError.validation_error(str(e), "app_num")

    url = f"{USPTO_API_BASE}/api/v1/patent/applications/{app_num}/attorney"
    return await api_client.make_request(url)


@mcp.tool()
async def get_app_continuity(app_num: str) -> Dict[str, Any]:
    """Get continuity data for an application

    Args:
        app_num: U.S. Patent Application Number (e.g., 14412875)
    """
    try:
        app_num = validate_app_number(app_num)
    except ValueError as e:
        return ApiError.validation_error(str(e), "app_num")

    url = f"{USPTO_API_BASE}/api/v1/patent/applications/{app_num}/continuity"
    return await api_client.make_request(url)


@mcp.tool()
async def get_app_foreign_priority(app_num: str) -> Dict[str, Any]:
    """Get foreign priority data for an application

    Args:
        app_num: U.S. Patent Application Number (e.g., 14412875)
    """
    try:
        app_num = validate_app_number(app_num)
    except ValueError as e:
        return ApiError.validation_error(str(e), "app_num")

    url = f"{USPTO_API_BASE}/api/v1/patent/applications/{app_num}/foreign-priority"
    return await api_client.make_request(url)


@mcp.tool()
async def get_app_transactions(app_num: str) -> Dict[str, Any]:
    """Get transaction data for an application

    Args:
        app_num: U.S. Patent Application Number (e.g., 14412875)
    """
    try:
        app_num = validate_app_number(app_num)
    except ValueError as e:
        return ApiError.validation_error(str(e), "app_num")

    url = f"{USPTO_API_BASE}/api/v1/patent/applications/{app_num}/transactions"
    return await api_client.make_request(url)


@mcp.tool()
async def get_app_documents(app_num: str) -> Dict[str, Any]:
    """Get document details for an application

    Args:
        app_num: U.S. Patent Application Number (e.g., 14412875)
    """
    try:
        app_num = validate_app_number(app_num)
    except ValueError as e:
        return ApiError.validation_error(str(e), "app_num")

    url = f"{USPTO_API_BASE}/api/v1/patent/applications/{app_num}/documents"
    return await api_client.make_request(url)


@mcp.tool()
async def get_app_associated_documents(app_num: str) -> Dict[str, Any]:
    """Get associated documents metadata for an application

    Args:
        app_num: U.S. Patent Application Number (e.g., 14412875)
    """
    try:
        app_num = validate_app_number(app_num)
    except ValueError as e:
        return ApiError.validation_error(str(e), "app_num")

    url = f"{USPTO_API_BASE}/api/v1/patent/applications/{app_num}/associated-documents"
    return await api_client.make_request(url)


# Status Code Endpoints

@mcp.tool()
async def get_status_codes(q: Optional[str] = None,
                         offset: Optional[int] = Defaults.SEARCH_START,
                         limit: Optional[int] = Defaults.API_LIMIT) -> Dict[str, Any]:
    """Search patent application status codes

    Args:
        q: Search query string
        offset: Position to start from (default: 0)
        limit: Maximum number of results (default: 25)
    """
    params = {
        "q": q,
        "offset": offset,
        "limit": limit,
    }

    query_string = api_client.build_query_string(params)
    url = f"{USPTO_API_BASE}/api/v1/patent/status-codes"
    if query_string:
        url = f"{url}?{query_string}"

    return await api_client.make_request(url)


@mcp.tool()
async def get_status_codes_post(q: Optional[str] = None,
                              offset: Optional[int] = Defaults.SEARCH_START,
                              limit: Optional[int] = Defaults.API_LIMIT) -> Dict[str, Any]:
    """Search patent application status codes by supplying JSON payload

    Args:
        q: Search query string
        offset: Position to start from (default: 0)
        limit: Maximum number of results (default: 25)
    """
    data = {
        "q": q,
        "pagination": {"offset": offset, "limit": limit}
    }

    # Remove None values
    data = {k: v for k, v in data.items() if v is not None}

    url = f"{USPTO_API_BASE}/api/v1/patent/status-codes"
    return await api_client.make_request(url, method="POST", data=data)


# Bulk Dataset Endpoints

@mcp.tool()
async def search_datasets(q: Optional[str] = None,
                        product_title: Optional[str] = None,
                        product_description: Optional[str] = None,
                        product_short_name: Optional[str] = None,
                        offset: Optional[int] = Defaults.SEARCH_START,
                        limit: Optional[int] = Defaults.DATASET_LIMIT,
                        facets: Optional[str] = None,
                        include_files: Optional[bool] = True,
                        latest: Optional[bool] = False,
                        labels: Optional[str] = None,
                        categories: Optional[str] = None,
                        datasets: Optional[str] = None,
                        file_types: Optional[str] = None) -> Dict[str, Any]:
    """Search bulk datasets products

    Args:
        q: Search query for products
        product_title: Specific product title
        product_description: Specific product description
        product_short_name: Product identifier
        offset: Number of product records to skip (default: 0)
        limit: Number of product records to collect (default: 10)
        facets: Enable facets in response (true/false)
        include_files: Include product files in response (default: true)
        latest: Return only the latest product file (default: false)
        labels: List of tags to filter with, comma-separated
        categories: List of categories to filter with, comma-separated
        datasets: List of datasets to filter with, comma-separated
        file_types: List of file types to filter with, comma-separated
    """
    params = {
        "q": q,
        "productTitle": product_title,
        "productDescription": product_description,
        "productShortName": product_short_name,
        "offset": offset,
        "limit": limit,
        "facets": facets,
        "includeFiles": include_files,
        "latest": latest,
        "labels": labels,
        "categories": categories,
        "datasets": datasets,
        "fileTypes": file_types
    }

    query_string = api_client.build_query_string(params)
    url = f"{USPTO_API_BASE}/api/v1/datasets/products/search"
    if query_string:
        url = f"{url}?{query_string}"

    return await api_client.make_request(url)


@mcp.tool()
async def get_dataset_product(product_id: str,
                            file_data_from_date: Optional[str] = None,
                            file_data_to_date: Optional[str] = None,
                            offset: Optional[int] = None,
                            limit: Optional[int] = None,
                            include_files: Optional[bool] = None,
                            latest: Optional[bool] = None) -> Dict[str, Any]:
    """Get a specific product by its identifier

    Args:
        product_id: Product identifier (shortName)
        file_data_from_date: Filter files by from date (YYYY-MM-DD)
        file_data_to_date: Filter files by to date (YYYY-MM-DD)
        offset: Number of product file records to skip
        limit: Number of product file records to collect
        include_files: Include product files in response (true/false)
        latest: Return only the latest product file (true/false)
    """
    params = {
        "fileDataFromDate": file_data_from_date,
        "fileDataToDate": file_data_to_date,
        "offset": offset,
        "limit": limit,
        "includeFiles": include_files,
        "latest": latest
    }

    query_string = api_client.build_query_string(params)
    url = f"{USPTO_API_BASE}/api/v1/datasets/products/{product_id}"
    if query_string:
        url = f"{url}?{query_string}"

    return await api_client.make_request(url)


# =====================================================================
# Tools for Google Patents (BigQuery Public Datasets)
# =====================================================================


@mcp.tool()
async def google_search_patents(
    query: str,
    country: str = GooglePatentsCountries.US,
    limit: int = Defaults.SEARCH_LIMIT,
) -> Dict[str, Any]:
    """Search Google Patents Public Datasets using BigQuery

    Searches patent titles and abstracts for the specified query string.
    Returns patent publication number, title, abstract, dates, inventors, assignees, and classification codes.

    This tool provides access to 90M+ patent publications from 17+ countries via Google's BigQuery.

    Args:
        query: Search query string (searches titles and abstracts)
        country: Country code (US, EP, WO, JP, CN, KR, GB, DE, FR, CA, AU) - Default: US
        limit: Maximum number of results to return (max 500) - Default: 100

    Returns:
        Dictionary containing search results with patent metadata including:
        - publication_number: Patent publication number
        - title_localized: Patent title
        - abstract_localized: Patent abstract
        - publication_date: Publication date
        - filing_date: Filing date
        - grant_date: Grant date (if granted)
        - inventor_harmonized: List of inventors
        - assignee_harmonized: List of assignees/companies
        - cpc: CPC classification codes
        - ipc: IPC classification codes
        - family_id: Patent family ID
    """
    if limit > Defaults.SEARCH_LIMIT_MAX:
        return ApiError.validation_error(
            f"Limit cannot exceed {Defaults.SEARCH_LIMIT_MAX}", "limit"
        )

    if country not in GooglePatentsCountries.ALL:
        return ApiError.validation_error(
            f"Invalid country code. Must be one of: {', '.join(GooglePatentsCountries.ALL)}",
            "country",
        )

    try:
        result = await google_bq_client.search_patents(query, country, limit)
        return result
    except Exception as e:
        logger.error(f"Error searching Google Patents: {str(e)}")
        return ApiError.create(
            message=f"Failed to search Google Patents: {str(e)}", status_code=500
        )


@mcp.tool()
async def google_get_patent(publication_number: str) -> Dict[str, Any]:
    """Get full patent details from Google Patents by publication number

    Retrieves complete patent information including title, abstract, inventors,
    assignees, dates, classifications, and more from Google Patents Public Datasets.

    Args:
        publication_number: Patent publication number (e.g., US-9876543-B2, US-2020123456-A1)

    Returns:
        Dictionary containing complete patent details including all metadata fields
    """
    try:
        result = await google_bq_client.get_patent_by_number(publication_number)
        return result
    except Exception as e:
        logger.error(f"Error fetching patent {publication_number}: {str(e)}")
        return ApiError.create(
            message=f"Failed to fetch patent: {str(e)}", status_code=500
        )


@mcp.tool()
async def google_get_patent_claims(publication_number: str) -> Dict[str, Any]:
    """Get patent claims from Google Patents by publication number

    Retrieves all claims for a patent, including independent and dependent claims.
    Claims define the legal scope of protection for a patent.

    Args:
        publication_number: Patent publication number (e.g., US-9876543-B2)

    Returns:
        Dictionary containing:
        - publication_number: The patent number
        - claims_count: Total number of claims
        - claims: List of claim objects with claim_num and claim_text
    """
    try:
        result = await google_bq_client.get_patent_claims(publication_number)
        return result
    except Exception as e:
        logger.error(f"Error fetching claims for {publication_number}: {str(e)}")
        return ApiError.create(
            message=f"Failed to fetch claims: {str(e)}", status_code=500
        )


@mcp.tool()
async def google_get_patent_description(publication_number: str) -> Dict[str, Any]:
    """Get patent description from Google Patents by publication number

    Retrieves the full description/specification text of a patent, which contains
    the detailed technical disclosure of the invention.

    Args:
        publication_number: Patent publication number (e.g., US-9876543-B2)

    Returns:
        Dictionary containing:
        - publication_number: The patent number
        - description_text: Full description text
        - description_length: Length of description in characters
    """
    try:
        result = await google_bq_client.get_patent_description(publication_number)
        return result
    except Exception as e:
        logger.error(
            f"Error fetching description for {publication_number}: {str(e)}"
        )
        return ApiError.create(
            message=f"Failed to fetch description: {str(e)}", status_code=500
        )


@mcp.tool()
async def google_search_by_inventor(
    inventor_name: str,
    country: str = GooglePatentsCountries.US,
    limit: int = Defaults.SEARCH_LIMIT,
) -> Dict[str, Any]:
    """Search Google Patents by inventor name

    Finds patents where the specified inventor is listed as one of the inventors.

    Args:
        inventor_name: Inventor name to search for (partial match supported)
        country: Country code (US, EP, WO, JP, CN, etc.) - Default: US
        limit: Maximum number of results to return (max 500) - Default: 100

    Returns:
        Dictionary containing search results with patent metadata
    """
    if limit > Defaults.SEARCH_LIMIT_MAX:
        return ApiError.validation_error(
            f"Limit cannot exceed {Defaults.SEARCH_LIMIT_MAX}", "limit"
        )

    if country not in GooglePatentsCountries.ALL:
        return ApiError.validation_error(
            f"Invalid country code. Must be one of: {', '.join(GooglePatentsCountries.ALL)}",
            "country",
        )

    try:
        result = await google_bq_client.search_by_inventor(
            inventor_name, country, limit
        )
        return result
    except Exception as e:
        logger.error(f"Error searching by inventor: {str(e)}")
        return ApiError.create(
            message=f"Failed to search by inventor: {str(e)}", status_code=500
        )


@mcp.tool()
async def google_search_by_assignee(
    assignee_name: str,
    country: str = GooglePatentsCountries.US,
    limit: int = Defaults.SEARCH_LIMIT,
) -> Dict[str, Any]:
    """Search Google Patents by assignee/company name

    Finds patents assigned to a specific company or organization.

    Args:
        assignee_name: Assignee/company name to search for (partial match supported)
        country: Country code (US, EP, WO, JP, CN, etc.) - Default: US
        limit: Maximum number of results to return (max 500) - Default: 100

    Returns:
        Dictionary containing search results with patent metadata
    """
    if limit > Defaults.SEARCH_LIMIT_MAX:
        return ApiError.validation_error(
            f"Limit cannot exceed {Defaults.SEARCH_LIMIT_MAX}", "limit"
        )

    if country not in GooglePatentsCountries.ALL:
        return ApiError.validation_error(
            f"Invalid country code. Must be one of: {', '.join(GooglePatentsCountries.ALL)}",
            "country",
        )

    try:
        result = await google_bq_client.search_by_assignee(
            assignee_name, country, limit
        )
        return result
    except Exception as e:
        logger.error(f"Error searching by assignee: {str(e)}")
        return ApiError.create(
            message=f"Failed to search by assignee: {str(e)}", status_code=500
        )


@mcp.tool()
async def google_search_by_cpc(
    cpc_code: str,
    country: str = GooglePatentsCountries.US,
    limit: int = Defaults.SEARCH_LIMIT,
) -> Dict[str, Any]:
    """Search Google Patents by CPC classification code

    Finds patents classified under a specific Cooperative Patent Classification (CPC) code.
    CPC is an international patent classification system.

    Args:
        cpc_code: CPC code to search for (e.g., G06N3/08 for neural networks)
        country: Country code (US, EP, WO, JP, CN, etc.) - Default: US
        limit: Maximum number of results to return (max 500) - Default: 100

    Returns:
        Dictionary containing search results with patent metadata

    Examples:
        - G06N: Computing arrangements based on specific computational models
        - G06N3/08: Learning methods (neural networks)
        - H04L: Transmission of digital information
    """
    if limit > Defaults.SEARCH_LIMIT_MAX:
        return ApiError.validation_error(
            f"Limit cannot exceed {Defaults.SEARCH_LIMIT_MAX}", "limit"
        )

    if country not in GooglePatentsCountries.ALL:
        return ApiError.validation_error(
            f"Invalid country code. Must be one of: {', '.join(GooglePatentsCountries.ALL)}",
            "country",
        )

    try:
        result = await google_bq_client.search_by_cpc(cpc_code, country, limit)
        return result
    except Exception as e:
        logger.error(f"Error searching by CPC code: {str(e)}")
        return ApiError.create(
            message=f"Failed to search by CPC code: {str(e)}", status_code=500
        )


def main():
    """Initialize and run the server with stdio transport."""
    logger.info("Starting USPTO Patent MCP server with stdio transport")
    mcp.run(transport='stdio')


if __name__ == "__main__":
    main()
