from dotenv import load_dotenv
load_dotenv()
import os
from typing import Any, Optional, Dict, List, Union
import httpx
from mcp.server.fastmcp import FastMCP
import logging
import urllib.parse

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('uspto_api')

# Initialize FastMCP patent server
mcp = FastMCP("patent")

# Constants
USPTO_API_BASE = "https://api.uspto.gov"
USER_AGENT = "patent-mcp-server/1.0"

def build_query_string(params: Dict[str, Any]) -> str:
    """Build a query string from a dictionary of parameters."""
    query_parts = []
    for key, value in params.items():
        if value is None:
            continue
            
        if isinstance(value, bool):
            value = str(value).lower()
        elif isinstance(value, (list, tuple)):
            value = ",".join(str(v) for v in value)
            
        query_parts.append(f"{key}={urllib.parse.quote(str(value))}")
        
    return "&".join(query_parts)

async def make_request(url: str, method: str = "GET", data: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
    """Make a request to the USPTO API with proper error handling."""
    headers = {
        "User-Agent": USER_AGENT,
        "X-API-KEY": os.getenv("PATENTS_MCP_SERVER_ODP_API_KEY")
    }
    
    logger.info(f"Making {method} request to {url}")
    
    async with httpx.AsyncClient() as client:
        try:
            if method.upper() == "GET":
                response = await client.get(url, headers=headers, timeout=30.0)
            elif method.upper() == "POST":
                headers["Content-Type"] = "application/json"
                response = await client.post(url, headers=headers, json=data, timeout=30.0)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return None
                
            response.raise_for_status()
            logger.info(f"Request successful: {response.status_code}")
            return response.json()
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            logger.error(f"HTTP error: {status_code} - {e.response.text}")
            
            try:
                error_json = e.response.json()
                return {
                    "error": True,
                    "status_code": status_code,
                    "message": error_json.get("error", e.response.text),
                    "details": error_json.get("errorDetails", None)
                }
            except:
                return {
                    "error": True,
                    "status_code": status_code,
                    "message": e.response.text
                }
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {
                "error": True,
                "message": f"Error: {str(e)}"
            }

# Patent Application Endpoints

@mcp.tool()
async def get_app(app_num: str) -> Dict[str, Any]:
    """Get patent application data
    
    Args:
        app_num: U.S. Patent Application Number, no / and no , (e.g. 14412875)
    """
    url = f"{USPTO_API_BASE}/api/v1/patent/applications/{app_num}"
    return await make_request(url)

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
    
    query_string = build_query_string(params)
    url = f"{USPTO_API_BASE}/api/v1/patent/applications/search"
    if query_string:
        url = f"{url}?{query_string}"
    
    return await make_request(url)

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
    return await make_request(url, method="POST", data=data)

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
    
    query_string = build_query_string(params)
    url = f"{USPTO_API_BASE}/api/v1/patent/applications/search/download"
    if query_string:
        url = f"{url}?{query_string}"
    
    return await make_request(url)

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
    return await make_request(url, method="POST", data=data)

@mcp.tool()
async def get_app_metadata(app_num: str) -> Dict[str, Any]:
    """Get patent application metadata
    
    Args:
        app_num: U.S. Patent Application Number (e.g., 14412875)
    """
    url = f"{USPTO_API_BASE}/api/v1/patent/applications/{app_num}/meta-data"
    return await make_request(url)

@mcp.tool()
async def get_app_adjustment(app_num: str) -> Dict[str, Any]:
    """Get patent term adjustment data for an application
    
    Args:
        app_num: U.S. Patent Application Number (e.g., 14412875)
    """
    url = f"{USPTO_API_BASE}/api/v1/patent/applications/{app_num}/adjustment"
    return await make_request(url)

@mcp.tool()
async def get_app_assignment(app_num: str) -> Dict[str, Any]:
    """Get patent assignment data for an application
    
    Args:
        app_num: U.S. Patent Application Number (e.g., 14412875)
    """
    url = f"{USPTO_API_BASE}/api/v1/patent/applications/{app_num}/assignment"
    return await make_request(url)

@mcp.tool()
async def get_app_attorney(app_num: str) -> Dict[str, Any]:
    """Get attorney/agent data for an application
    
    Args:
        app_num: U.S. Patent Application Number (e.g., 14412875)
    """
    url = f"{USPTO_API_BASE}/api/v1/patent/applications/{app_num}/attorney"
    return await make_request(url)

@mcp.tool()
async def get_app_continuity(app_num: str) -> Dict[str, Any]:
    """Get continuity data for an application
    
    Args:
        app_num: U.S. Patent Application Number (e.g., 14412875)
    """
    url = f"{USPTO_API_BASE}/api/v1/patent/applications/{app_num}/continuity"
    return await make_request(url)

@mcp.tool()
async def get_app_foreign_priority(app_num: str) -> Dict[str, Any]:
    """Get foreign priority data for an application
    
    Args:
        app_num: U.S. Patent Application Number (e.g., 14412875)
    """
    url = f"{USPTO_API_BASE}/api/v1/patent/applications/{app_num}/foreign-priority"
    return await make_request(url)

@mcp.tool()
async def get_app_transactions(app_num: str) -> Dict[str, Any]:
    """Get transaction data for an application
    
    Args:
        app_num: U.S. Patent Application Number (e.g., 14412875)
    """
    url = f"{USPTO_API_BASE}/api/v1/patent/applications/{app_num}/transactions"
    return await make_request(url)

@mcp.tool()
async def get_app_documents(app_num: str) -> Dict[str, Any]:
    """Get document details for an application
    
    Args:
        app_num: U.S. Patent Application Number (e.g., 14412875)
    """
    url = f"{USPTO_API_BASE}/api/v1/patent/applications/{app_num}/documents"
    return await make_request(url)

@mcp.tool()
async def get_app_associated_documents(app_num: str) -> Dict[str, Any]:
    """Get associated documents metadata for an application
    
    Args:
        app_num: U.S. Patent Application Number (e.g., 14412875)
    """
    url = f"{USPTO_API_BASE}/api/v1/patent/applications/{app_num}/associated-documents"
    return await make_request(url)

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
    
    query_string = build_query_string(params)
    url = f"{USPTO_API_BASE}/api/v1/patent/status-codes"
    if query_string:
        url = f"{url}?{query_string}"
    
    return await make_request(url)

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
    return await make_request(url, method="POST", data=data)

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
    
    query_string = build_query_string(params)
    url = f"{USPTO_API_BASE}/api/v1/datasets/products/search"
    if query_string:
        url = f"{url}?{query_string}"
    
    return await make_request(url)

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
    
    query_string = build_query_string(params)
    url = f"{USPTO_API_BASE}/api/v1/datasets/products/{product_id}"
    if query_string:
        url = f"{url}?{query_string}"
    
    return await make_request(url)

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')