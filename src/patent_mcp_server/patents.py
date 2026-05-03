"""
USPTO Patent Search MCP Server

This file provides a Model Context Protocol (MCP) server that exposes tools for interacting
with multiple USPTO patent data APIs:

1. ppubs.uspto.gov - Full text patent documents, PDF downloads, and advanced search
2. api.uspto.gov - Metadata, continuity information, transactions, and assignments
3. PTAB API v3 - Patent Trial and Appeal Board proceedings and decisions
4. PatentsView API - UNAVAILABLE (shut down March 2026; data migrated to ODP bulk datasets)
5. Office Action APIs - UNAVAILABLE (decommissioned early 2026, pending ODP migration)

The server uses stdio transport for Claude Code/Cursor integration.

Version: 0.5.0 - USPTO-only focus
"""
import atexit
import json
import logging
import sys
from typing import Any, Dict, List, Optional, Union

from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError

from patent_mcp_server.config import config
from patent_mcp_server.constants import (
    Sources, Fields, Defaults, PatentsViewEndpoints
)
from patent_mcp_server.util.errors import ApiError, is_error
from patent_mcp_server.util.validation import validate_patent_number, validate_app_number
from patent_mcp_server.util.response import (
    ResponseEnvelope, check_and_truncate, estimate_tokens
)
from patent_mcp_server.resources import (
    get_cpc_section_info, get_cpc_subsection_info,
    get_status_code_info, get_all_status_codes,
    get_data_source_info, get_all_data_sources,
    get_search_syntax_guide, CPC_SECTIONS, DATA_SOURCES
)
from patent_mcp_server.prompts import get_prompt, list_prompts, PROMPTS
from patent_mcp_server.uspto.ppubs_uspto_gov import PpubsClient
from patent_mcp_server.uspto.api_uspto_gov import ApiUsptoClient
from patent_mcp_server.uspto.office_action_client import OfficeActionClient
from patent_mcp_server.uspto.enriched_citation_client import EnrichedCitationClient
from patent_mcp_server.patentsview.patentsview_client import PatentsViewClient

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
office_action_client = OfficeActionClient()
enriched_citation_client = EnrichedCitationClient()

# Create PatentsView client
patentsview_client = PatentsViewClient()


# Register cleanup handler
async def cleanup():
    """Clean up resources on shutdown."""
    logger.info("Shutting down USPTO Patent MCP server, cleaning up resources...")
    try:
        await ppubs_client.close()
        await api_client.close()
        await office_action_client.close()
        await enriched_citation_client.close()
        await patentsview_client.close()
        logger.info("Cleanup completed successfully")
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")


# Register cleanup with atexit (best effort for stdio shutdown)
def sync_cleanup():
    """Synchronous cleanup wrapper for atexit."""
    import asyncio
    try:
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                loop.create_task(cleanup())
                return
        except RuntimeError:
            pass

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
# MCP Resources - Static data accessible via @ mentions
# =====================================================================

@mcp.resource("patents://cpc/{code}")
async def resource_cpc_classification(code: str) -> str:
    """Get CPC classification code information.

    Returns details about a CPC (Cooperative Patent Classification) code
    including section, class, and subclass information.
    """
    if len(code) == 1:
        info = get_cpc_section_info(code)
    else:
        info = get_cpc_subsection_info(code)
    return json.dumps(info, indent=2)


@mcp.resource("patents://cpc")
async def resource_cpc_sections() -> str:
    """Get all CPC section overview.

    Returns summary of all 9 CPC sections (A-H, Y) with their titles
    and descriptions for patent classification reference.
    """
    sections = {
        code: {"title": data["title"], "description": data["description"]}
        for code, data in CPC_SECTIONS.items()
    }
    return json.dumps(sections, indent=2)


@mcp.resource("patents://status-codes")
async def resource_status_codes() -> str:
    """Get USPTO application status code definitions.

    Returns all status codes used in patent application tracking
    with descriptions and examination stages.
    """
    return json.dumps(get_all_status_codes(), indent=2)


@mcp.resource("patents://status-codes/{code}")
async def resource_status_code(code: str) -> str:
    """Get a specific USPTO status code definition."""
    return json.dumps(get_status_code_info(code), indent=2)


@mcp.resource("patents://sources")
async def resource_data_sources() -> str:
    """Get information about available patent data sources.

    Returns details about all integrated APIs including coverage,
    rate limits, authentication requirements, and best use cases.
    """
    return json.dumps(get_all_data_sources(), indent=2)


@mcp.resource("patents://sources/{source}")
async def resource_data_source(source: str) -> str:
    """Get information about a specific data source."""
    return json.dumps(get_data_source_info(source), indent=2)


@mcp.resource("patents://search-syntax")
async def resource_search_syntax() -> str:
    """Get search query syntax guide for all APIs.

    Returns documentation on query syntax for PPUBS, PatentsView,
    and ODP APIs with examples.
    """
    return get_search_syntax_guide()


# =====================================================================
# MCP Prompts - Workflow templates accessible via / commands
# =====================================================================

@mcp.prompt()
async def prior_art_search() -> str:
    """Guide for conducting a comprehensive prior art search.

    USE THIS PROMPT WHEN: You need to find existing patents and publications
    relevant to an invention for patentability assessment or invalidity analysis.
    """
    return get_prompt("prior_art_search")["content"]


@mcp.prompt()
async def patent_validity_analysis() -> str:
    """Guide for analyzing patent validity and prosecution history.

    USE THIS PROMPT WHEN: You need to assess the strength and validity
    of a patent by reviewing its prosecution history and any challenges.
    """
    return get_prompt("patent_validity")["content"]


@mcp.prompt()
async def competitor_portfolio_analysis() -> str:
    """Guide for analyzing a company's patent portfolio.

    USE THIS PROMPT WHEN: You need to understand a competitor's IP position,
    technology focus areas, and patent strategy.
    """
    return get_prompt("competitor_portfolio")["content"]


@mcp.prompt()
async def ptab_proceeding_research() -> str:
    """Guide for researching PTAB proceedings (IPR/PGR/CBM).

    USE THIS PROMPT WHEN: You need to research Patent Trial and Appeal Board
    proceedings, decisions, and outcomes for validity challenges.
    """
    return get_prompt("ptab_research")["content"]


@mcp.prompt()
async def freedom_to_operate() -> str:
    """Guide for freedom-to-operate (FTO) analysis.

    USE THIS PROMPT WHEN: You need to assess patent infringement risk
    for a product or technology before commercialization.
    """
    return get_prompt("freedom_to_operate")["content"]


@mcp.prompt()
async def patent_landscape() -> str:
    """Guide for patent landscape analysis.

    USE THIS PROMPT WHEN: You need to map the competitive patent environment
    in a technology area to identify trends and opportunities.
    """
    return get_prompt("patent_landscape")["content"]


# =====================================================================
# Helper Functions
# =====================================================================

