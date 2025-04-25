"""
USPTO Public Search Module (ppubs.uspto.gov)

This module provides tools for accessing the USPTO Public Search API at ppubs.uspto.gov,
which provides full text patent documents, patent PDFs, and advanced search capabilities.
"""

import os
import json
import asyncio
from typing import Any, Optional, Dict, List, Union
import httpx
import logging
from pathlib import Path
from patent_mcp_server.util.logging import LoggingTransport

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('ppubs_uspto_gov')

# Constants
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
BASE_URL = "https://ppubs.uspto.gov"

class PpubsClient:
    """Client for the USPTO Public Search API at ppubs.uspto.gov.
    
    This client provides access to full text patent documents, search capabilities, 
    and PDF downloads from the USPTO Public Search system.
    """
    
    def __init__(self):
        self.headers = {
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": USER_AGENT,
            "Origin": BASE_URL,
            "Referer": f"{BASE_URL}/pubwebapp/",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "Priority": "u=1, i",
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
        self.session = dict()
        self.case_id = None
        self.access_token = None
        self.search_query = None
        
        # Load search query template
        script_dir = Path(__file__).parent.parent
        search_query_path = script_dir / "json" / "search_query.json"
        with open(search_query_path, 'r') as f:
            self.search_query = json.load(f)

    async def get_session(self):
        """Establish a session with USPTO Public Search."""
        logger.info("Establishing new session with USPTO Public Search")
        self.client.cookies = httpx.Cookies()
        
        # First request to get cookies
        response = await self.client.get(f"{BASE_URL}/pubwebapp/")
        
        # Create session
        url = f"{BASE_URL}/api/users/me/session"
        response = await self.client.post(
            url,
            json=-1,
            headers={
                "X-Access-Token": "null",
                "referer": f"{BASE_URL}/pubwebapp/",
            },
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to establish session: {response.status_code} - {response.text}")
            return None
            
        # Log response body for debugging
        logger.debug(f"Session response body: {response.text}")
        
        self.session = response.json()
        self.case_id = self.session["userCase"]["caseId"]
        self.access_token = response.headers["X-Access-Token"]
        self.client.headers["X-Access-Token"] = self.access_token
        
        logger.info(f"Session established with case ID: {self.case_id}")
        return self.session

    async def make_request(self, method, url, **kwargs):
        """Make a request with automatic retry for session expiration."""
        try:
            response = await self.client.request(method, url, **kwargs)
            
            # Handle 403 (Session expired)
            if response.status_code == 403:
                logger.info("Session expired, refreshing")
                await self.get_session()
                response = await self.client.request(method, url, **kwargs)
                
            # Handle rate limiting
            if response.status_code == 429:
                wait_time = int(response.headers.get("x-rate-limit-retry-after-seconds", 5)) + 1
                logger.info(f"Rate limited, waiting {wait_time} seconds")
                await asyncio.sleep(wait_time)
                response = await self.client.request(method, url, **kwargs)
                
            # Log response body for debugging
            logger.debug(f"Response body for {method} {url}: {response.text}")
            
            return response
            
        except Exception as e:
            logger.error(f"Request error: {str(e)}")
            return {
                "error": True,
                "message": f"Error: {str(e)}"
            }

    async def run_query(
        self,
        query,
        start=0,
        limit=500,
        sort="date_publ desc",
        default_operator="OR",
        sources=["US-PGPUB", "USPAT", "USOCR"],
        expand_plurals=True,
        british_equivalents=True,
    ) -> Dict[str, Any]:
        """Run a search query against USPTO Public Search."""
        # Ensure we have a session
        if self.case_id is None:
            await self.get_session()
            
        logger.info(f"Running query: {query}")
        
        # Prepare query data
        data = self.search_query.copy()
        data["start"] = start
        data["pageCount"] = limit
        data["sort"] = sort
        data["query"]["caseId"] = self.case_id
        data["query"]["op"] = default_operator
        data["query"]["q"] = query
        data["query"]["queryName"] = query
        data["query"]["userEnteredQuery"] = query
        data["query"]["databaseFilters"] = [
            {"databaseName": s, "countryCodes": []} for s in sources
        ]
        data["query"]["plurals"] = expand_plurals
        data["query"]["britishEquivalents"] = british_equivalents
        
        # Get counts first
        logger.info("Getting search counts")
        counts_url = f"{BASE_URL}/api/searches/counts"
        counts_response = await self.make_request("POST", counts_url, json=data["query"])
        
        if isinstance(counts_response, dict) and counts_response.get("error", False):
            return counts_response
            
        # Execute search
        logger.info("Executing search query")
        search_url = f"{BASE_URL}/api/searches/searchWithBeFamily"
        search_response = await self.make_request("POST", search_url, json=data)
        
        if isinstance(search_response, dict) and search_response.get("error", False):
            return search_response
            
        # Process response
        if search_response.status_code != 200:
            return {
                "error": True,
                "status_code": search_response.status_code,
                "message": search_response.text
            }
            
        result = search_response.json()
        
        # Check for API errors
        if result.get("error", None) is not None:
            return {
                "error": True,
                "errorCode": result["error"]["errorCode"],
                "message": result["error"]["errorMessage"]
            }
            
        # Log search results for debugging
        logger.debug(f"Search results: {json.dumps(result, indent=2, default=str)}")
        
        return result

    async def get_document(self, guid, source_type) -> Dict[str, Any]:
        """Get full document details by GUID."""
        # Ensure we have a session
        if self.case_id is None:
            await self.get_session()
            
        logger.info(f"Getting document: {guid}")
        
        url = f"{BASE_URL}/api/patents/highlight/{guid}"
        params = {
            "queryId": 1,
            "source": source_type,
            "includeSections": True,
            "uniqueId": None,
        }
        
        response = await self.make_request("GET", url, params=params)
        
        if isinstance(response, dict) and response.get("error", False):
            return response
            
        if response.status_code != 200:
            return {
                "error": True,
                "status_code": response.status_code,
                "message": response.text
            }
            
        # Log document data for debugging
        document_data = response.json()
        logger.debug(f"Document data: {json.dumps(document_data, indent=2, default=str)}")
        
        return document_data

    async def _request_save(self, guid, image_location, page_count, document_type):
        """Request generation of a PDF for download."""
        # Ensure we have a session
        if self.case_id is None:
            await self.get_session()
            
        logger.info(f"Requesting PDF save for: {guid}")
        
        page_keys = [
            f"{image_location}/{i:0>8}.tif"
            for i in range(1, page_count + 1)
        ]
        
        response = await self.client.post(
            f"{BASE_URL}/api/print/imageviewer",
            json={
                "caseId": self.case_id,
                "pageKeys": page_keys,
                "patentGuid": guid,
                "saveOrPrint": "save",
                "source": document_type,
            },
        )
        
        if response.status_code == 500:
            return {
                "error": True,
                "status_code": 500,
                "message": response.text
            }
            
        return response.text  # This is the print job ID

    async def download_image(self, guid, image_location, page_count, document_type) -> Dict[str, Any]:
        """Download a patent document as PDF."""
        # Ensure we have a session
        if self.case_id is None:
            await self.get_session()
            
        logger.info(f"Downloading document images for: {guid}")
        
        try:
            # Request the document save
            print_job_id = await self._request_save(guid, image_location, page_count, document_type)
            
            if isinstance(print_job_id, dict) and print_job_id.get("error", False):
                return print_job_id
                
            # Poll for completion
            while True:
                logger.info(f"Checking print job status: {print_job_id}")
                response = await self.client.post(
                    f"{BASE_URL}/api/print/print-process",
                    json=[print_job_id],
                )
                
                if response.status_code != 200:
                    return {
                        "error": True,
                        "status_code": response.status_code,
                        "message": response.text
                    }
                    
                print_data = response.json()
                
                if print_data[0]["printStatus"] == "COMPLETED":
                    break
                    
                await asyncio.sleep(1)
                
            # Get the PDF name
            pdf_name = print_data[0]["pdfName"]
            
            # Download the PDF
            logger.info(f"Downloading PDF: {pdf_name}")
            request = self.client.build_request(
                "GET",
                f"{BASE_URL}/api/internal/print/save/{pdf_name}",
            )
            
            response = await self.client.send(request, stream=True)
            
            if response.status_code != 200:
                return {
                    "error": True,
                    "status_code": response.status_code,
                    "message": "Failed to download PDF"
                }
                
            # Return the PDF as base64
            content = await response.aread()
            import base64
            b64_content = base64.b64encode(content).decode('utf-8')
            
            return {
                "success": True,
                "filename": f"{guid}.pdf",
                "content_type": "application/pdf",
                "content": b64_content
            }
            
        except Exception as e:
            logger.error(f"Error downloading document: {str(e)}")
            return {
                "error": True,
                "message": f"Error: {str(e)}"
            }
    
    async def close(self):
        """Close the client connections."""
        await self.client.aclose()