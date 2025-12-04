"""
USPTO Patent Litigation API Client

This module provides access to the OCE Patent Litigation Cases API
for accessing district court case records involving patents.

Contains 74,623+ district court case records.
"""

import logging
from typing import Any, Optional, Dict, List
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from patent_mcp_server.util.logging import LoggingTransport
from patent_mcp_server.util.errors import ApiError
from patent_mcp_server.config import config
from patent_mcp_server.constants import HTTPMethods, Defaults

logger = logging.getLogger('litigation_client')


class LitigationClient:
    """Client for the USPTO OCE Patent Litigation Cases API.

    Provides access to 74,623+ district court case records involving patents.
    """

    def __init__(self):
        self.base_url = f"{config.API_BASE_URL}/api/v1/patent/litigation"
        self.headers = {
            "User-Agent": config.USER_AGENT,
            "X-API-KEY": config.USPTO_API_KEY if config.USPTO_API_KEY else "",
            "Accept": "application/json",
        }

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
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
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
    async def _make_request(
        self,
        endpoint: str,
        method: str = HTTPMethods.GET,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a request to the Patent Litigation API.

        Args:
            endpoint: API endpoint path
            method: HTTP method
            params: Query parameters for GET requests
            data: JSON body for POST requests

        Returns:
            Response JSON dictionary or error dictionary
        """
        url = f"{self.base_url}{endpoint}"
        logger.info(f"Making {method} request to {url}")

        try:
            if method == HTTPMethods.GET:
                response = await self.client.get(url, params=params)
            else:
                response = await self.client.post(url, json=data)

            response.raise_for_status()
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
            except Exception:
                return ApiError.from_http_error(
                    status_code=status_code,
                    response_text=e.response.text
                )

        except (httpx.TimeoutException, httpx.NetworkError) as e:
            logger.warning(f"Network error (will retry): {str(e)}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return ApiError.from_exception(e, "Patent Litigation API request failed")

    async def search_cases(
        self,
        query: Optional[str] = None,
        patent_number: Optional[str] = None,
        plaintiff: Optional[str] = None,
        defendant: Optional[str] = None,
        court: Optional[str] = None,
        case_type: Optional[str] = None,
        filing_date_from: Optional[str] = None,
        filing_date_to: Optional[str] = None,
        termination_date_from: Optional[str] = None,
        termination_date_to: Optional[str] = None,
        disposition: Optional[str] = None,
        offset: int = Defaults.SEARCH_START,
        limit: int = Defaults.API_LIMIT,
    ) -> Dict[str, Any]:
        """Search patent litigation cases.

        Args:
            query: Full-text search query
            patent_number: Patent number involved in case
            plaintiff: Plaintiff name
            defendant: Defendant name
            court: Court name or district
            case_type: Type of case
            filing_date_from: Filing date range start (YYYY-MM-DD)
            filing_date_to: Filing date range end (YYYY-MM-DD)
            termination_date_from: Termination date range start
            termination_date_to: Termination date range end
            disposition: Case disposition/outcome
            offset: Starting position for pagination
            limit: Maximum results to return

        Returns:
            Dictionary containing case search results
        """
        params = {"offset": offset, "limit": limit}

        if query:
            params["q"] = query
        if patent_number:
            params["patentNumber"] = patent_number
        if plaintiff:
            params["plaintiff"] = plaintiff
        if defendant:
            params["defendant"] = defendant
        if court:
            params["court"] = court
        if case_type:
            params["caseType"] = case_type
        if filing_date_from:
            params["filingDateFrom"] = filing_date_from
        if filing_date_to:
            params["filingDateTo"] = filing_date_to
        if termination_date_from:
            params["terminationDateFrom"] = termination_date_from
        if termination_date_to:
            params["terminationDateTo"] = termination_date_to
        if disposition:
            params["disposition"] = disposition

        return await self._make_request("/cases/search", params=params)

    async def get_case(self, case_id: str) -> Dict[str, Any]:
        """Get details of a specific litigation case.

        Args:
            case_id: The case identifier

        Returns:
            Dictionary containing case details including:
            - Case number
            - Court information
            - Parties (plaintiffs, defendants)
            - Patents involved
            - Filing and termination dates
            - Disposition/outcome
        """
        return await self._make_request(f"/cases/{case_id}")

    async def get_patent_litigation_history(
        self,
        patent_number: str,
    ) -> Dict[str, Any]:
        """Get all litigation cases involving a specific patent.

        Args:
            patent_number: Patent number

        Returns:
            Dictionary containing all cases involving the patent
        """
        params = {"patentNumber": patent_number, "limit": 100}
        return await self._make_request("/cases/search", params=params)

    async def get_party_litigation_history(
        self,
        party_name: str,
        role: Optional[str] = None,
        limit: int = Defaults.API_LIMIT,
    ) -> Dict[str, Any]:
        """Get litigation history for a party (company or individual).

        Args:
            party_name: Name of the party
            role: Filter by role (plaintiff, defendant, or both if None)
            limit: Maximum results to return

        Returns:
            Dictionary containing cases involving the party
        """
        params = {"limit": limit}

        if role == "plaintiff":
            params["plaintiff"] = party_name
        elif role == "defendant":
            params["defendant"] = party_name
        else:
            # Search as either plaintiff or defendant
            params["q"] = party_name

        return await self._make_request("/cases/search", params=params)

    async def get_court_statistics(
        self,
        court: Optional[str] = None,
        year: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get litigation statistics by court.

        Args:
            court: Specific court to get statistics for
            year: Filter by year

        Returns:
            Dictionary containing court statistics
        """
        params = {}
        if court:
            params["court"] = court
        if year:
            params["year"] = year

        return await self._make_request("/statistics/courts", params=params)

    async def close(self):
        """Close the client connections."""
        logger.info("Closing Litigation client connections")
        await self.client.aclose()