async def _search_patent_by_number(patent_number: str) -> Dict[str, Any]:
    """Search for a patent by number and return the patent document metadata."""
    query = f'patentNumber:"{patent_number}"'
    logger.info(f"Searching for patent with query: {query}")

    result = await ppubs_client.run_query(
        query=query,
        sources=[Sources.GRANTED_PATENTS],
        limit=1
    )

    if is_error(result):
        return result

    patents = result.get(Fields.PATENTS, result.get(Fields.DOCS, []))

    if patents and len(patents) > 0:
        logger.info(f"Found patent: {patents[0].get(Fields.GUID)}")
        return {"success": True, "patent": patents[0]}

    # Try alternative query format
    alternative_query = f'"{patent_number}".pn.'
    logger.info(f"Trying alternative query: {alternative_query}")

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
# Diagnostic Tools
# =====================================================================

@mcp.tool()
async def check_api_status() -> Dict[str, Any]:
    """Check status and availability of all patent data sources.

    USE THIS TOOL WHEN: You encounter errors or want to verify which APIs
    are available and properly configured before starting research.

    Returns status of each data source including:
    - Configuration status (API keys, credentials)
    - Connection availability
    - Rate limit information where available
    """
    status = {
        "odp": {
            "name": "USPTO Open Data Portal",
            "configured": bool(config.USPTO_API_KEY),
            "api_key_set": bool(config.USPTO_API_KEY),
        },
        "ppubs": {
            "name": "Patent Public Search",
            "configured": True,
            "requires_auth": False,
        },
        "ptab": {
            "name": "PTAB Trial API",
            "configured": False,
            "status": "UNAVAILABLE",
            "note": (
                "The PTAB Trial API is not available on the USPTO Open Data "
                "Portal (api.uspto.gov). The legacy PTAB API at "
                "developer.uspto.gov was retired, and no PTAB endpoints are "
                "listed in the ODP Swagger catalog. Use ppubs_search_patents "
                "/ ppubs_get_full_document to locate PTAB-related documents, "
                "or download PTAB bulk data from https://developer.uspto.gov/data."
            ),
        },
        "patentsview": {
            "name": "PatentsView API",
            "configured": False,
            "status": "UNAVAILABLE",
            "note": (
                "PatentsView API (search.patentsview.org) was shut down on "
                "March 20, 2026. Data has been migrated to ODP as bulk "
                "downloadable datasets. Use ppubs_search_patents for patent "
                "search, odp_get_application for metadata, or "
                "odp_search_datasets to find PatentsView bulk datasets."
            ),
        },
        "office_actions": {
            "name": "Office Action APIs",
            "configured": False,
            "status": "UNAVAILABLE",
            "note": (
                "Legacy endpoints at developer.uspto.gov were decommissioned "
                "in early 2026. Migration to ODP (api.uspto.gov) is pending. "
                "Use odp_get_documents as a workaround."
            ),
        },
        "litigation": {
            "name": "Patent Litigation API",
            "configured": False,
            "status": "UNAVAILABLE",
            "note": (
                "The Patent Litigation API is not available on the USPTO "
                "Open Data Portal (api.uspto.gov) and is not listed in the "
                "ODP Swagger catalog. The OCE Patent Litigation dataset is "
                "distributed as a bulk download at "
                "https://www.uspto.gov/ip-policy/economic-research/research-"
                "datasets/patent-litigation-docket-reports-data."
            ),
        },
    }

    return {
        "success": True,
        "sources": status,
        "token_budget": {
            "max_response_tokens": config.MAX_RESPONSE_TOKENS,
            "truncation_enabled": config.TRUNCATE_LARGE_RESPONSES,
        }
    }


@mcp.tool()
async def get_cpc_info(cpc_code: str) -> Dict[str, Any]:
    """Look up CPC (Cooperative Patent Classification) code information.

    USE THIS TOOL WHEN: You need to understand what technology area a CPC
    code represents, or find related classification codes.

    Args:
        cpc_code: CPC code to look up (e.g., "G06" for computing, "G06N3/08" for neural networks)

    Returns:
        Classification details including section, title, and description.
        For section codes (A-H, Y), returns subsection list.
    """
    if len(cpc_code) == 1:
        return get_cpc_section_info(cpc_code)
    else:
        return get_cpc_subsection_info(cpc_code)


@mcp.tool()
async def get_status_code(code: str) -> Dict[str, Any]:
    """Look up USPTO application status code meaning.

    USE THIS TOOL WHEN: You encounter a status code in application data
    and need to understand what examination stage it represents.

    Args:
        code: Status code number (e.g., "30" for "Docketed New Case")

    Returns:
        Status code description and examination stage.
    """
    return get_status_code_info(code)


# =====================================================================
# PPUBS Tools - Full text patents and PDF downloads
# =====================================================================

@mcp.tool()
async def ppubs_search_patents(
    query: str,
    offset: int = 0,
    limit: int = 100,
    sort: str = "date_publ desc",
) -> Dict[str, Any]:
    """Search granted US patents in Patent Public Search (ppubs.uspto.gov).

    USE THIS TOOL WHEN: You need full-text search of US patents with daily
    updates, or need access to the most recent patent filings.

    PREFER OVER patentsview_search WHEN: You need the most current data
    (PPUBS updates daily vs PatentsView periodic updates).

    Args:
        query: Search query using USPTO syntax. Examples:
               - "machine learning" - searches all fields
               - TTL/"neural network" - title contains phrase
               - IN/Smith AND AN/IBM - inventor Smith, assignee IBM
               - CPC/G06N3/08 - CPC classification
        offset: Starting position for pagination (default: 0)
        limit: Maximum results to return (default: 100, max: 500)
        sort: Sort order (default: "date_publ desc")

    Returns:
        Normalized response with patent results including GUID, title,
        abstract, dates, inventors, and classification codes.
    """
    result = await ppubs_client.run_query(
        query=query,
        start=offset,
        limit=min(limit, 500),
        sort=sort,
        sources=[Sources.GRANTED_PATENTS],
    )

    if is_error(result):
        return result

    response = ResponseEnvelope.from_ppubs(result, offset, limit)
    return check_and_truncate(response)


@mcp.tool()
async def ppubs_search_applications(
    query: str,
    offset: int = 0,
    limit: int = 100,
    sort: str = "date_publ desc",
) -> Dict[str, Any]:
    """Search published US patent applications in Patent Public Search.

    USE THIS TOOL WHEN: You need to search pre-grant published applications
    (applications publish 18 months after filing, before grant).

    Args:
        query: Search query using USPTO syntax (same as ppubs_search_patents)
        offset: Starting position for pagination (default: 0)
        limit: Maximum results to return (default: 100, max: 500)
        sort: Sort order (default: "date_publ desc")

    Returns:
        Normalized response with application results.
    """
    result = await ppubs_client.run_query(
        query=query,
        start=offset,
        limit=min(limit, 500),
        sort=sort,
        sources=[Sources.PUBLISHED_APPLICATIONS],
    )

    if is_error(result):
        return result

    response = ResponseEnvelope.from_ppubs(result, offset, limit)
    return check_and_truncate(response)


@mcp.tool()
async def ppubs_get_full_document(guid: str, source_type: str) -> Dict[str, Any]:
    """Get complete patent document by GUID from PPUBS.

    USE THIS TOOL WHEN: You have a document GUID from search results
    and need the full patent text including all claims and description.

    Args:
        guid: Document GUID (e.g., "US-9876543-B2")
        source_type: Document type - "USPAT" for patents, "US-PGPUB" for applications

    Returns:
        Complete document with claims, description, drawings info, and metadata.
    """
    result = await ppubs_client.get_document(guid, source_type)

    if is_error(result):
        return result

    return check_and_truncate(result)


