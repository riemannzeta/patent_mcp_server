"""
USPTO Patent Search MCP Server

This file provides a Model Context Protocol (MCP) server that exposes tools for interacting with multiple USPTO APIs:

1. ppubs.uspto.gov - Provides full text patent documents, PDF downloads, and advanced search
2. api.uspto.gov - Provides metadata, continuity information, transactions, and assignments

The server uses stdio transport for command-line tools, following the MCP standard.
"""
import os
import json
import logging
import sys
from typing import Any, Dict, List, Optional, Union

from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("uspto_patent_tools")

# Set up logging
logging.basicConfig(
    level=logging.INFO, # for production
    #level=logging.DEBUG, # for debugging
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger('uspto_patent_mcp')

# Import USPTO client implementations
from patent_mcp_server.uspto.ppubs_uspto_gov import PpubsClient
from patent_mcp_server.uspto.api_uspto_gov import ApiUsptoClient

# Create client instances for each USPTO API
ppubs_client = PpubsClient()  # ppubs.uspto.gov module
api_client = ApiUsptoClient() # api.uspto.gov module

# =====================================================================
# Tools for ppubs.uspto.gov (full text patents and PDF downloads)
# =====================================================================

@mcp.tool()
async def ppubs_search_patents(
    query: str,
    start: Optional[int] = 0,
    limit: Optional[int] = 100,
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
        sources=["USPAT"],
        expand_plurals=expand_plurals,
        british_equivalents=british_equivalents
    )

@mcp.tool()
async def ppubs_search_applications(
    query: str,
    start: Optional[int] = 0,
    limit: Optional[int] = 100,
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
        sources=["US-PGPUB"],
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
    # Convert to string if integer
    patent_number = str(patent_number)
    
    # First search for the patent using specific field
    query = f'patentNumber:"{patent_number}"'
    logger.info(f"Searching for patent with query: {query}")
    
    result = await ppubs_client.run_query(
        query=query,
        sources=["USPAT"],
        limit=1
    )
    
    if result.get("error", False):
        return result
    
    # Handle different response structures
    if result.get("patents") and len(result["patents"]) > 0:
        patent = result["patents"][0]
        logger.info(f"Found patent: {patent.get('guid')}")
    elif result.get("docs") and len(result["docs"]) > 0:
        patent = result["docs"][0]
        logger.info(f"Found patent: {patent.get('guid')}")
    else:
        # Try alternative query format
        alternative_query = f'"{patent_number}".pn.'
        logger.info(f"No results found, trying alternative query: {alternative_query}")
        
        result = await ppubs_client.run_query(
            query=alternative_query,
            sources=["USPAT"],
            limit=1
        )
        
        if result.get("error", False):
            return result
            
        if not result.get("patents") and not result.get("docs"):
            return {
                "error": True,
                "message": f"Patent {patent_number} not found"
            }
            
        if result.get("patents") and len(result["patents"]) > 0:
            patent = result["patents"][0]
        elif result.get("docs") and len(result["docs"]) > 0:
            patent = result["docs"][0]
        else:
            return {
                "error": True,
                "message": f"Patent {patent_number} not found"
            }
    
    # Now get the full document
    return await ppubs_client.get_document(patent["guid"], patent["type"])

@mcp.tool()
async def ppubs_download_patent_pdf(patent_number: Union[str, int]) -> Dict[str, Any]:
    """Download a granted patent as PDF from ppubs.uspto.gov
    
    This tool provides access to the complete patent document as a PDF.
    
    Args:
        patent_number: The patent number (e.g., '7123456')
    """
    # Convert to string if integer
    patent_number = str(patent_number)
    
    # First search for the patent using specific field
    query = f'patentNumber:"{patent_number}"'
    logger.info(f"Searching for patent with query: {query}")
    
    result = await ppubs_client.run_query(
        query=query,
        sources=["USPAT"],
        limit=1
    )
    
    if result.get("error", False):
        return result
    
    # Handle different response structures
    if result.get("patents") and len(result["patents"]) > 0:
        patent = result["patents"][0]
    elif result.get("docs") and len(result["docs"]) > 0:
        patent = result["docs"][0]
    else:
        # Try alternative query format
        alternative_query = f'"{patent_number}".pn.'
        logger.info(f"No results found, trying alternative query: {alternative_query}")
        
        result = await ppubs_client.run_query(
            query=alternative_query,
            sources=["USPAT"],
            limit=1
        )
        
        if result.get("error", False):
            return result
            
        if not result.get("patents") and not result.get("docs"):
            return {
                "error": True,
                "message": f"Patent {patent_number} not found"
            }
            
        if result.get("patents") and len(result["patents"]) > 0:
            patent = result["patents"][0]
        elif result.get("docs") and len(result["docs"]) > 0:
            patent = result["docs"][0]
        else:
            return {
                "error": True,
                "message": f"Patent {patent_number} not found"
            }
    
    # Handle different field naming in the response
    image_location = patent.get("imageLocation", patent.get("document_structure", {}).get("image_location"))
    page_count = patent.get("pageCount", patent.get("document_structure", {}).get("page_count"))
    
    if not image_location or not page_count:
        return {
            "error": True,
            "message": "Missing image location or page count information"
        }
    
    # Download the PDF
    return await ppubs_client.download_image(
        patent["guid"],
        image_location,
        page_count,
        patent["type"]
    )

# =====================================================================
# Tools for api.uspto.gov (metadata)
# =====================================================================

USPTO_API_BASE = "https://api.uspto.gov"

@mcp.tool()
async def get_app(app_num: str) -> Dict[str, Any]:
    """Get patent application data
    
    Args:
        app_num: U.S. Patent Application Number, no / and no , (e.g. 14412875)
    """
    url = f"{USPTO_API_BASE}/api/v1/patent/applications/{app_num}"
    return await api_client.make_request(url)

@mcp.tool()
async def search_applications(q: Optional[str] = None, 
                            sort: Optional[str] = None, 
                            offset: Optional[int] = 0, 
                            limit: Optional[int] = 25, 
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
                                 offset: Optional[int] = 0, 
                                 limit: Optional[int] = 25,
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
                              offset: Optional[int] = 0, 
                              limit: Optional[int] = 25, 
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
                                   offset: Optional[int] = 0, 
                                   limit: Optional[int] = 25,
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
    url = f"{USPTO_API_BASE}/api/v1/patent/applications/{app_num}/meta-data"
    return await api_client.make_request(url)

@mcp.tool()
async def get_app_adjustment(app_num: str) -> Dict[str, Any]:
    """Get patent term adjustment data for an application
    
    Args:
        app_num: U.S. Patent Application Number (e.g., 14412875)
    """
    url = f"{USPTO_API_BASE}/api/v1/patent/applications/{app_num}/adjustment"
    return await api_client.make_request(url)

@mcp.tool()
async def get_app_assignment(app_num: str) -> Dict[str, Any]:
    """Get patent assignment data for an application
    
    Args:
        app_num: U.S. Patent Application Number (e.g., 14412875)
    """
    url = f"{USPTO_API_BASE}/api/v1/patent/applications/{app_num}/assignment"
    return await api_client.make_request(url)

@mcp.tool()
async def get_app_attorney(app_num: str) -> Dict[str, Any]:
    """Get attorney/agent data for an application
    
    Args:
        app_num: U.S. Patent Application Number (e.g., 14412875)
    """
    url = f"{USPTO_API_BASE}/api/v1/patent/applications/{app_num}/attorney"
    return await api_client.make_request(url)

@mcp.tool()
async def get_app_continuity(app_num: str) -> Dict[str, Any]:
    """Get continuity data for an application
    
    Args:
        app_num: U.S. Patent Application Number (e.g., 14412875)
    """
    url = f"{USPTO_API_BASE}/api/v1/patent/applications/{app_num}/continuity"
    return await api_client.make_request(url)

@mcp.tool()
async def get_app_foreign_priority(app_num: str) -> Dict[str, Any]:
    """Get foreign priority data for an application
    
    Args:
        app_num: U.S. Patent Application Number (e.g., 14412875)
    """
    url = f"{USPTO_API_BASE}/api/v1/patent/applications/{app_num}/foreign-priority"
    return await api_client.make_request(url)

@mcp.tool()
async def get_app_transactions(app_num: str) -> Dict[str, Any]:
    """Get transaction data for an application
    
    Args:
        app_num: U.S. Patent Application Number (e.g., 14412875)
    """
    url = f"{USPTO_API_BASE}/api/v1/patent/applications/{app_num}/transactions"
    return await api_client.make_request(url)

@mcp.tool()
async def get_app_documents(app_num: str) -> Dict[str, Any]:
    """Get document details for an application
    
    Args:
        app_num: U.S. Patent Application Number (e.g., 14412875)
    """
    url = f"{USPTO_API_BASE}/api/v1/patent/applications/{app_num}/documents"
    return await api_client.make_request(url)

@mcp.tool()
async def get_app_associated_documents(app_num: str) -> Dict[str, Any]:
    """Get associated documents metadata for an application
    
    Args:
        app_num: U.S. Patent Application Number (e.g., 14412875)
    """
    url = f"{USPTO_API_BASE}/api/v1/patent/applications/{app_num}/associated-documents"
    return await api_client.make_request(url)

# Status Code Endpoints

@mcp.tool()
async def get_status_codes(q: Optional[str] = None, 
                         offset: Optional[int] = 0, 
                         limit: Optional[int] = 25) -> Dict[str, Any]:
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
                              offset: Optional[int] = 0, 
                              limit: Optional[int] = 25) -> Dict[str, Any]:
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
                        offset: Optional[int] = 0, 
                        limit: Optional[int] = 10, 
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

def main():
    # Initialize and run the server with stdio transport
    logger.info("Starting USPTO Patent MCP server with stdio transport")
    mcp.run(transport='stdio')

if __name__ == "__main__":
    main()