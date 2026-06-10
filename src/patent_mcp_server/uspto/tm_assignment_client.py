"""
USPTO Trademark Assignment Search Module

Searches recorded trademark assignment (ownership transfer) records,
covering the USPTO assignment database (1955-present).

BACKEND STATUS (2026-06-10): The legacy Trademark Assignment Search API at
assignment-api.uspto.gov was migrated to the Open Data Portal around April
2026, but the exact ODP endpoint could not be verified from this environment
(no network access to uspto.gov hosts). This client therefore probes at
runtime:
  1. ODP first: GET {API_BASE_URL}/api/v1/trademark/assignment/search
     (X-API-KEY auth, JSON responses)
  2. On 404/501, falls back to the legacy XML API:
     GET {TM_ASSIGNMENT_BASE_URL}/trademark/basicSearch (no auth, XML)
The working backend is cached per client instance. Once the live location is
confirmed, prune the dead path and update this docstring.
"""

import xml.etree.ElementTree as ET
from typing import Any, Optional, Dict, List, Union
import httpx
import logging
import urllib.parse
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from patent_mcp_server.util.logging import LoggingTransport
from patent_mcp_server.util.errors import ApiError
from patent_mcp_server.config import config
from patent_mcp_server.constants import TrademarkDefaults

# Set up logging
logger = logging.getLogger('tm_assignment_client')

# ODP candidate path — confirmed at implementation time only as the documented
# migration target family; verify against https://data.uspto.gov swagger.
ODP_SEARCH_PATH = "/api/v1/trademark/assignment/search"
LEGACY_SEARCH_PATH = "/trademark/basicSearch"