@mcp.tool()
async def ppubs_get_patent_by_number(patent_number: str) -> Dict[str, Any]:
    """Get a granted patent's full text by patent number.

    USE THIS TOOL WHEN: You know the patent number and need the complete
    document including claims, description, and all sections.

    Args:
        patent_number: Patent number without commas (e.g., "7123456" or "10000000")

    Returns:
        Complete patent document with full text of all sections.
    """
    try:
        patent_number = validate_patent_number(str(patent_number))
    except ValueError as e:
        return ApiError.validation_error(str(e), "patent_number")

    search_result = await _search_patent_by_number(patent_number)

    if is_error(search_result):
        return search_result

    patent = search_result["patent"]
    result = await ppubs_client.get_document(patent[Fields.GUID], patent[Fields.TYPE])

    if is_error(result):
        return result

    return check_and_truncate(result)


@mcp.tool()
async def ppubs_download_patent_pdf(patent_number: str) -> Dict[str, Any]:
    """Download a patent as PDF (base64 encoded).

    USE THIS TOOL WHEN: You need the official PDF document of a patent.
    Note: Claude Desktop may not fully support PDF display.

    Args:
        patent_number: Patent number without commas (e.g., "7123456")

    Returns:
        Dictionary with base64-encoded PDF data.
    """
    try:
        patent_number = validate_patent_number(str(patent_number))
    except ValueError as e:
        return ApiError.validation_error(str(e), "patent_number")

    search_result = await _search_patent_by_number(patent_number)

    if is_error(search_result):
        return search_result

    patent = search_result["patent"]
    return await ppubs_client.download_image(patent[Fields.GUID], patent[Fields.TYPE])


# =====================================================================
# ODP Tools - USPTO Open Data Portal (api.uspto.gov)
# =====================================================================

@mcp.tool()
async def odp_get_application(app_num: str) -> Dict[str, Any]:
    """Get patent application data from USPTO Open Data Portal.

    USE THIS TOOL WHEN: You need prosecution/file wrapper data for an
    application including status, dates, and basic metadata.

    Args:
        app_num: Application number without slashes or commas (e.g., "14412875")

    Returns:
        Application data including filing date, status, and basic info.
    """
    try:
        app_num = validate_app_number(str(app_num))
    except ValueError as e:
        return ApiError.validation_error(str(e), "app_num")

    url = f"{config.API_BASE_URL}/api/v1/patent/applications/{app_num}"
    result = await api_client.make_request(url)

    if is_error(result):
        return result

    return ResponseEnvelope.from_odp(result)


@mcp.tool()
async def odp_get_application_metadata(app_num: str) -> Dict[str, Any]:
    """Get detailed metadata for a patent application.

    USE THIS TOOL WHEN: You need comprehensive application metadata
    including examiner info, art unit, and detailed status.

    Args:
        app_num: Application number without slashes (e.g., "14412875")
    """
    try:
        app_num = validate_app_number(str(app_num))
    except ValueError as e:
        return ApiError.validation_error(str(e), "app_num")

    url = f"{config.API_BASE_URL}/api/v1/patent/applications/{app_num}/meta-data"
    result = await api_client.make_request(url)

    if is_error(result):
        return result

    return ResponseEnvelope.from_odp(result)


@mcp.tool()
async def odp_get_continuity(app_num: str) -> Dict[str, Any]:
    """Get patent family/continuity data (parent and child applications).

    USE THIS TOOL WHEN: You need to understand the patent family tree -
    parent applications, continuations, divisionals, and CIPs.

    Args:
        app_num: Application number without slashes (e.g., "14412875")

    Returns:
        Continuity data showing parent/child relationships and priority claims.
    """
    try:
        app_num = validate_app_number(str(app_num))
    except ValueError as e:
        return ApiError.validation_error(str(e), "app_num")

    url = f"{config.API_BASE_URL}/api/v1/patent/applications/{app_num}/continuity"
    result = await api_client.make_request(url)

    if is_error(result):
        return result

    return ResponseEnvelope.from_odp(result)


@mcp.tool()
async def odp_get_assignment(app_num: str) -> Dict[str, Any]:
    """Get patent assignment/ownership records.

    USE THIS TOOL WHEN: You need to know current and historical owners
    of a patent or application.

    Args:
        app_num: Application number without slashes (e.g., "14412875")
    """
    try:
        app_num = validate_app_number(str(app_num))
    except ValueError as e:
        return ApiError.validation_error(str(e), "app_num")

    url = f"{config.API_BASE_URL}/api/v1/patent/applications/{app_num}/assignment"
    return await api_client.make_request(url)


@mcp.tool()
async def odp_get_adjustment(app_num: str) -> Dict[str, Any]:
    """Get patent term adjustment (PTA) data.

    USE THIS TOOL WHEN: You need to calculate the actual expiration date
    of a patent accounting for USPTO delays.

    Args:
        app_num: Application number without slashes (e.g., "14412875")
    """
    try:
        app_num = validate_app_number(str(app_num))
    except ValueError as e:
        return ApiError.validation_error(str(e), "app_num")

    url = f"{config.API_BASE_URL}/api/v1/patent/applications/{app_num}/adjustment"
    return await api_client.make_request(url)


@mcp.tool()
async def odp_get_attorney(app_num: str) -> Dict[str, Any]:
    """Get attorney/agent of record for an application.

    Args:
        app_num: Application number without slashes (e.g., "14412875")
    """
    try:
        app_num = validate_app_number(str(app_num))
    except ValueError as e:
        return ApiError.validation_error(str(e), "app_num")

    url = f"{config.API_BASE_URL}/api/v1/patent/applications/{app_num}/attorney"
    return await api_client.make_request(url)


@mcp.tool()
async def odp_get_foreign_priority(app_num: str) -> Dict[str, Any]:
    """Get foreign priority claims for an application.

    USE THIS TOOL WHEN: You need to find priority claims to foreign
    applications that may affect the effective filing date.

    Args:
        app_num: Application number without slashes (e.g., "14412875")
    """
    try:
        app_num = validate_app_number(str(app_num))
    except ValueError as e:
        return ApiError.validation_error(str(e), "app_num")

    url = f"{config.API_BASE_URL}/api/v1/patent/applications/{app_num}/foreign-priority"
    return await api_client.make_request(url)


@mcp.tool()
async def odp_get_transactions(app_num: str) -> Dict[str, Any]:
    """Get prosecution transaction history for an application.

    USE THIS TOOL WHEN: You need the complete timeline of prosecution
    events including office actions, responses, and fee payments.

    Args:
        app_num: Application number without slashes (e.g., "14412875")
    """
    try:
        app_num = validate_app_number(str(app_num))
    except ValueError as e:
        return ApiError.validation_error(str(e), "app_num")

    url = f"{config.API_BASE_URL}/api/v1/patent/applications/{app_num}/transactions"
    result = await api_client.make_request(url)

    if is_error(result):
        return result

    return check_and_truncate(ResponseEnvelope.from_odp(result))


