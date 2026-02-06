"""
USPTO Open Data Portal (ODP) API Module (api.uspto.gov)

This module provides tools for accessing the USPTO Open Data Portal API at api.uspto.gov,
which provides metadata, continuity information, transactions, and assignment data
for patents and applications.

Note: Requires an ODP API key obtained from https://data.uspto.gov ("My ODP").
The API endpoint is api.uspto.gov; data.uspto.gov is the web portal only.
"""

import os
from typing import Any, Optional, Dict, List, Union
import httpx
import logging
import urllib.parse
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
from patent_mcp_server.constants import HTTPMethods, Defaults

# Set up logging
logger = logging.getLogger('api_uspto_gov')


class ApiUsptoClient:
    """Client for the USPTO Open Data Portal (ODP) API at api.uspto.gov.

    This client provides access to patent and patent application metadata.
    Requires an ODP API key (register at https://data.uspto.gov).

    Supports context manager protocol for proper resource cleanup.
    """

    def __init__(self):
        self.headers = {
            "User-Agent": config.USER_AGENT,
            "X-API-KEY": config.USPTO_API_KEY if config.USPTO_API_KEY else ""
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

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        await self.close()

    def build_query_string(self, params: Dict[str, Any]) -> str:
        """Build a query string from a dictionary of parameters.

        Args:
            params: Dictionary of query parameters

        Returns:
            URL-encoded query string
        """
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
    async def make_request(
        self,
        url: str,
        method: str = HTTPMethods.GET,
        data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Make a request to the USPTO API with proper error handling and retry logic.

        Args:
            url: Request URL
            method: HTTP method (GET or POST)
            data: Request body data for POST requests

        Returns:
            Response JSON dictionary or error dictionary
        """
        headers = {
            "User-Agent": config.USER_AGENT,
            "X-API-KEY": config.USPTO_API_KEY if config.USPTO_API_KEY else ""
        }

        logger.info(f"Making {method} request to {url}")

        try:
            if method.upper() == HTTPMethods.GET:
                response = await self.client.get(
                    url,
                    headers=headers,
                    timeout=config.REQUEST_TIMEOUT
                )
            elif method.upper() == HTTPMethods.POST:
                headers["Content-Type"] = "application/json"
                response = await self.client.post(
                    url,
                    headers=headers,
                    json=data,
                    timeout=config.REQUEST_TIMEOUT
                )
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return ApiError.create(
                    message=f"Unsupported HTTP method: {method}",
                    status_code=400
                )

            response.raise_for_status()
            logger.info(f"Request successful: {response.status_code}")
            return response.json()

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            logger.error(f"HTTP error: {status_code} - {e.response.text}")

            try:
                error_json = e.response.json()
                return ApiError.from_http_error(
                    status_code=status_code,
                    response_text=e.response.text,
                    response_json=error_json
                )
            except:
                return ApiError.from_http_error(
                    status_code=status_code,
                    response_text=e.response.text
                )

        except (httpx.TimeoutException, httpx.NetworkError) as e:
            logger.warning(f"Network error (will retry): {str(e)}")
            raise  # Let tenacity handle the retry

        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return ApiError.from_exception(e, f"Request to {url} failed")

    async def close(self):
        """Close the client connections and clean up resources."""
        logger.info("Closing api.uspto.gov client connections")
        await self.client.aclose()
