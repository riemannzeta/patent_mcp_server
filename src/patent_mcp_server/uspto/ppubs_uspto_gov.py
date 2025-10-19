"""
USPTO Public Search Module (ppubs.uspto.gov)

This module provides tools for accessing the USPTO Public Search API at ppubs.uspto.gov,
which provides full text patent documents, patent PDFs, and advanced search capabilities.
"""

import os
import json
import asyncio
from typing import Any, Optional, Dict, List, Union
from datetime import datetime, timedelta
import httpx
import logging
from pathlib import Path
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryError
)

from patent_mcp_server.util.logging import LoggingTransport
from patent_mcp_server.util.errors import ApiError
from patent_mcp_server.config import config
from patent_mcp_server.constants import (
    Sources, Fields, PrintStatus, HTTPMethods, Defaults
)

# Set up logging
logger = logging.getLogger('ppubs_uspto_gov')


class PpubsClient:
    """Client for the USPTO Public Search API at ppubs.uspto.gov.

    This client provides access to full text patent documents, search capabilities,
    and PDF downloads from the USPTO Public Search system.

    Supports context manager protocol for proper resource cleanup.
    """

    def __init__(self):
        self.headers = {
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": config.USER_AGENT,
            "Origin": config.PPUBS_BASE_URL,
            "Referer": f"{config.PPUBS_BASE_URL}/pubwebapp/",
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
            timeout=config.REQUEST_TIMEOUT,
        )
        self.session = dict()
        self.case_id = None
        self.access_token = None
        self.search_query = None

        # Session caching
        self.session_expires_at: Optional[datetime] = None

        # Load search query template
        script_dir = Path(__file__).parent.parent
        search_query_path = script_dir / "json" / "search_query.json"
        with open(search_query_path, 'r') as f:
            self.search_query = json.load(f)

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        await self.close()

    async def get_session(self) -> Optional[Dict[str, Any]]:
        """Establish a session with USPTO Public Search.

        Uses caching to avoid unnecessary session creation.
        """
        # Check if cached session is still valid
        if config.ENABLE_CACHING and self.session_expires_at:
            if datetime.now() < self.session_expires_at:
                logger.info("Using cached session")
                return self.session

        logger.info("Establishing new session with USPTO Public Search")
        self.client.cookies = httpx.Cookies()

        try:
            # First request to get cookies
            response = await self.client.get(f"{config.PPUBS_BASE_URL}/pubwebapp/")

            # Create session
            url = f"{config.PPUBS_BASE_URL}/api/users/me/session"
            response = await self.client.post(
                url,
                json=-1,
                headers={
                    "X-Access-Token": "null",
                    "referer": f"{config.PPUBS_BASE_URL}/pubwebapp/",
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

            # Set session expiration
            if config.ENABLE_CACHING:
                self.session_expires_at = datetime.now() + timedelta(
                    minutes=config.SESSION_EXPIRY_MINUTES
                )

            logger.info(f"Session established with case ID: {self.case_id}")
            return self.session

        except Exception as e:
            logger.error(f"Error establishing session: {str(e)}")
            return None

    @retry(
        stop=stop_after_attempt(config.MAX_RETRIES),
        wait=wait_exponential(
            multiplier=config.RETRY_DELAY,
            min=config.RETRY_MIN_WAIT,
            max=config.RETRY_MAX_WAIT
        ),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True
    )
    async def make_request(self, method: str, url: str, **kwargs) -> Union[httpx.Response, Dict[str, Any]]:
        """Make a request with automatic retry for session expiration and network errors.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Target URL
            **kwargs: Additional arguments to pass to httpx

        Returns:
            httpx.Response object or error dictionary
        """
        try:
            response = await self.client.request(method, url, **kwargs)

            # Handle 403 (Session expired)
            if response.status_code == 403:
                logger.info("Session expired, refreshing")
                await self.get_session()
                response = await self.client.request(method, url, **kwargs)

            # Handle rate limiting
            if response.status_code == 429:
                wait_time = int(
                    response.headers.get(
                        "x-rate-limit-retry-after-seconds",
                        Defaults.RATE_LIMIT_RETRY_DELAY
                    )
                ) + 1
                logger.info(f"Rate limited, waiting {wait_time} seconds")
                await asyncio.sleep(wait_time)
                response = await self.client.request(method, url, **kwargs)

            # Log response body for debugging
            logger.debug(f"Response body for {method} {url}: {response.text}")

            return response

        except (httpx.TimeoutException, httpx.NetworkError) as e:
            logger.warning(f"Network error (will retry): {str(e)}")
            raise  # Let tenacity handle the retry
        except Exception as e:
            logger.error(f"Request error: {str(e)}")
            return ApiError.from_exception(e, f"Request to {url} failed")

    async def run_query(
        self,
        query: str,
        start: int = Defaults.SEARCH_START,
        limit: int = Defaults.SEARCH_LIMIT,
        sort: str = "date_publ desc",
        default_operator: str = "OR",
        sources: List[str] = None,
        expand_plurals: bool = True,
        british_equivalents: bool = True,
    ) -> Dict[str, Any]:
        """Run a search query against USPTO Public Search.

        Args:
            query: Search query string
            start: Starting position for results
            limit: Maximum number of results
            sort: Sort order
            default_operator: Default query operator (AND/OR)
            sources: List of source types to search
            expand_plurals: Whether to expand plural forms
            british_equivalents: Whether to include British spellings

        Returns:
            Dictionary containing search results or error
        """
        # Default sources
        if sources is None:
            sources = [Sources.PUBLISHED_APPLICATIONS, Sources.GRANTED_PATENTS, Sources.OCR]

        # Ensure we have a session
        if self.case_id is None:
            await self.get_session()

        logger.info(f"Running query: {query}")

        # Prepare query data
        data = self.search_query.copy()
        data["start"] = start
        data["pageCount"] = min(limit, Defaults.SEARCH_LIMIT_MAX)
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
        counts_url = f"{config.PPUBS_BASE_URL}/api/searches/counts"
        counts_response = await self.make_request(HTTPMethods.POST, counts_url, json=data["query"])

        if isinstance(counts_response, dict) and counts_response.get(Fields.ERROR, False):
            return counts_response

        # Execute search
        logger.info("Executing search query")
        search_url = f"{config.PPUBS_BASE_URL}/api/searches/searchWithBeFamily"
        search_response = await self.make_request(HTTPMethods.POST, search_url, json=data)

        if isinstance(search_response, dict) and search_response.get(Fields.ERROR, False):
            return search_response

        # Process response
        if search_response.status_code != 200:
            return ApiError.create(
                message=search_response.text,
                status_code=search_response.status_code
            )

        result = search_response.json()

        # Check for API errors
        if result.get(Fields.ERROR, None) is not None:
            error_obj = result[Fields.ERROR]
            return ApiError.create(
                message=error_obj.get(Fields.ERROR_MESSAGE, "Unknown error"),
                error_code=error_obj.get(Fields.ERROR_CODE)
            )

        # Log search results for debugging
        logger.debug(f"Search results: {json.dumps(result, indent=2, default=str)}")

        return result

    async def get_document(self, guid: str, source_type: str) -> Dict[str, Any]:
        """Get full document details by GUID.

        Args:
            guid: Document GUID
            source_type: Source type (USPAT, US-PGPUB, etc.)

        Returns:
            Dictionary containing document data or error
        """
        # Ensure we have a session
        if self.case_id is None:
            await self.get_session()

        logger.info(f"Getting document: {guid}")

        url = f"{config.PPUBS_BASE_URL}/api/patents/highlight/{guid}"
        params = {
            "queryId": 1,
            "source": source_type,
            "includeSections": True,
            "uniqueId": None,
        }

        response = await self.make_request(HTTPMethods.GET, url, params=params)

        if isinstance(response, dict) and response.get(Fields.ERROR, False):
            return response

        if response.status_code != 200:
            return ApiError.create(
                message=response.text,
                status_code=response.status_code
            )

        # Log document data for debugging
        document_data = response.json()
        logger.debug(f"Document data: {json.dumps(document_data, indent=2, default=str)}")

        return document_data

    async def _request_save(
        self,
        guid: str,
        image_location: str,
        page_count: int,
        document_type: str
    ) -> Union[str, Dict[str, Any]]:
        """Request generation of a PDF for download.

        Args:
            guid: Document GUID
            image_location: Path to document images
            page_count: Number of pages
            document_type: Document type

        Returns:
            Print job ID string or error dictionary
        """
        # Ensure we have a session
        if self.case_id is None:
            await self.get_session()

        logger.info(f"Requesting PDF save for: {guid}")

        page_keys = [
            f"{image_location}/{i:0>8}.tif"
            for i in range(1, page_count + 1)
        ]

        response = await self.client.post(
            f"{config.PPUBS_BASE_URL}/api/print/imageviewer",
            json={
                "caseId": self.case_id,
                "pageKeys": page_keys,
                "patentGuid": guid,
                "saveOrPrint": "save",
                "source": document_type,
            },
        )

        if response.status_code == 500:
            return ApiError.create(
                message=response.text,
                status_code=500
            )

        return response.text  # This is the print job ID

    async def download_image(
        self,
        guid: str,
        image_location: str,
        page_count: int,
        document_type: str
    ) -> Dict[str, Any]:
        """Download a patent document as PDF.

        Args:
            guid: Document GUID
            image_location: Path to document images
            page_count: Number of pages
            document_type: Document type

        Returns:
            Dictionary with PDF content (base64) or error
        """
        # Ensure we have a session
        if self.case_id is None:
            await self.get_session()

        logger.info(f"Downloading document images for: {guid}")

        try:
            # Request the document save
            print_job_id = await self._request_save(guid, image_location, page_count, document_type)

            if isinstance(print_job_id, dict) and print_job_id.get(Fields.ERROR, False):
                return print_job_id

            # Poll for completion
            while True:
                logger.info(f"Checking print job status: {print_job_id}")
                response = await self.client.post(
                    f"{config.PPUBS_BASE_URL}/api/print/print-process",
                    json=[print_job_id],
                )

                if response.status_code != 200:
                    return ApiError.create(
                        message=response.text,
                        status_code=response.status_code
                    )

                print_data = response.json()

                if print_data[0]["printStatus"] == PrintStatus.COMPLETED:
                    break

                await asyncio.sleep(Defaults.RETRY_DELAY)

            # Get the PDF name
            pdf_name = print_data[0]["pdfName"]

            # Download the PDF
            logger.info(f"Downloading PDF: {pdf_name}")
            request = self.client.build_request(
                HTTPMethods.GET,
                f"{config.PPUBS_BASE_URL}/api/internal/print/save/{pdf_name}",
            )

            response = await self.client.send(request, stream=True)

            if response.status_code != 200:
                return ApiError.create(
                    message="Failed to download PDF",
                    status_code=response.status_code
                )

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
            return ApiError.from_exception(e, "Document download failed")

    async def close(self):
        """Close the client connections and clean up resources."""
        logger.info("Closing ppubs client connections")
        await self.client.aclose()