@mcp.tool()
async def odp_get_documents(app_num: str) -> Dict[str, Any]:
    """Get list of documents in the application file wrapper.

    Args:
        app_num: Application number without slashes (e.g., "14412875")
    """
    try:
        app_num = validate_app_number(str(app_num))
    except ValueError as e:
        return ApiError.validation_error(str(e), "app_num")

    url = f"{config.API_BASE_URL}/api/v1/patent/applications/{app_num}/documents"
    result = await api_client.make_request(url)

    if is_error(result):
        return result

    return check_and_truncate(ResponseEnvelope.from_odp(result))


@mcp.tool()
async def odp_search_applications(
    query: Optional[str] = None,
    application_number: Optional[str] = None,
    patent_number: Optional[str] = None,
    inventor_name: Optional[str] = None,
    assignee_name: Optional[str] = None,
    filing_date_from: Optional[str] = None,
    filing_date_to: Optional[str] = None,
    offset: int = 0,
    limit: int = 25,
) -> Dict[str, Any]:
    """Search patent applications in USPTO Open Data Portal.

    USE THIS TOOL WHEN: You need to search applications with filtering
    by applicant metadata, dates, or other criteria not available in PPUBS.

    Supports both simple queries and complex multi-field filtering.

    Args:
        query: General search query string
        application_number: Filter by application number
        patent_number: Filter by patent number
        inventor_name: Filter by inventor name
        assignee_name: Filter by assignee/applicant name
        filing_date_from: Filing date range start (YYYY-MM-DD)
        filing_date_to: Filing date range end (YYYY-MM-DD)
        offset: Starting position (default: 0)
        limit: Max results (default: 25)

    Returns:
        Normalized response with matching applications.
    """
    params = {"start": offset, "rows": limit}

    if query:
        params["q"] = query
    if application_number:
        params["applicationNumberText"] = application_number
    if patent_number:
        params["patentNumber"] = patent_number
    if inventor_name:
        params["inventorName"] = inventor_name
    if assignee_name:
        params["assigneeName"] = assignee_name
    if filing_date_from or filing_date_to:
        date_range = f"{filing_date_from or '*'},{filing_date_to or '*'}"
        params["appFilingDate"] = date_range

    query_string = api_client.build_query_string(params)
    url = f"{config.API_BASE_URL}/api/v1/patent/applications/search?{query_string}"

    result = await api_client.make_request(url)

    if is_error(result):
        return result

    # Upstream ODP search ignores the `rows` parameter and returns a fixed
    # page (~25 records). Enforce the caller's `limit` by post-slicing.
    if isinstance(result, dict) and isinstance(
        result.get("patentFileWrapperDataBag"), list
    ):
        result["patentFileWrapperDataBag"] = (
            result["patentFileWrapperDataBag"][:limit]
        )

    return check_and_truncate(ResponseEnvelope.from_odp(result, offset, limit))


@mcp.tool()
async def odp_search_datasets(
    query: Optional[str] = None,
    offset: int = 0,
    limit: int = 25,
) -> Dict[str, Any]:
    """Search USPTO bulk data products/datasets.

    USE THIS TOOL WHEN: You need to find bulk download datasets
    available from USPTO for large-scale analysis.

    Args:
        query: Search query for dataset names/descriptions
        offset: Starting position (default: 0)
        limit: Max results (default: 25)
    """
    params = {"start": offset, "rows": limit}
    if query:
        params["searchText"] = query

    query_string = api_client.build_query_string(params)
    url = f"{config.API_BASE_URL}/api/v1/datasets/products/search?{query_string}"

    return await api_client.make_request(url)


@mcp.tool()
async def odp_get_dataset(product_id: str) -> Dict[str, Any]:
    """Get details of a specific bulk dataset product.

    Args:
        product_id: Dataset product identifier
    """
    url = f"{config.API_BASE_URL}/api/v1/datasets/products/{product_id}"
    return await api_client.make_request(url)


# =====================================================================
# PTAB Tools - Patent Trial and Appeal Board
# =====================================================================

@mcp.tool()
async def ptab_search_proceedings(
    query: Optional[str] = None,
    trial_type: Optional[str] = None,
    patent_number: Optional[str] = None,
    party_name: Optional[str] = None,
    filing_date_from: Optional[str] = None,
    filing_date_to: Optional[str] = None,
    status: Optional[str] = None,
    offset: int = 0,
    limit: int = 25,
) -> Dict[str, Any]:
    """Search PTAB trial proceedings (IPR, PGR, CBM, derivation).

    USE THIS TOOL WHEN: You need to find patent validity challenges at
    the Patent Trial and Appeal Board.

    Trial types:
    - IPR: Inter Partes Review (most common, based on patents/publications)
    - PGR: Post-Grant Review (broader grounds, within 9 months of grant)
    - CBM: Covered Business Method (for financial method patents, sunsetted)
    - DER: Derivation proceedings

    Args:
        query: Full-text search query
        trial_type: Type of trial (IPR, PGR, CBM, DER)
        patent_number: Patent number being challenged
        party_name: Petitioner or patent owner name
        filing_date_from: Filing date range start (YYYY-MM-DD)
        filing_date_to: Filing date range end (YYYY-MM-DD)
        status: Proceeding status (Pending, Instituted, Terminated, FWD Entered)
        offset: Starting position (default: 0)
        limit: Max results (default: 25)

    Returns:
        Normalized response with matching proceedings.
    """
    return _ptab_unavailable()


@mcp.tool()
async def ptab_get_proceeding(proceeding_number: str) -> Dict[str, Any]:
    """Get details of a specific PTAB proceeding.

    IMPORTANT: The PTAB Trial API is not available on the USPTO Open Data
    Portal (api.uspto.gov). The legacy PTAB API on developer.uspto.gov was
    retired, and no PTAB endpoints are listed in the ODP Swagger catalog.

    Args:
        proceeding_number: Proceeding number (e.g., "IPR2023-00001")

    Returns:
        Proceeding details including parties, patent, status, and dates.
    """
    return _ptab_unavailable()


@mcp.tool()
async def ptab_get_documents(
    proceeding_number: str,
    document_type: Optional[str] = None,
    offset: int = 0,
    limit: int = 25,
) -> Dict[str, Any]:
    """Get documents filed in a PTAB proceeding.

    IMPORTANT: The PTAB Trial API is not available on the USPTO Open Data
    Portal (api.uspto.gov). The legacy PTAB API on developer.uspto.gov was
    retired, and no PTAB endpoints are listed in the ODP Swagger catalog.

    Args:
        proceeding_number: Proceeding number (e.g., "IPR2023-00001")
        document_type: Filter by type (petition, response, declaration, etc.)
        offset: Starting position (default: 0)
        limit: Max results (default: 25)
    """
    return _ptab_unavailable()


