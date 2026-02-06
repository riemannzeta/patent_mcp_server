"""
USPTO Enriched Citation API Client

This module provides access to the USPTO Enriched Citation API v3
for patent evaluation insights and citation analysis.

Note: This API is scheduled for decommissioning and migration to ODP in early 2026.
Requires an ODP API key obtained from https://data.uspto.gov ("My ODP").
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

logger = logging.getLogger('enriched_citation_client')


class EnrichedCitationClient:
    """Client for the USPTO Enriched Citation API v3.

    Provides patent evaluation insights for IP5 stakeholders including
    citation analysis, patent family data, and evaluation metrics.
    """

    def __init__(self):
        self.base_url = f"{config.API_BASE_URL}/api/v3/patent/citations"
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
        """Make a request to the Enriched Citation API.

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
            return ApiError.from_exception(e, "Enriched Citation API request failed")

    async def get_patent_citations(
        self,
        patent_number: str,
        include_forward: bool = True,
        include_backward: bool = True,
    ) -> Dict[str, Any]:
        """Get enriched citation data for a patent.

        Args:
            patent_number: Patent number (e.g., "7123456")
            include_forward: Include forward citations (patents citing this one)
            include_backward: Include backward citations (patents this one cites)

        Returns:
            Dictionary containing enriched citation data
        """
        params = {
            "patentNumber": patent_number,
            "includeForward": str(include_forward).lower(),
            "includeBackward": str(include_backward).lower(),
        }

        return await self._make_request("/patent", params=params)

    async def search_citations(
        self,
        query: Optional[str] = None,
        citing_patent: Optional[str] = None,
        cited_patent: Optional[str] = None,
        citation_category: Optional[str] = None,
        assignee: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        offset: int = Defaults.SEARCH_START,
        limit: int = Defaults.API_LIMIT,
    ) -> Dict[str, Any]:
        """Search enriched citation records.

        Args:
            query: Full-text search query
            citing_patent: Patent number that is citing
            cited_patent: Patent number being cited
            citation_category: Category of citation (X, Y, A, etc.)
            assignee: Assignee name
            date_from: Citation date range start (YYYY-MM-DD)
            date_to: Citation date range end (YYYY-MM-DD)
            offset: Starting position for pagination
            limit: Maximum results to return

        Returns:
            Dictionary containing search results
        """
        params = {"offset": offset, "limit": limit}

        if query:
            params["q"] = query
        if citing_patent:
            params["citingPatent"] = citing_patent
        if cited_patent:
            params["citedPatent"] = cited_patent
        if citation_category:
            params["citationCategory"] = citation_category
        if assignee:
            params["assignee"] = assignee
        if date_from:
            params["dateFrom"] = date_from
        if date_to:
            params["dateTo"] = date_to

        return await self._make_request("/search", params=params)

    async def get_citation_metrics(
        self,
        patent_number: str,
    ) -> Dict[str, Any]:
        """Get citation metrics and evaluation data for a patent.

        Args:
            patent_number: Patent number

        Returns:
            Dictionary containing citation metrics including:
            - Forward citation count
            - Backward citation count
            - Citation age metrics
            - Technology field analysis
        """
        return await self._make_request(f"/metrics/{patent_number}")

    async def get_patent_family_citations(
        self,
        family_id: str,
    ) -> Dict[str, Any]:
        """Get citations for an entire patent family.

        Args:
            family_id: Patent family identifier

        Returns:
            Dictionary containing family-level citation data
        """
        return await self._make_request(f"/family/{family_id}")

    async def close(self):
        """Close the client connections."""
        logger.info("Closing Enriched Citation client connections")
        await self.client.aclose()
