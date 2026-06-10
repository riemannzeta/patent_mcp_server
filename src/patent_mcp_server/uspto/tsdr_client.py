"""
USPTO TSDR (Trademark Status and Document Retrieval) API Module (tsdrapi.uspto.gov)

This module provides access to the official TSDR API for trademark case status,
prosecution documents, and mark images.

Base URL: https://tsdrapi.uspto.gov/ts/cd
Authentication: USPTO-API-KEY header. IMPORTANT: TSDR issues its OWN API key
(https://account.uspto.gov/profile/api-manager, "TSDR API" product). The ODP
key passes the gateway's auth check but the backend returns 404 for every
request ("BACKEND RESPONSE STATUS: 404") — if you see that, you need a TSDR
key, not an ODP key.

Rate limits (per API key, enforced by USPTO), peak hours 5am-10pm ET:
  - 60 requests/minute for general (JSON/XML) requests (120/min off-peak)
  - 4 requests/minute for PDF/ZIP document bundle downloads (12/min off-peak)
"""

import asyncio
import base64
import xml.etree.ElementTree as ET
from typing import Any, Optional, Dict, List, Union
import httpx
import logging
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from patent_mcp_server.util.logging import LoggingTransport
from patent_mcp_server.util.errors import ApiError
from patent_mcp_server.config import config
from patent_mcp_server.constants import Defaults, TrademarkDefaults

# Set up logging
logger = logging.getLogger('tsdr_client')

# Namespace of the TSDR document-list XML (verified live 2026-06-10)
DOCUMENT_LIST_NS = "urn:us:gov:doc:uspto:trademark"