@mcp.tool()
async def ptab_search_decisions(
    query: Optional[str] = None,
    decision_type: Optional[str] = None,
    proceeding_number: Optional[str] = None,
    patent_number: Optional[str] = None,
    decision_date_from: Optional[str] = None,
    decision_date_to: Optional[str] = None,
    offset: int = 0,
    limit: int = 25,
) -> Dict[str, Any]:
    """Search PTAB trial decisions.

    IMPORTANT: The PTAB Trial API is not available on the USPTO Open Data
    Portal (api.uspto.gov). The legacy PTAB API on developer.uspto.gov was
    retired, and no PTAB endpoints are listed in the ODP Swagger catalog.

    Args:
        query: Full-text search in decision text
        decision_type: Type (institution, final, termination)
        proceeding_number: Filter by proceeding number
        patent_number: Filter by patent number
        decision_date_from: Date range start (YYYY-MM-DD)
        decision_date_to: Date range end (YYYY-MM-DD)
        offset: Starting position (default: 0)
        limit: Max results (default: 25)
    """
    return _ptab_unavailable()


@mcp.tool()
async def ptab_get_decision(decision_id: str) -> Dict[str, Any]:
    """Get details of a specific PTAB decision.

    IMPORTANT: The PTAB Trial API is not available on the USPTO Open Data
    Portal (api.uspto.gov). See ptab_search_proceedings for details.

    Args:
        decision_id: Decision identifier
    """
    return _ptab_unavailable()


@mcp.tool()
async def ptab_search_appeals(
    query: Optional[str] = None,
    application_number: Optional[str] = None,
    patent_number: Optional[str] = None,
    decision_date_from: Optional[str] = None,
    decision_date_to: Optional[str] = None,
    offset: int = 0,
    limit: int = 25,
) -> Dict[str, Any]:
    """Search ex parte appeal decisions.

    IMPORTANT: The PTAB Trial API is not available on the USPTO Open Data
    Portal (api.uspto.gov). The legacy PTAB API on developer.uspto.gov was
    retired, and no PTAB endpoints are listed in the ODP Swagger catalog.

    Args:
        query: Full-text search query
        application_number: Filter by application number
        patent_number: Filter by patent number
        decision_date_from: Date range start (YYYY-MM-DD)
        decision_date_to: Date range end (YYYY-MM-DD)
        offset: Starting position (default: 0)
        limit: Max results (default: 25)
    """
    return _ptab_unavailable()


@mcp.tool()
async def ptab_get_appeal(appeal_number: str) -> Dict[str, Any]:
    """Get details of a specific ex parte appeal decision.

    IMPORTANT: The PTAB Trial API is not available on the USPTO Open Data
    Portal (api.uspto.gov). See ptab_search_proceedings for details.

    Args:
        appeal_number: Appeal number
    """
    return _ptab_unavailable()


def _ptab_unavailable() -> Dict[str, Any]:
    """Shared API_UNAVAILABLE payload for all PTAB tools (see issue #16)."""
    return {
        "error": True,
        "message": (
            "The USPTO PTAB Trial API is not available on the Open Data "
            "Portal (api.uspto.gov). The legacy PTAB API at "
            "developer.uspto.gov was retired, and no PTAB endpoints are "
            "listed in the ODP Swagger catalog at "
            "https://data.uspto.gov/swagger/index.html. Use "
            "ppubs_search_patents / ppubs_get_full_document to locate "
            "PTAB-related documents, or download PTAB bulk data from "
            "https://developer.uspto.gov/data."
        ),
        "error_code": "API_UNAVAILABLE",
        "workaround": (
            "Use ppubs_search_patents(query) to locate PTAB-related "
            "documents, or download PTAB bulk data from "
            "https://developer.uspto.gov/data."
        ),
    }


# =====================================================================
# PatentsView Tools - Advanced search with disambiguation
# =====================================================================

@mcp.tool()
async def patentsview_search_patents(
    query: str,
    search_type: str = "any",
    offset: int = 0,
    limit: int = 100,
) -> Dict[str, Any]:
    """Search US patents with PatentsView full-text search.

    IMPORTANT: The PatentsView API (search.patentsview.org) was shut down on
    March 20, 2026. Use ppubs_search_patents for full-text patent search.
    PatentsView disambiguated data is available as bulk datasets on the
    USPTO Open Data Portal (use odp_search_datasets to find them).

    Args:
        query: Search terms for patent titles and abstracts
        search_type: Match type ("any", "all", "phrase")
        offset: Starting position (default: 0)
        limit: Max results (default: 100, max: 1000)
    """
    return {
        "error": True,
        "message": (
            "PatentsView API is no longer available. The PatentsView search API "
            "(search.patentsview.org) was shut down on March 20, 2026. "
            "Use ppubs_search_patents for full-text patent search. PatentsView "
            "disambiguated data is available as bulk datasets on the USPTO Open "
            "Data Portal (use odp_search_datasets to find them)."
        ),
        "error_code": "API_UNAVAILABLE",
        "workaround": "Use ppubs_search_patents(query) for patent search.",
    }


@mcp.tool()
async def patentsview_get_patent(patent_id: str) -> Dict[str, Any]:
    """Get detailed patent information from PatentsView.

    IMPORTANT: The PatentsView API (search.patentsview.org) was shut down on
    March 20, 2026. Use ppubs_get_patent_by_number for patent details.

    Args:
        patent_id: Patent ID/number (e.g., "7861317")
    """
    return {
        "error": True,
        "message": (
            "PatentsView API is no longer available. The PatentsView API "
            "(search.patentsview.org) was shut down on March 20, 2026. "
            "Use ppubs_get_patent_by_number for patent details, or "
            "odp_get_application for application metadata."
        ),
        "error_code": "API_UNAVAILABLE",
        "workaround": "Use ppubs_get_patent_by_number(patent_number) for patent details.",
    }


@mcp.tool()
async def patentsview_search_assignees(
    name: str,
    limit: int = 100,
) -> Dict[str, Any]:
    """Search for assignees (companies/organizations) with disambiguation.

    IMPORTANT: The PatentsView API (search.patentsview.org) was shut down on
    March 20, 2026. Use ppubs_search_patents with an assignee name query
    (e.g., AN/"company name") as a workaround.

    Args:
        name: Assignee/company name (partial match supported)
        limit: Max results (default: 100, max: 1000)
    """
    return {
        "error": True,
        "message": (
            "PatentsView API is no longer available. The PatentsView API "
            "(search.patentsview.org) was shut down on March 20, 2026. "
            "Use ppubs_search_patents with an assignee name query "
            '(e.g., query=\'AN/"company name"\') to search by assignee. '
            "Disambiguated assignee data is available as bulk datasets "
            "on the USPTO Open Data Portal (use odp_search_datasets)."
        ),
        "error_code": "API_UNAVAILABLE",
        "workaround": 'Use ppubs_search_patents(query=\'AN/"company name"\') to search by assignee.',
    }


@mcp.tool()
async def patentsview_get_assignee(assignee_id: str) -> Dict[str, Any]:
    """Get detailed assignee information by disambiguated ID.

    IMPORTANT: The PatentsView API (search.patentsview.org) was shut down on
    March 20, 2026. No direct replacement exists for disambiguated assignee
    lookups. Use odp_search_datasets to find PatentsView bulk datasets.

    Args:
        assignee_id: Disambiguated assignee ID from search results
    """
    return {
        "error": True,
        "message": (
            "PatentsView API is no longer available. The PatentsView API "
            "(search.patentsview.org) was shut down on March 20, 2026. "
            "No direct replacement exists for disambiguated assignee ID lookups. "
            "Disambiguated assignee data is available as bulk datasets on the "
            "USPTO Open Data Portal (use odp_search_datasets to find them)."
        ),
        "error_code": "API_UNAVAILABLE",
        "workaround": "Use odp_search_datasets to find PatentsView bulk disambiguated datasets.",
    }


