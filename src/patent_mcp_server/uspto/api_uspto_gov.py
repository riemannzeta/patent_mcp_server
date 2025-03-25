"""
USPTO Open Data Protocol (ODP) API Module (api.uspto.gov)

This module provides tools for accessing the USPTO Open Data Protocol API at api.uspto.gov,
which provides metadata, continuity information, transactions, and assignment data
for patents and applications.
"""

from dotenv import load_dotenv
load_dotenv()
import os
from typing import Any, Optional, Dict, List, Union
import httpx
import logging
import urllib.parse
from patent_mcp_server.util.logging import LoggingTransport

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('api_uspto_gov')

# Constants
USPTO_API_BASE = "https://api.uspto.gov"
USER_AGENT = "patent-mcp-server/1.0"
USPTO_API_KEY = os.getenv("USPTO_API_KEY")

class ApiUsptoClient:
    """Client for the USPTO Open Data Protocol (ODP) API at api.uspto.gov.
    
    This client provides access to patent and patent application metadata.
    """

    def __init__(self):
        # Check if API key is available
        api_key = os.getenv("USPTO_API_KEY")
        
        self.headers = {
            "User-Agent": USER_AGENT,
            "X-API-KEY": api_key if api_key else ""  # Ensure we don't pass None
        }
        
        # Create a custom transport that logs all requests and responses
        transport = httpx.AsyncHTTPTransport()
        logging_transport = LoggingTransport(transport)
        
        self.client = httpx.AsyncClient(
            headers=self.headers,
            http2=True,
            follow_redirects=True,
            transport=logging_transport,
        )
    
    def build_query_string(self, params: Dict[str, Any]) -> str:
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
    
    async def make_request(self, url: str, method: str = "GET", data: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Make a request to the USPTO API with proper error handling."""
        # Check if API key is available
        api_key = os.getenv("USPTO_API_KEY")
        
        headers = {
            "User-Agent": USER_AGENT,
            "X-API-KEY": api_key if api_key else ""  # Ensure we don't pass None
        }
        
        logger.info(f"Making {method} request to {url}")
        
        try:
            if method.upper() == "GET":
                response = await self.client.get(url, headers=headers, timeout=30.0)
            elif method.upper() == "POST":
                headers["Content-Type"] = "application/json"
                response = await self.client.post(url, headers=headers, json=data, timeout=30.0)
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

    async def close(self):
        """Close the client connections."""
        await self.client.aclose()