"""
USPTO Open Data Portal (ODP) API Module (api.uspto.gov)

This module provides tools for accessing the USPTO Open Data Portal API at api.uspto.gov,
which provides metadata, continuity information, transactions, and assignment data
for patents and applications.

Note: Requires an ODP API key obtained from https://data.uspto.gov ("My ODP").
The API endpoint is api.uspto.gov; data.uspto.gov is the web portal only.
"""

import asyncio
import base64
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
from patent_mcp_server.util.errors import ApiError, retry_after_seconds
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

        if method.upper() not in (HTTPMethods.GET, HTTPMethods.POST):
            logger.error(f"Unsupported HTTP method: {method}")
            return ApiError.create(
                message=f"Unsupported HTTP method: {method}",
                status_code=400
            )

        try:
            for attempt in range(config.MAX_RETRIES):
                if method.upper() == HTTPMethods.GET:
                    response = await self.client.get(
                        url,
                        headers=headers,
                        timeout=config.REQUEST_TIMEOUT
                    )
                else:
                    headers["Content-Type"] = "application/json"
                    response = await self.client.post(
                        url,
                        headers=headers,
                        json=data,
                        timeout=config.REQUEST_TIMEOUT
                    )

                # api.uspto.gov rate-limits per key; wait and try again
                # rather than handing a burst of tool calls a 429 each.
                if response.status_code == 429 and attempt < config.MAX_RETRIES - 1:
                    delay = retry_after_seconds(response, attempt)
                    logger.warning(f"ODP API rate limit (429); retrying in {delay:.0f}s")
                    await asyncio.sleep(delay)
                    continue

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

    async def download_file(
        self,
        url: str,
        max_bytes: int = Defaults.MAX_BINARY_BYTES,
    ) -> Dict[str, Any]:
        """Fetch a binary document (a file-wrapper PDF) as base64.

        ODP answers a document URL with a 302 to a signed
        data-documents.uspto.gov link that is valid for 30 seconds; the
        client follows it (verified live 2026-09-26). The body is read in
        chunks and abandoned once it passes ``max_bytes``, since base64 of
        a multi-megabyte PDF would swamp the MCP response.

        Args:
            url: Document URL on api.uspto.gov
            max_bytes: Largest payload to return

        Returns:
            {"success": True, "content_type", "size_bytes", "content"} with
            the base64 body, or an error dictionary
        """
        headers = {
            "User-Agent": config.USER_AGENT,
            "X-API-KEY": config.USPTO_API_KEY if config.USPTO_API_KEY else ""
        }
        logger.info(f"Downloading {url}")

        try:
            request = self.client.build_request(HTTPMethods.GET, url, headers=headers)
            response = await self.client.send(request, stream=True)
            try:
                if response.status_code >= 400:
                    text = (await response.aread()).decode("utf-8", errors="replace")
                    logger.error(f"HTTP error: {response.status_code} - {text}")
                    return ApiError.from_http_error(
                        status_code=response.status_code, response_text=text
                    )

                declared = response.headers.get("content-length")
                if declared and declared.isdigit() and int(declared) > max_bytes:
                    return self._too_large(int(declared), max_bytes)

                chunks: List[bytes] = []
                size = 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > max_bytes:
                        return self._too_large(size, max_bytes)
                    chunks.append(chunk)
            finally:
                await response.aclose()

            content = b"".join(chunks)
            logger.info(f"Downloaded {size} bytes from {url}")
            return {
                "success": True,
                "content_type": response.headers.get("content-type", "application/pdf"),
                "size_bytes": size,
                "content": base64.b64encode(content).decode("ascii"),
            }

        except (httpx.TimeoutException, httpx.NetworkError) as e:
            logger.error(f"Network error downloading {url}: {str(e)}")
            return ApiError.from_exception(e, f"Download of {url} failed")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return ApiError.from_exception(e, f"Download of {url} failed")

    @staticmethod
    def _too_large(size: int, max_bytes: int) -> Dict[str, Any]:
        return ApiError.create(
            message=(
                f"Document is {size:,} bytes (over the {max_bytes:,}-byte "
                f"limit for base64 responses). Download it directly from "
                f"Patent Center instead, or raise the limit in code."
            ),
            error_code="RESPONSE_TOO_LARGE",
            details={"size_bytes": size, "max_bytes": max_bytes},
        )

    async def close(self):
        """Close the client connections and clean up resources."""
        logger.info("Closing api.uspto.gov client connections")
        await self.client.aclose()