@mcp.tool()
async def patentsview_search_inventors(
    name: str,
    limit: int = 100,
) -> Dict[str, Any]:
    """Search for inventors with disambiguation.

    IMPORTANT: The PatentsView API (search.patentsview.org) was shut down on
    March 20, 2026. Use ppubs_search_patents with an inventor name query
    (e.g., IN/"last name") as a workaround.

    Args:
        name: Inventor name (last name, or "First Last")
        limit: Max results (default: 100, max: 1000)
    """
    return {
        "error": True,
        "message": (
            "PatentsView API is no longer available. The PatentsView API "
            "(search.patentsview.org) was shut down on March 20, 2026. "
            "Use ppubs_search_patents with an inventor name query "
            '(e.g., query=\'IN/"inventor name"\') to search by inventor. '
            "Disambiguated inventor data is available as bulk datasets "
            "on the USPTO Open Data Portal (use odp_search_datasets)."
        ),
        "error_code": "API_UNAVAILABLE",
        "workaround": 'Use ppubs_search_patents(query=\'IN/"inventor name"\') to search by inventor.',
    }


@mcp.tool()
async def patentsview_get_inventor(inventor_id: str) -> Dict[str, Any]:
    """Get detailed inventor information by disambiguated ID.

    IMPORTANT: The PatentsView API (search.patentsview.org) was shut down on
    March 20, 2026. No direct replacement exists for disambiguated inventor
    lookups. Use odp_search_datasets to find PatentsView bulk datasets.

    Args:
        inventor_id: Disambiguated inventor ID from search results
    """
    return {
        "error": True,
        "message": (
            "PatentsView API is no longer available. The PatentsView API "
            "(search.patentsview.org) was shut down on March 20, 2026. "
            "No direct replacement exists for disambiguated inventor ID lookups. "
            "Disambiguated inventor data is available as bulk datasets on the "
            "USPTO Open Data Portal (use odp_search_datasets to find them)."
        ),
        "error_code": "API_UNAVAILABLE",
        "workaround": "Use odp_search_datasets to find PatentsView bulk disambiguated datasets.",
    }


@mcp.tool()
async def patentsview_get_claims(patent_id: str) -> Dict[str, Any]:
    """Get all claims text for a patent.

    IMPORTANT: The PatentsView API (search.patentsview.org) was shut down on
    March 20, 2026. Use ppubs_get_full_document to retrieve patent text
    including claims.

    Args:
        patent_id: Patent ID/number (e.g., "7861317")
    """
    return {
        "error": True,
        "message": (
            "PatentsView API is no longer available. The PatentsView API "
            "(search.patentsview.org) was shut down on March 20, 2026. "
            "Use ppubs_get_full_document to retrieve patent text including "
            "claims, or ppubs_get_patent_by_number to get the document GUID "
            "first."
        ),
        "error_code": "API_UNAVAILABLE",
        "workaround": "Use ppubs_get_patent_by_number then ppubs_get_full_document for patent claims.",
    }


@mcp.tool()
async def patentsview_get_description(patent_id: str) -> Dict[str, Any]:
    """Get patent detailed description/specification text.

    IMPORTANT: The PatentsView API (search.patentsview.org) was shut down on
    March 20, 2026. Use ppubs_get_full_document to retrieve the full patent
    specification.

    Args:
        patent_id: Patent ID/number (e.g., "7861317")
    """
    return {
        "error": True,
        "message": (
            "PatentsView API is no longer available. The PatentsView API "
            "(search.patentsview.org) was shut down on March 20, 2026. "
            "Use ppubs_get_full_document to retrieve the full patent "
            "specification, or ppubs_get_patent_by_number to get the "
            "document GUID first."
        ),
        "error_code": "API_UNAVAILABLE",
        "workaround": "Use ppubs_get_patent_by_number then ppubs_get_full_document for patent text.",
    }


@mcp.tool()
async def patentsview_search_by_cpc(
    cpc_code: str,
    limit: int = 100,
) -> Dict[str, Any]:
    """Search patents by CPC classification code.

    IMPORTANT: The PatentsView API (search.patentsview.org) was shut down on
    March 20, 2026. Use ppubs_search_patents with a CPC query
    (e.g., CPC/"G06N3/08") as a workaround.

    Args:
        cpc_code: CPC code (e.g., "G06N3/08" for neural networks)
        limit: Max results (default: 100, max: 1000)
    """
    return {
        "error": True,
        "message": (
            "PatentsView API is no longer available. The PatentsView API "
            "(search.patentsview.org) was shut down on March 20, 2026. "
            "Use ppubs_search_patents with a CPC classification query "
            '(e.g., query=\'CPC/"G06N3/08"\') to search by CPC code.'
        ),
        "error_code": "API_UNAVAILABLE",
        "workaround": 'Use ppubs_search_patents(query=\'CPC/"G06N3/08"\') to search by CPC.',
    }


@mcp.tool()
async def patentsview_lookup_cpc(cpc_code: str) -> Dict[str, Any]:
    """Look up CPC classification code details.

    IMPORTANT: The PatentsView API (search.patentsview.org) was shut down on
    March 20, 2026. Use get_cpc_info for CPC code descriptions.

    Args:
        cpc_code: CPC code (class "G06" or group "G06N3/08")
    """
    return {
        "error": True,
        "message": (
            "PatentsView API is no longer available. The PatentsView API "
            "(search.patentsview.org) was shut down on March 20, 2026. "
            "Use get_cpc_info for CPC classification code descriptions."
        ),
        "error_code": "API_UNAVAILABLE",
        "workaround": "Use get_cpc_info(cpc_code) for CPC classification details.",
    }


@mcp.tool()
async def patentsview_search_attorneys(
    name: str,
    limit: int = 100,
) -> Dict[str, Any]:
    """Search for patent attorneys/agents.

    IMPORTANT: The PatentsView API (search.patentsview.org) was shut down on
    March 20, 2026. Use odp_get_attorney with a specific application number
    to look up attorney information per application.

    Args:
        name: Attorney or firm name (partial match supported)
        limit: Maximum results to return (default: 100, max: 1000)
    """
    return {
        "error": True,
        "message": (
            "PatentsView API is no longer available. The PatentsView API "
            "(search.patentsview.org) was shut down on March 20, 2026. "
            "Use odp_get_attorney(app_num) to look up attorney information "
            "for a specific application."
        ),
        "error_code": "API_UNAVAILABLE",
        "workaround": "Use odp_get_attorney(app_num) for attorney info on specific applications.",
    }


