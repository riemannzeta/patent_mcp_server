"""
USPTO Office Action API Client

This module provides access to USPTO Office Action APIs at developer.uspto.gov
for accessing full-text office actions, citations, and rejection data.

APIs included:
- Office Action Text Retrieval API
- Office Action Citations API
- Office Action Rejection API
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

logger = logging.getLogger('office_action_client')


class OfficeActionClient:
    """Client for USPTO Office Action APIs.

    Provides access to:
    - Office Action text retrieval (full-text of office actions)
    - Office Action citations (references cited in office actions)
    - Office Action rejections (rejection data with claim-level details)

    Data available from June 1, 2018 to 180 days prior to current date.
    """

    def __init__(self):
        self.base_url = config.OFFICE_ACTION_BASE_URL
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
        """Make a request to the Office Action API.

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
            return ApiError.from_exception(e, "Office Action API request failed")

    # =========================================================================
    # Office Action Text Retrieval API
    # =========================================================================

    async def get_office_action_text(
        self,
        application_number: str,
        mail_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get full-text of office actions for an application.

        Args:
            application_number: Patent application number (e.g., "12345678")
            mail_date: Filter by mail date (YYYY-MM-DD format)

        Returns:
            Dictionary containing office action text
        """
        params = {"applicationNumber": application_number}
        if mail_date:
            params["mailDate"] = mail_date

        return await self._make_request("/ds-api/oa-text/v1/search", params=params)

    async def search_office_actions(
        self,
        query: Optional[str] = None,
        application_number: Optional[str] = None,
        examiner_name: Optional[str] = None,
        art_unit: Optional[str] = None,
        mail_date_from: Optional[str] = None,
        mail_date_to: Optional[str] = None,
        action_type: Optional[str] = None,
        offset: int = Defaults.SEARCH_START,
        limit: int = Defaults.API_LIMIT,
    ) -> Dict[str, Any]:
        """Search office actions.

        Args:
            query: Full-text search query
            application_number: Patent application number
            examiner_name: Examiner name
            art_unit: Art unit number
            mail_date_from: Mail date range start (YYYY-MM-DD)
            mail_date_to: Mail date range end (YYYY-MM-DD)
            action_type: Type of office action
            offset: Starting position for pagination
            limit: Maximum results to return

        Returns:
            Dictionary containing search results
        """
        params = {"offset": offset, "limit": limit}

        if query:
            params["q"] = query
        if application_number:
            params["applicationNumber"] = application_number
        if examiner_name:
            params["examinerName"] = examiner_name
        if art_unit:
            params["artUnit"] = art_unit
        if mail_date_from:
            params["mailDateFrom"] = mail_date_from
        if mail_date_to:
            params["mailDateTo"] = mail_date_to
        if action_type:
            params["actionType"] = action_type

        return await self._make_request("/ds-api/oa-text/v1/search", params=params)

    # =========================================================================
    # Office Action Citations API
    # =========================================================================

    async def get_office_action_citations(
        self,
        application_number: str,
        mail_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get citations from office actions for an application.

        Citations include references from Form PTO-892, Form PTO-1449,
        and text of office actions.

        Args:
            application_number: Patent application number
            mail_date: Filter by mail date (YYYY-MM-DD format)

        Returns:
            Dictionary containing citation data
        """
        params = {"applicationNumber": application_number}
        if mail_date:
            params["mailDate"] = mail_date

        return await self._make_request("/ds-api/oa-citations/v2/search", params=params)

    async def search_citations(
        self,
        query: Optional[str] = None,
        application_number: Optional[str] = None,
        cited_patent_number: Optional[str] = None,
        citation_type: Optional[str] = None,
        mail_date_from: Optional[str] = None,
        mail_date_to: Optional[str] = None,
        offset: int = Defaults.SEARCH_START,
        limit: int = Defaults.API_LIMIT,
    ) -> Dict[str, Any]:
        """Search office action citations.

        Args:
            query: Full-text search query
            application_number: Patent application number
            cited_patent_number: Patent number being cited
            citation_type: Type of citation (US Patent, Foreign, NPL)
            mail_date_from: Mail date range start (YYYY-MM-DD)
            mail_date_to: Mail date range end (YYYY-MM-DD)
            offset: Starting position for pagination
            limit: Maximum results to return

        Returns:
            Dictionary containing citation search results
        """
        params = {"offset": offset, "limit": limit}

        if query:
            params["q"] = query
        if application_number:
            params["applicationNumber"] = application_number
        if cited_patent_number:
            params["citedPatentNumber"] = cited_patent_number
        if citation_type:
            params["citationType"] = citation_type
        if mail_date_from:
            params["mailDateFrom"] = mail_date_from
        if mail_date_to:
            params["mailDateTo"] = mail_date_to

        return await self._make_request("/ds-api/oa-citations/v2/search", params=params)

    # =========================================================================
    # Office Action Rejection API
    # =========================================================================

    async def get_office_action_rejections(
        self,
        application_number: str,
        mail_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get rejection data from office actions for an application.

        Includes document level data with type of actions taken on claims.

        Args:
            application_number: Patent application number
            mail_date: Filter by mail date (YYYY-MM-DD format)

        Returns:
            Dictionary containing rejection data
        """
        params = {"applicationNumber": application_number}
        if mail_date:
            params["mailDate"] = mail_date

        return await self._make_request("/ds-api/oa-rejections/v2/search", params=params)

    async def search_rejections(
        self,
        query: Optional[str] = None,
        application_number: Optional[str] = None,
        rejection_type: Optional[str] = None,
        rejection_basis: Optional[str] = None,
        claim_number: Optional[int] = None,
        mail_date_from: Optional[str] = None,
        mail_date_to: Optional[str] = None,
        offset: int = Defaults.SEARCH_START,
        limit: int = Defaults.API_LIMIT,
    ) -> Dict[str, Any]:
        """Search office action rejections.

        Args:
            query: Full-text search query
            application_number: Patent application number
            rejection_type: Type of rejection (102, 103, 112, etc.)
            rejection_basis: Basis for rejection (anticipation, obviousness)
            claim_number: Specific claim number
            mail_date_from: Mail date range start (YYYY-MM-DD)
            mail_date_to: Mail date range end (YYYY-MM-DD)
            offset: Starting position for pagination
            limit: Maximum results to return

        Returns:
            Dictionary containing rejection search results
        """
        params = {"offset": offset, "limit": limit}

        if query:
            params["q"] = query
        if application_number:
            params["applicationNumber"] = application_number
        if rejection_type:
            params["rejectionType"] = rejection_type
        if rejection_basis:
            params["rejectionBasis"] = rejection_basis
        if claim_number is not None:
            params["claimNumber"] = claim_number
        if mail_date_from:
            params["mailDateFrom"] = mail_date_from
        if mail_date_to:
            params["mailDateTo"] = mail_date_to

        return await self._make_request("/ds-api/oa-rejections/v2/search", params=params)

    # =========================================================================
    # Bulk Download
    # =========================================================================

    async def get_weekly_zip_url(
        self,
        date: str,
    ) -> Dict[str, Any]:
        """Get URL for weekly bulk download zip file.

        Args:
            date: Date for the weekly zip (YYYY-MM-DD format, typically a Sunday)

        Returns:
            Dictionary containing the download URL
        """
        # Weekly zips are stored on S3
        base_s3_url = "https://developer-hub.s3.amazonaws.com/bdr-oa-bulkdata/weekly"
        zip_url = f"{base_s3_url}/bdr_oa_bulkdata_weekly_{date}.zip"

        return {
            "download_url": zip_url,
            "date": date,
            "note": "Weekly bulk download files are published each Sunday"
        }

    async def close(self):
        """Close the client connections."""
        logger.info("Closing Office Action client connections")
        await self.client.aclose()