class TmAssignmentClient:
    """Client for trademark assignment search (ODP with legacy fallback).

    Supports context manager protocol for proper resource cleanup.
    """

    def __init__(self):
        self.headers = {
            "User-Agent": config.USER_AGENT,
            "X-API-KEY": config.USPTO_API_KEY if config.USPTO_API_KEY else ""
        }

        # Which backend answered last: None (unprobed), "odp", or "legacy"
        self._backend: Optional[str] = None

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
    async def _get(self, url: str) -> Union[httpx.Response, Dict[str, Any]]:
        """Perform a GET with retry; returns the response or an error dict."""
        try:
            return await self.client.get(url, timeout=config.REQUEST_TIMEOUT)
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            logger.warning(f"Network error (will retry): {str(e)}")
            raise  # Let tenacity handle the retry
        except Exception as e:
            logger.error(f"Request error: {str(e)}")
            return ApiError.from_exception(e, f"Request to {url} failed")

    @staticmethod
    def _build_filters(
        serial_number: Optional[str],
        registration_number: Optional[str],
        assignee_name: Optional[str],
        assignor_name: Optional[str],
    ) -> Dict[str, str]:
        """Collect the non-empty filters into a dict; empty dict means none."""
        filters = {
            "serial_number": serial_number,
            "registration_number": registration_number,
            "assignee_name": assignee_name,
            "assignor_name": assignor_name,
        }
        return {k: v for k, v in filters.items() if v}

    def _parse_legacy_xml(self, xml_text: str) -> Dict[str, Any]:
        """Parse the legacy assignment-api XML response.

        The legacy API returns Solr-style XML:
        <response><result numFound="N"><doc>...fields...</doc></result></response>
        where each <doc> contains typed children (<str>, <arr>, <int>, <date>)
        keyed by a "name" attribute.

        Args:
            xml_text: Raw XML response body

        Returns:
            {"results": [...], "total": N} or error dictionary
        """
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            return ApiError.from_exception(e, "Failed to parse legacy assignment XML")

        result_el = root.find(".//result")
        if result_el is None:
            return {"results": [], "total": 0}

        try:
            total = int(result_el.get("numFound", "0"))
        except ValueError:
            total = 0

        results: List[Dict[str, Any]] = []
        for doc in result_el.findall("doc"):
            record: Dict[str, Any] = {}
            for child in doc:
                name = child.get("name")
                if not name:
                    continue
                if child.tag == "arr":
                    record[name] = [el.text for el in child]
                else:
                    record[name] = child.text
            results.append(record)

        return {"results": results, "total": total}

    async def search_assignments(
        self,
        serial_number: Optional[str] = None,
        registration_number: Optional[str] = None,
        assignee_name: Optional[str] = None,
        assignor_name: Optional[str] = None,
        offset: int = 0,
        limit: int = TrademarkDefaults.SEARCH_LIMIT,
    ) -> Dict[str, Any]:
        """Search trademark assignment records.

        At least one filter is required. Tries ODP first, then falls back to
        the legacy XML API; the working backend is cached on the instance.

        Args:
            serial_number: Trademark application serial number
            registration_number: Trademark registration number
            assignee_name: Assignee (new owner) name
            assignor_name: Assignor (previous owner) name
            offset: Pagination offset
            limit: Maximum results

        Returns:
            {"results": [...], "total": N, "backend": "odp"|"legacy"} or error
        """
        filters = self._build_filters(
            serial_number, registration_number, assignee_name, assignor_name
        )
        if not filters:
            return ApiError.create(
                message=(
                    "At least one filter is required: serial_number, "
                    "registration_number, assignee_name, or assignor_name"
                ),
                status_code=400,
                error_code="MISSING_FILTER"
            )

        if self._backend != "legacy":
            result = await self._search_odp(filters, offset, limit)
            # 404/501 means the ODP endpoint isn't there — try legacy.
            if not (
                result.get("error", False) is True
                and result.get("status_code") in (404, 501)
            ):
                self._backend = "odp"
                result["backend"] = "odp"
                return result
            logger.info("ODP trademark assignment endpoint unavailable; falling back to legacy API")

        result = await self._search_legacy(filters, offset, limit)
        if result.get("error", False) is not True:
            self._backend = "legacy"
            result["backend"] = "legacy"
        return result

    async def _search_odp(
        self,
        filters: Dict[str, str],
        offset: int,
        limit: int,
    ) -> Dict[str, Any]:
        """Query the ODP trademark assignment endpoint (JSON)."""
        # ODP search APIs use Lucene-style q= filtering
        clauses = []
        if "serial_number" in filters:
            clauses.append(f'applicationNumberText:{filters["serial_number"]}')
        if "registration_number" in filters:
            clauses.append(f'registrationNumber:{filters["registration_number"]}')
        if "assignee_name" in filters:
            clauses.append(f'assigneeName:"{filters["assignee_name"]}"')
        if "assignor_name" in filters:
            clauses.append(f'assignorName:"{filters["assignor_name"]}"')
        q = " AND ".join(clauses)

        params = urllib.parse.urlencode({"q": q, "offset": offset, "limit": limit})
        url = f"{config.API_BASE_URL}{ODP_SEARCH_PATH}?{params}"

        response = await self._get(url)
        if isinstance(response, dict):
            return response  # Already an error dict

        if response.status_code != 200:
            try:
                error_json = response.json()
                return ApiError.from_http_error(
                    status_code=response.status_code,
                    response_text=response.text,
                    response_json=error_json
                )
            except Exception:
                return ApiError.from_http_error(
                    status_code=response.status_code,
                    response_text=response.text
                )

        try:
            raw = response.json()
        except Exception as e:
            return ApiError.from_exception(e, "ODP returned non-JSON response")

        # Normalize possible bag shapes into {"results", "total"}
        if isinstance(raw, dict):
            results = (
                raw.get("results")
                or raw.get("assignmentBag")
                or raw.get("trademarkAssignmentDataBag")
                or []
            )
            total = raw.get("count", raw.get("total", len(results)))
            return {"results": results, "total": total}
        return {"results": raw, "total": len(raw) if isinstance(raw, list) else 1}

    async def _search_legacy(
        self,
        filters: Dict[str, str],
        offset: int,
        limit: int,
    ) -> Dict[str, Any]:
        """Query the legacy assignment-api.uspto.gov XML endpoint."""
        # Legacy API takes a single query value plus a filter field name
        legacy_fields = {
            "serial_number": "ApplicationNumber",
            "registration_number": "RegistrationNumber",
            "assignee_name": "AssigneeName",
            "assignor_name": "AssignorName",
        }
        # Use the first provided filter as the primary query
        key, value = next(iter(filters.items()))
        params = urllib.parse.urlencode({
            "query": value,
            "filter_field": legacy_fields[key],
            "rows": limit,
            "start": offset,
        })
        url = f"{config.TM_ASSIGNMENT_BASE_URL}{LEGACY_SEARCH_PATH}?{params}"

        response = await self._get(url)
        if isinstance(response, dict):
            return response  # Already an error dict

        if response.status_code != 200:
            return ApiError.from_http_error(
                status_code=response.status_code,
                response_text=response.text
            )

        return self._parse_legacy_xml(response.text)

    async def close(self):
        """Close the client connections and clean up resources."""
        logger.info("Closing trademark assignment client connections")
        await self.client.aclose()