@mcp.tool()
async def patentsview_get_attorney(attorney_id: str) -> Dict[str, Any]:
    """Get detailed attorney information by ID.

    IMPORTANT: The PatentsView API (search.patentsview.org) was shut down on
    March 20, 2026. Use odp_get_attorney with a specific application number
    to look up attorney information per application.

    Args:
        attorney_id: Attorney ID from search results
    """
    return {
        "error": True,
        "message": (
            "PatentsView API is no longer available. The PatentsView API "
            "(search.patentsview.org) was shut down on March 20, 2026. "
            "Use odp_get_attorney(app_num) to look up attorney information "
            "for a specific application."
        ),
        "error_code": "API_UNAVAILABLE",
        "workaround": "Use odp_get_attorney(app_num) for attorney info on specific applications.",
    }


@mcp.tool()
async def patentsview_lookup_ipc(ipc_code: str) -> Dict[str, Any]:
    """Look up IPC (International Patent Classification) code details.

    IMPORTANT: The PatentsView API (search.patentsview.org) was shut down on
    March 20, 2026. No direct replacement exists for IPC lookups. Use
    odp_search_datasets to find PatentsView bulk datasets containing IPC data.

    Args:
        ipc_code: IPC code (e.g., "G06F" for data processing)
    """
    return {
        "error": True,
        "message": (
            "PatentsView API is no longer available. The PatentsView API "
            "(search.patentsview.org) was shut down on March 20, 2026. "
            "No direct replacement exists for IPC code lookups. "
            "PatentsView bulk datasets on the USPTO Open Data Portal may "
            "contain IPC data (use odp_search_datasets to find them)."
        ),
        "error_code": "API_UNAVAILABLE",
        "workaround": "Use odp_search_datasets to find PatentsView bulk datasets with IPC data.",
    }


@mcp.tool()
async def patentsview_search_by_ipc(
    ipc_code: str,
    limit: int = 100,
) -> Dict[str, Any]:
    """Search patents by IPC (International Patent Classification) code.

    IMPORTANT: The PatentsView API (search.patentsview.org) was shut down on
    March 20, 2026. Use ppubs_search_patents with an IPC query as a workaround.

    Args:
        ipc_code: IPC code (e.g., "G06F" for data processing)
        limit: Maximum results to return (default: 100, max: 1000)
    """
    return {
        "error": True,
        "message": (
            "PatentsView API is no longer available. The PatentsView API "
            "(search.patentsview.org) was shut down on March 20, 2026. "
            "Use ppubs_search_patents with an IPC classification query "
            "to search by IPC code."
        ),
        "error_code": "API_UNAVAILABLE",
        "workaround": "Use ppubs_search_patents with an IPC query to search by classification.",
    }


# =====================================================================
# Office Action Tools
# =====================================================================