class TSDRClient:
    """Client for the USPTO TSDR API at tsdrapi.uspto.gov.

    Provides trademark case status (JSON), document bundles (PDF), and
    mark images. Requires an API key sent as the USPTO-API-KEY header.

    Supports context manager protocol for proper resource cleanup.
    """

    def __init__(self):
        self.headers = {
            "User-Agent": config.USER_AGENT,
            "USPTO-API-KEY": config.TSDR_API_KEY if config.TSDR_API_KEY else ""
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
    async def _get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> Union[httpx.Response, Dict[str, Any]]:
        """Perform a GET with retry and 429 (rate limit) handling.

        TSDR enforces 60 req/min generally and 4 req/min for PDF/ZIP, so the
        429 path here will fire under normal document-heavy usage.

        Args:
            url: Request URL
            headers: Optional extra headers (merged over the client defaults)

        Returns:
            httpx.Response on success/HTTP error, or an ApiError dict on
            unexpected failure.
        """
        try:
            response = await self.client.get(
                url, headers=headers, timeout=config.REQUEST_TIMEOUT
            )

            if response.status_code == 429:
                wait_time = int(
                    response.headers.get(
                        "Retry-After",
                        Defaults.RATE_LIMIT_RETRY_DELAY
                    )
                ) + 1
                logger.info(f"TSDR rate limited, waiting {wait_time} seconds")
                await asyncio.sleep(wait_time)
                response = await self.client.get(
                    url, headers=headers, timeout=config.REQUEST_TIMEOUT
                )

            return response

        except (httpx.TimeoutException, httpx.NetworkError) as e:
            logger.warning(f"Network error (will retry): {str(e)}")
            raise  # Let tenacity handle the retry
        except Exception as e:
            logger.error(f"Request error: {str(e)}")
            return ApiError.from_exception(e, f"Request to {url} failed")

    @staticmethod
    def _auth_hint(status_code: int, response_text: str) -> Optional[str]:
        """Map TSDR auth failures to an actionable hint, or None."""
        if status_code == 401:
            return (
                "TSDR requires an API key in the USPTO-API-KEY header. Request "
                "one at https://account.uspto.gov/profile/api-manager (select "
                "the 'TSDR API' product) and set TSDR_API_KEY."
            )
        if status_code == 404 and "BACKEND RESPONSE STATUS" in (response_text or ""):
            return (
                "TSDR accepted the API key at its gateway but the backend "
                "returned 404 for the request. This is the signature of using "
                "an ODP API key — TSDR issues its own key. Request a TSDR key "
                "at https://account.uspto.gov/profile/api-manager (select the "
                "'TSDR API' product) and set TSDR_API_KEY. If you already use "
                "a TSDR key, the case may not exist."
            )
        return None

    async def _make_json_request(self, url: str) -> Dict[str, Any]:
        """Make a GET request expecting a JSON response.

        TSDR's /info endpoints return XML by default and JSON via content
        negotiation, so the Accept header is set explicitly.

        Args:
            url: Request URL

        Returns:
            Parsed JSON dictionary or error dictionary
        """
        logger.info(f"Making TSDR JSON request to {url}")

        response = await self._get(url, headers={"Accept": "application/json"})
        if isinstance(response, dict):
            return response  # Already an error dict

        if response.status_code != 200:
            try:
                error_json = response.json()
                error = ApiError.from_http_error(
                    status_code=response.status_code,
                    response_text=response.text,
                    response_json=error_json
                )
            except Exception:
                error = ApiError.from_http_error(
                    status_code=response.status_code,
                    response_text=response.text
                )
            hint = self._auth_hint(response.status_code, response.text)
            if hint:
                error["hint"] = hint
            return error

        try:
            return response.json()
        except Exception as e:
            return ApiError.from_exception(e, "TSDR returned non-JSON response")

    async def _make_binary_request(self, url: str, filename: str) -> Dict[str, Any]:
        """Make a GET request expecting binary content (PDF or image).

        Args:
            url: Request URL
            filename: Filename to report in the response

        Returns:
            Dictionary with base64-encoded content or error dictionary:
            {"success": True, "filename": ..., "content_type": ...,
             "content": <base64>, "size_bytes": N}
        """
        logger.info(f"Making TSDR binary request to {url}")

        response = await self._get(url)
        if isinstance(response, dict):
            return response  # Already an error dict

        if response.status_code != 200:
            error = ApiError.from_http_error(
                status_code=response.status_code,
                response_text=response.text
            )
            hint = self._auth_hint(response.status_code, response.text)
            if hint:
                error["hint"] = hint
            return error

        content = response.content
        if len(content) > TrademarkDefaults.MAX_BINARY_BYTES:
            # Full file wrappers run to tens of MB; base64 of that would
            # overwhelm the MCP response (and any LLM context window)
            return ApiError.create(
                message=(
                    f"Document bundle is {len(content):,} bytes, above the "
                    f"{TrademarkDefaults.MAX_BINARY_BYTES:,}-byte response "
                    "limit. Narrow the request with document_type and/or "
                    "date_from/date_to — use tsdr_list_trademark_documents "
                    "first to see what exists and pick a filter."
                ),
                status_code=413,
                error_code="RESPONSE_TOO_LARGE",
            )
        b64_content = base64.b64encode(content).decode('utf-8')

        return {
            "success": True,
            "filename": filename,
            "content_type": response.headers.get("content-type", "application/octet-stream"),
            "content": b64_content,
            "size_bytes": len(content),
        }

    def _status_url(
        self,
        serial_number: Optional[str],
        registration_number: Optional[str]
    ) -> Union[str, Dict[str, Any]]:
        """Build the case-status URL for exactly one identifier.

        Returns the URL string, or an ApiError dict if identifiers are invalid.
        """
        if bool(serial_number) == bool(registration_number):
            return ApiError.validation_error(
                "Provide exactly one of serial_number or registration_number",
                "serial_number"
            )
        # /info returns XML by default; JSON comes via the Accept header
        if serial_number:
            return f"{config.TSDR_BASE_URL}/casestatus/sn{serial_number}/info"
        return f"{config.TSDR_BASE_URL}/casestatus/rn{registration_number}/info"

    async def get_case_status(
        self,
        serial_number: Optional[str] = None,
        registration_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get trademark case status by serial number or registration number.

        Args:
            serial_number: 8-digit application serial number
            registration_number: Registration number

        Returns:
            Parsed TSDR status JSON or error dictionary
        """
        url = self._status_url(serial_number, registration_number)
        if isinstance(url, dict):
            return url
        return await self._make_json_request(url)

    @staticmethod
    def _parse_document_list_xml(xml_text: str) -> Dict[str, Any]:
        """Parse the TSDR document-list XML into a list of dicts.

        The /casedocs/{caseid}/info endpoint serves XML only (it answers
        406 to Accept: application/json — verified live 2026-06-10). The
        response is a flat <DocumentList><Document>...</Document>... tree
        in the urn:us:gov:doc:uspto:trademark namespace; each Document's
        child elements become dict keys (PageMediaTypeList collapses to a
        list of media type names).

        Args:
            xml_text: Raw XML response body

        Returns:
            {"results": [...], "total": N} or error dictionary
        """
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            return ApiError.from_exception(e, "Failed to parse TSDR document list XML")

        ns = {"tm": DOCUMENT_LIST_NS}
        results: List[Dict[str, Any]] = []
        for doc in root.findall("tm:Document", ns):
            record: Dict[str, Any] = {}
            for child in doc:
                tag = child.tag.split("}", 1)[-1]  # strip namespace
                if tag == "PageMediaTypeList":
                    record[tag] = [el.text for el in child]
                else:
                    record[tag] = child.text
            results.append(record)

        return {"results": results, "total": len(results)}

    async def list_case_documents(self, serial_number: str) -> Dict[str, Any]:
        """List prosecution document metadata for a trademark case.

        Returns document descriptions, types, and dates WITHOUT downloading
        content, so it is not subject to the 4 req/min PDF rate limit. Use
        this to find what exists before downloading a filtered bundle.

        Args:
            serial_number: 8-digit application serial number

        Returns:
            {"results": [...], "total": N} or error dictionary
        """
        url = f"{config.TSDR_BASE_URL}/casedocs/sn{serial_number}/info"

        response = await self._get(url)
        if isinstance(response, dict):
            return response  # Already an error dict

        if response.status_code != 200:
            error = ApiError.from_http_error(
                status_code=response.status_code,
                response_text=response.text
            )
            hint = self._auth_hint(response.status_code, response.text)
            if hint:
                error["hint"] = hint
            return error

        return self._parse_document_list_xml(response.text)

    async def download_case_documents(
        self,
        serial_number: str,
        document_type: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """Download the prosecution document bundle for a trademark as PDF.

        NOTE: TSDR limits PDF/ZIP downloads to 4 requests/minute per API key.

        Args:
            serial_number: 8-digit application serial number
            document_type: Optional document type filter (e.g., "OOA" for
                outgoing office actions, "SPE" for specimens)
            date_from: Optional start date filter (YYYY-MM-DD)
            date_to: Optional end date filter (YYYY-MM-DD)

        Returns:
            Dictionary with base64-encoded PDF content or error
        """
        params = [f"sn={serial_number}"]
        if document_type:
            params.append(f"type={document_type}")
        if date_from:
            params.append(f"fromDate={date_from}")
        if date_to:
            params.append(f"toDate={date_to}")

        url = f"{config.TSDR_BASE_URL}/casedocs/bundle.pdf?{'&'.join(params)}"
        return await self._make_binary_request(url, f"tm-{serial_number}-documents.pdf")

    async def get_mark_image(self, serial_number: str) -> Dict[str, Any]:
        """Get the mark image (drawing) for a trademark.

        Args:
            serial_number: 8-digit application serial number

        Returns:
            Dictionary with base64-encoded image content or error
        """
        url = f"{config.TSDR_BASE_URL}/rawImage/{serial_number}"
        return await self._make_binary_request(url, f"tm-{serial_number}-mark")

    async def close(self):
        """Close the client connections and clean up resources."""
        logger.info("Closing TSDR client connections")
        await self.client.aclose()
