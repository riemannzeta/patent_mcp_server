"""
USPTO Trademark Assignment Search Module (assignmentcenter.uspto.gov)

Searches recorded trademark assignment (ownership transfer) records,
covering the USPTO assignment database (1955-present).

BACKEND (verified live 2026-06-10): the USPTO Assignment Center public API.
The legacy assignment-api.uspto.gov XML API was decommissioned with the
Developer Hub on June 5, 2026, and no ODP endpoint exists for trademark
assignments; Assignment Center is the live replacement.

  POST {TM_ASSIGNMENT_BASE_URL}/ipas/search/api/v2/public/trademark/exportTradeMarkData
  Body: {"searchCriteria": [{"property": "<value>", "searchBy": "<field>"}, ...]}
  Pagination criteria: startRow/endRow (1-based) and rowsNeeded (max 1000).
  Response: [{"searchCriteria": [...], "data": [<records>]}]

No API key is required.
"""

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
from patent_mcp_server.constants import TrademarkDefaults

# Set up logging
logger = logging.getLogger('tm_assignment_client')

SEARCH_PATH = "/ipas/search/api/v2/public/trademark/exportTradeMarkData"

# Maximum rows the Assignment Center API returns per request
MAX_ROWS_PER_REQUEST = 1000

# Map of our filter names to Assignment Center searchBy values
SEARCH_BY_FIELDS = {
    "serial_number": "serialNumber",
    "registration_number": "registrationNumber",
    "assignee_name": "assigneeName",
    "assignor_name": "assignorName",
    "reel_frame": "reelFrame",
}


class TmAssignmentClient:
    """Client for trademark assignment search via USPTO Assignment Center.

    Supports context manager protocol for proper resource cleanup.
    """

    def __init__(self):
        self.headers = {
            "User-Agent": config.USER_AGENT,
            "Accept": "application/json",
            "Content-Type": "application/json",
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

    @staticmethod
    def build_search_criteria(
        filters: Dict[str, str],
        offset: int = 0,
        limit: int = TrademarkDefaults.SEARCH_LIMIT,
    ) -> List[Dict[str, str]]:
        """Build the Assignment Center searchCriteria list.

        Pure function; fully unit-testable offline. Every entry is a
        {"property": <value>, "searchBy": <field>} pair; pagination rides
        along as startRow/endRow/rowsNeeded criteria.

        Args:
            filters: Mapping of our filter names (see SEARCH_BY_FIELDS) to values
            offset: 0-based pagination offset (converted to 1-based rows)
            limit: Maximum results (capped at MAX_ROWS_PER_REQUEST)

        Returns:
            List of searchCriteria dictionaries
        """
        criteria = [
            {"property": value, "searchBy": SEARCH_BY_FIELDS[name]}
            for name, value in filters.items()
        ]

        limit = min(limit, MAX_ROWS_PER_REQUEST)
        if offset > 0:
            start_row = offset + 1  # API rows are 1-based
            criteria.append({"property": str(start_row), "searchBy": "startRow"})
            criteria.append({"property": str(start_row + limit - 1), "searchBy": "endRow"})
        criteria.append({"property": str(limit), "searchBy": "rowsNeeded"})

        return criteria

    @staticmethod
    def parse_search_response(raw: Any) -> Dict[str, Any]:
        """Extract assignment records from the Assignment Center envelope.

        The API returns a list with one element: {"searchCriteria": [...],
        "data": [<records>]}. No overall hit count is reported, so total
        reflects the number of returned records.

        Args:
            raw: Parsed JSON response

        Returns:
            {"results": [...], "total": N}
        """
        if isinstance(raw, list) and raw and isinstance(raw[0], dict):
            records = raw[0].get("data") or []
            return {"results": records, "total": len(records)}
        if isinstance(raw, dict):
            records = raw.get("data") or []
            return {"results": records, "total": len(records)}
        return {"results": [], "total": 0}

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
    async def _post(self, url: str, body: Dict[str, Any]) -> Union[httpx.Response, Dict[str, Any]]:
        """Perform a POST with retry; returns the response or an error dict."""
        try:
            return await self.client.post(url, json=body, timeout=config.REQUEST_TIMEOUT)
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            logger.warning(f"Network error (will retry): {str(e)}")
            raise  # Let tenacity handle the retry
        except Exception as e:
            logger.error(f"Request error: {str(e)}")
            return ApiError.from_exception(e, f"Request to {url} failed")

    async def search_assignments(
        self,
        serial_number: Optional[str] = None,
        registration_number: Optional[str] = None,
        assignee_name: Optional[str] = None,
        assignor_name: Optional[str] = None,
        reel_frame: Optional[str] = None,
        offset: int = 0,
        limit: int = TrademarkDefaults.SEARCH_LIMIT,
    ) -> Dict[str, Any]:
        """Search trademark assignment records.

        At least one filter is required; multiple filters combine (AND).

        Args:
            serial_number: Trademark application serial number
            registration_number: Trademark registration number
            assignee_name: Assignee (new owner) name
            assignor_name: Assignor (previous owner) name
            reel_frame: Recordation reel/frame identifier (e.g. "9006/0093")
            offset: Pagination offset
            limit: Maximum results

        Returns:
            {"results": [...], "total": N, "backend": "assignment-center"} or error
        """
        filters = {
            name: value
            for name, value in {
                "serial_number": serial_number,
                "registration_number": registration_number,
                "assignee_name": assignee_name,
                "assignor_name": assignor_name,
                "reel_frame": reel_frame,
            }.items()
            if value
        }
        if not filters:
            return ApiError.create(
                message=(
                    "At least one filter is required: serial_number, "
                    "registration_number, assignee_name, assignor_name, "
                    "or reel_frame"
                ),
                status_code=400,
                error_code="MISSING_FILTER"
            )

        criteria = self.build_search_criteria(filters, offset=offset, limit=limit)
        url = f"{config.TM_ASSIGNMENT_BASE_URL}{SEARCH_PATH}"

        response = await self._post(url, {"searchCriteria": criteria})
        if isinstance(response, dict):
            return response  # Already an error dict

        if response.status_code != 200:
            return ApiError.from_http_error(
                status_code=response.status_code,
                response_text=response.text
            )

        try:
            raw = response.json()
        except Exception as e:
            return ApiError.from_exception(
                e, "Assignment Center returned non-JSON response"
            )

        result = self.parse_search_response(raw)
        result["backend"] = "assignment-center"
        return result

    async def close(self):
        """Close the client connections and clean up resources."""
        logger.info("Closing trademark assignment client connections")
        await self.client.aclose()