@mcp.tool()
async def get_office_action_text(
    application_number: str,
    mail_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Get full-text of office actions for an application.

    USE THIS TOOL WHEN: You need to read examiner rejections, requirements,
    and objections from prosecution.

    IMPORTANT: The legacy Office Action text APIs (developer.uspto.gov) were
    decommissioned in early 2026 and have NOT yet been migrated to the ODP.
    This tool is temporarily unavailable. Use odp_get_documents to list file
    wrapper documents (including office actions) and download them instead.

    Args:
        application_number: Application number (e.g., "16123456")
        mail_date: Optional filter by mail date (YYYY-MM-DD)

    Returns:
        Office action text including rejections and examiner comments.
    """
    return {
        "error": True,
        "message": (
            "Office Action text API is temporarily unavailable. The legacy "
            "endpoints at developer.uspto.gov were decommissioned in early 2026 "
            "and have not yet been migrated to the ODP (api.uspto.gov). "
            "Use odp_get_documents to list file wrapper documents including "
            "office actions, then download them from Patent Center."
        ),
        "error_code": "API_UNAVAILABLE",
        "workaround": "Use odp_get_documents(app_num) to find office action documents in the file wrapper.",
    }


@mcp.tool()
async def search_office_actions(
    query: Optional[str] = None,
    application_number: Optional[str] = None,
    examiner_name: Optional[str] = None,
    art_unit: Optional[str] = None,
    mail_date_from: Optional[str] = None,
    mail_date_to: Optional[str] = None,
    offset: int = 0,
    limit: int = 25,
) -> Dict[str, Any]:
    """Search office actions across applications.

    IMPORTANT: Temporarily unavailable — legacy endpoints decommissioned,
    ODP migration pending. Use odp_get_documents or odp_get_transactions instead.

    Args:
        query: Full-text search query
        application_number: Filter by application number
        examiner_name: Filter by examiner name
        art_unit: Filter by art unit number
        mail_date_from: Date range start (YYYY-MM-DD)
        mail_date_to: Date range end (YYYY-MM-DD)
        offset: Starting position (default: 0)
        limit: Max results (default: 25)
    """
    return {
        "error": True,
        "message": (
            "Office Action search API is temporarily unavailable. The legacy "
            "endpoints at developer.uspto.gov were decommissioned in early 2026 "
            "and have not yet been migrated to the ODP (api.uspto.gov). "
            "Use odp_get_transactions to search prosecution history, or "
            "odp_search_applications to find applications by examiner/art unit."
        ),
        "error_code": "API_UNAVAILABLE",
        "workaround": "Use odp_get_transactions(app_num) or odp_search_applications().",
    }


@mcp.tool()
async def get_office_action_citations(
    application_number: str,
    mail_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Get prior art citations from office actions.

    USE THIS TOOL WHEN: You need to see what references the examiner
    cited against an application.

    IMPORTANT: Temporarily unavailable — legacy endpoints decommissioned,
    ODP migration pending. Use get_enriched_citations as an alternative.

    Args:
        application_number: Application number
        mail_date: Optional filter by mail date (YYYY-MM-DD)

    Returns:
        Citations from Form PTO-892, PTO-1449, and office action text.
    """
    return {
        "error": True,
        "message": (
            "Office Action citations API is temporarily unavailable. The legacy "
            "endpoints at developer.uspto.gov were decommissioned in early 2026 "
            "and have not yet been migrated to the ODP (api.uspto.gov). "
            "Try get_enriched_citations for citation data, or use "
            "odp_get_documents to find PTO-892/PTO-1449 forms in the file wrapper."
        ),
        "error_code": "API_UNAVAILABLE",
        "workaround": "Use get_enriched_citations(patent_number) or odp_get_documents(app_num).",
    }


@mcp.tool()
async def get_office_action_rejections(
    application_number: str,
    mail_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Get rejection data from office actions.

    USE THIS TOOL WHEN: You need structured data about claim rejections
    including rejection type (102, 103, 112) and affected claims.

    IMPORTANT: Temporarily unavailable — legacy endpoints decommissioned,
    ODP migration pending. Use odp_get_documents to find office actions.

    Args:
        application_number: Application number
        mail_date: Optional filter by mail date (YYYY-MM-DD)

    Returns:
        Rejection data with claim-level details.
    """
    return {
        "error": True,
        "message": (
            "Office Action rejections API is temporarily unavailable. The legacy "
            "endpoints at developer.uspto.gov were decommissioned in early 2026 "
            "and have not yet been migrated to the ODP (api.uspto.gov). "
            "Use odp_get_documents to find office action documents in the file "
            "wrapper and download them from Patent Center for rejection details."
        ),
        "error_code": "API_UNAVAILABLE",
        "workaround": "Use odp_get_documents(app_num) to find office action documents.",
    }


# =====================================================================
# Citation Tools
# =====================================================================

@mcp.tool()
async def get_enriched_citations(
    patent_number: str,
    include_forward: bool = True,
    include_backward: bool = True,
) -> Dict[str, Any]:
    """Get enriched citation data for a patent.

    USE THIS TOOL WHEN: You need citation analysis including forward
    citations (who cites this patent) and backward (what this patent cites).

    IMPORTANT: The legacy Enriched Citation API (developer.uspto.gov) was
    decommissioned in early 2026 and has NOT yet been migrated to the ODP.
    This tool is temporarily unavailable. Use patentsview_get_patent for
    basic citation data instead.

    Args:
        patent_number: Patent number
        include_forward: Include forward citations (default: True)
        include_backward: Include backward citations (default: True)

    Returns:
        Enriched citation data with metrics.
    """
    return {
        "error": True,
        "message": (
            "Enriched Citation API is temporarily unavailable. The legacy "
            "endpoints at developer.uspto.gov were decommissioned in early 2026 "
            "and have not yet been migrated to the ODP (api.uspto.gov). "
            "Use patentsview_get_patent for basic citation data, or "
            "odp_get_documents to find PTO-892 citation forms in the file wrapper."
        ),
        "error_code": "API_UNAVAILABLE",
        "workaround": "Use patentsview_get_patent(patent_number) for citation data.",
    }


@mcp.tool()
async def search_citations(
    citing_patent: Optional[str] = None,
    cited_patent: Optional[str] = None,
    assignee: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    offset: int = 0,
    limit: int = 25,
) -> Dict[str, Any]:
    """Search citation records.

    IMPORTANT: Temporarily unavailable — legacy endpoints decommissioned,
    ODP migration pending. Use patentsview_search_patents instead.

    Args:
        citing_patent: Patent that is citing
        cited_patent: Patent being cited
        assignee: Filter by assignee name
        date_from: Date range start (YYYY-MM-DD)
        date_to: Date range end (YYYY-MM-DD)
        offset: Starting position (default: 0)
        limit: Max results (default: 25)
    """
    return {
        "error": True,
        "message": (
            "Enriched Citation search API is temporarily unavailable. The legacy "
            "endpoints at developer.uspto.gov were decommissioned in early 2026 "
            "and have not yet been migrated to the ODP (api.uspto.gov). "
            "Use patentsview_search_patents for citation-based patent searches."
        ),
        "error_code": "API_UNAVAILABLE",
        "workaround": "Use patentsview_search_patents(query) for citation searches.",
    }


@mcp.tool()
async def get_citation_metrics(patent_number: str) -> Dict[str, Any]:
    """Get citation metrics for a patent.

    USE THIS TOOL WHEN: You need quantitative citation analysis including
    forward/backward counts and citation age metrics.

    IMPORTANT: Temporarily unavailable — legacy endpoints decommissioned,
    ODP migration pending.

    Args:
        patent_number: Patent number
    """
    return {
        "error": True,
        "message": (
            "Citation metrics API is temporarily unavailable. The legacy "
            "endpoints at developer.uspto.gov were decommissioned in early 2026 "
            "and have not yet been migrated to the ODP (api.uspto.gov). "
            "Use patentsview_get_patent for basic citation counts."
        ),
        "error_code": "API_UNAVAILABLE",
        "workaround": "Use patentsview_get_patent(patent_number) for citation counts.",
    }


# =====================================================================
# Litigation Tools
# =====================================================================

def _litigation_unavailable() -> Dict[str, Any]:
    """Shared API_UNAVAILABLE payload for all litigation tools (see issue #16)."""
    return {
        "error": True,
        "message": (
            "The USPTO Patent Litigation API is not available on the Open "
            "Data Portal (api.uspto.gov). No litigation endpoints are "
            "listed in the ODP Swagger catalog at "
            "https://data.uspto.gov/swagger/index.html. The OCE Patent "
            "Litigation dataset (74,000+ district court cases) is "
            "distributed as a bulk download rather than a live API. "
            "Download it from https://www.uspto.gov/ip-policy/economic-"
            "research/research-datasets/patent-litigation-docket-reports-"
            "data, or use ppubs_search_patents as a partial workaround."
        ),
        "error_code": "API_UNAVAILABLE",
        "workaround": (
            "Download the OCE Patent Litigation bulk dataset from "
            "https://www.uspto.gov/ip-policy/economic-research/research-"
            "datasets/patent-litigation-docket-reports-data, or use "
            "ppubs_search_patents(query) for patent-level lookups."
        ),
    }


@mcp.tool()
async def search_litigation(
    query: Optional[str] = None,
    patent_number: Optional[str] = None,
    plaintiff: Optional[str] = None,
    defendant: Optional[str] = None,
    court: Optional[str] = None,
    filing_date_from: Optional[str] = None,
    filing_date_to: Optional[str] = None,
    offset: int = 0,
    limit: int = 25,
) -> Dict[str, Any]:
    """Search patent litigation cases (74,000+ district court records).

    IMPORTANT: The USPTO Patent Litigation API is not available on the Open
    Data Portal (api.uspto.gov) and is not listed in the ODP Swagger
    catalog. The OCE Patent Litigation dataset is distributed as bulk
    downloadable files rather than a live API.

    Args:
        query: Full-text search query
        patent_number: Filter by patent number
        plaintiff: Filter by plaintiff name
        defendant: Filter by defendant name
        court: Filter by court/district
        filing_date_from: Date range start (YYYY-MM-DD)
        filing_date_to: Date range end (YYYY-MM-DD)
        offset: Starting position (default: 0)
        limit: Max results (default: 25)
    """
    return _litigation_unavailable()


@mcp.tool()
async def get_litigation_case(case_id: str) -> Dict[str, Any]:
    """Get details of a specific litigation case.

    IMPORTANT: The USPTO Patent Litigation API is not available on the Open
    Data Portal. See search_litigation for details and workarounds.

    Args:
        case_id: Case identifier
    """
    return _litigation_unavailable()


@mcp.tool()
async def get_patent_litigation(patent_number: str) -> Dict[str, Any]:
    """Get all litigation involving a specific patent.

    IMPORTANT: The USPTO Patent Litigation API is not available on the Open
    Data Portal. See search_litigation for details and workarounds.

    Args:
        patent_number: Patent number
    """
    return _litigation_unavailable()


@mcp.tool()
async def get_party_litigation(
    party_name: str,
    role: Optional[str] = None,
    limit: int = 25,
) -> Dict[str, Any]:
    """Get litigation history for a company or individual.

    IMPORTANT: The USPTO Patent Litigation API is not available on the Open
    Data Portal. See search_litigation for details and workarounds.

    Args:
        party_name: Company or individual name
        role: Filter by role - "plaintiff", "defendant", or None for both
        limit: Max results (default: 25)
    """
    return _litigation_unavailable()


# =====================================================================
# Main entry point
# =====================================================================

def main():
    """Initialize and run the server with stdio transport."""
    logger.info("Starting USPTO Patent MCP server with stdio transport")
    mcp.run(transport='stdio')


if __name__ == "__main__":
    main()
