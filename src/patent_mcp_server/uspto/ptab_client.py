"""
USPTO PTAB API Client (Patent Trial and Appeal Board)

This module provides access to the PTAB API v3 at api.uspto.gov for accessing
Patent Trial and Appeal Board data including IPR, PGR, CBM proceedings,
trial decisions, appeal outcomes, and interference records.
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
from patent_mcp_server.constants import HTTPMethods, Defaults, PTABTrialTypes

logger = logging.getLogger('ptab_client')


class PTABClient:
    """Client for the USPTO PTAB API v3.

    Provides access to Patent Trial and Appeal Board data including:
    - Trial proceedings (IPR, PGR, CBM, derivation)
    - Trial decisions (institution, final written decisions, terminations)
    - Trial documents
    - Appeals (ex parte)
    - Interferences (historical pre-AIA)
    """

    def __init__(self):
        self.base_url = f"{config.API_BASE_URL}/api/v1/patent/trials"
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
        """Make a request to the PTAB API.

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
            return ApiError.from_exception(e, f"PTAB API request failed")

    async def search_proceedings(
        self,
        query: Optional[str] = None,
        trial_type: Optional[str] = None,
        patent_number: Optional[str] = None,
        party_name: Optional[str] = None,
        filing_date_from: Optional[str] = None,
        filing_date_to: Optional[str] = None,
        status: Optional[str] = None,
        offset: int = Defaults.SEARCH_START,
        limit: int = Defaults.API_LIMIT,
    ) -> Dict[str, Any]:
        """Search PTAB trial proceedings.

        Args:
            query: Full-text search query
            trial_type: Type of trial (IPR, PGR, CBM, DER)
            patent_number: Patent number involved in the proceeding
            party_name: Name of petitioner or patent owner
            filing_date_from: Filing date range start (YYYY-MM-DD)
            filing_date_to: Filing date range end (YYYY-MM-DD)
            status: Proceeding status
            offset: Starting position for pagination
            limit: Maximum results to return

        Returns:
            Dictionary containing search results
        """
        params = {
            "offset": offset,
            "limit": limit,
        }

        if query:
            params["q"] = query
        if trial_type and trial_type in PTABTrialTypes.ALL:
            params["trialType"] = trial_type
        if patent_number:
            params["patentNumber"] = patent_number
        if party_name:
            params["partyName"] = party_name
        if filing_date_from:
            params["filingDateFrom"] = filing_date_from
        if filing_date_to:
            params["filingDateTo"] = filing_date_to
        if status:
            params["status"] = status

        return await self._make_request("/proceedings/search", params=params)

    async def get_proceeding(self, proceeding_number: str) -> Dict[str, Any]:
        """Get details of a specific PTAB proceeding.

        Args:
            proceeding_number: The proceeding number (e.g., IPR2023-00001)

        Returns:
            Dictionary containing proceeding details
        """
        return await self._make_request(f"/proceedings/{proceeding_number}")

    async def get_proceeding_documents(
        self,
        proceeding_number: str,
        document_type: Optional[str] = None,
        offset: int = Defaults.SEARCH_START,
        limit: int = Defaults.API_LIMIT,
    ) -> Dict[str, Any]:
        """Get documents filed in a PTAB proceeding.

        Args:
            proceeding_number: The proceeding number
            document_type: Filter by document type (petition, response, etc.)
            offset: Starting position for pagination
            limit: Maximum results to return

        Returns:
            Dictionary containing document list
        """
        params = {"offset": offset, "limit": limit}
        if document_type:
            params["documentType"] = document_type

        return await self._make_request(
            f"/proceedings/{proceeding_number}/documents",
            params=params
        )

    async def search_decisions(
        self,
        query: Optional[str] = None,
        decision_type: Optional[str] = None,
        proceeding_number: Optional[str] = None,
        patent_number: Optional[str] = None,
        decision_date_from: Optional[str] = None,
        decision_date_to: Optional[str] = None,
        offset: int = Defaults.SEARCH_START,
        limit: int = Defaults.API_LIMIT,
    ) -> Dict[str, Any]:
        """Search PTAB trial decisions.

        Args:
            query: Full-text search in decision documents
            decision_type: Type of decision (institution, final, termination)
            proceeding_number: Proceeding number
            patent_number: Patent number
            decision_date_from: Decision date range start (YYYY-MM-DD)
            decision_date_to: Decision date range end (YYYY-MM-DD)
            offset: Starting position for pagination
            limit: Maximum results to return

        Returns:
            Dictionary containing decision search results
        """
        params = {"offset": offset, "limit": limit}

        if query:
            params["q"] = query
        if decision_type:
            params["decisionType"] = decision_type
        if proceeding_number:
            params["proceedingNumber"] = proceeding_number
        if patent_number:
            params["patentNumber"] = patent_number
        if decision_date_from:
            params["decisionDateFrom"] = decision_date_from
        if decision_date_to:
            params["decisionDateTo"] = decision_date_to

        return await self._make_request("/decisions/search", params=params)

    async def get_decision(self, decision_id: str) -> Dict[str, Any]:
        """Get details of a specific PTAB decision.

        Args:
            decision_id: The decision identifier

        Returns:
            Dictionary containing decision details
        """
        return await self._make_request(f"/decisions/{decision_id}")

    async def search_appeals(
        self,
        query: Optional[str] = None,
        application_number: Optional[str] = None,
        patent_number: Optional[str] = None,
        appeal_number: Optional[str] = None,
        decision_date_from: Optional[str] = None,
        decision_date_to: Optional[str] = None,
        offset: int = Defaults.SEARCH_START,
        limit: int = Defaults.API_LIMIT,
    ) -> Dict[str, Any]:
        """Search ex parte appeal decisions.

        Args:
            query: Full-text search query
            application_number: Application number
            patent_number: Patent number
            appeal_number: Appeal number
            decision_date_from: Decision date range start
            decision_date_to: Decision date range end
            offset: Starting position for pagination
            limit: Maximum results to return

        Returns:
            Dictionary containing appeal search results
        """
        params = {"offset": offset, "limit": limit}

        if query:
            params["q"] = query
        if application_number:
            params["applicationNumber"] = application_number
        if patent_number:
            params["patentNumber"] = patent_number
        if appeal_number:
            params["appealNumber"] = appeal_number
        if decision_date_from:
            params["decisionDateFrom"] = decision_date_from
        if decision_date_to:
            params["decisionDateTo"] = decision_date_to

        return await self._make_request("/appeals/decisions/search", params=params)

    async def get_appeal_decision(self, appeal_number: str) -> Dict[str, Any]:
        """Get details of a specific ex parte appeal decision.

        Args:
            appeal_number: The appeal number

        Returns:
            Dictionary containing appeal decision details
        """
        return await self._make_request(f"/appeals/decisions/{appeal_number}")

    async def search_interferences(
        self,
        query: Optional[str] = None,
        interference_number: Optional[str] = None,
        patent_number: Optional[str] = None,
        party_name: Optional[str] = None,
        offset: int = Defaults.SEARCH_START,
        limit: int = Defaults.API_LIMIT,
    ) -> Dict[str, Any]:
        """Search historical interference proceedings (pre-AIA).

        Args:
            query: Full-text search query
            interference_number: Interference proceeding number
            patent_number: Patent number
            party_name: Name of a party
            offset: Starting position for pagination
            limit: Maximum results to return

        Returns:
            Dictionary containing interference search results
        """
        params = {"offset": offset, "limit": limit}

        if query:
            params["q"] = query
        if interference_number:
            params["interferenceNumber"] = interference_number
        if patent_number:
            params["patentNumber"] = patent_number
        if party_name:
            params["partyName"] = party_name

        return await self._make_request("/interferences/search", params=params)

    async def get_interference(self, interference_number: str) -> Dict[str, Any]:
        """Get details of a specific interference proceeding.

        Args:
            interference_number: The interference number

        Returns:
            Dictionary containing interference details
        """
        return await self._make_request(f"/interferences/{interference_number}")

    async def close(self):
        """Close the client connections."""
        logger.info("Closing PTAB client connections")
        await self.client.aclose()
