"""
PatentsView PatentSearch API Client

This module provides access to the PatentsView API at search.patentsview.org
for advanced patent search capabilities with full-text search, inventor/assignee
disambiguation, and CPC classification lookups.

API Reference: https://search.patentsview.org/docs/docs/Search%20API/SearchAPIReference/
"""

import asyncio
import json
import logging
import time
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
from patent_mcp_server.constants import HTTPMethods, Defaults, PatentsViewEndpoints

logger = logging.getLogger('patentsview_client')


class PatentsViewClient:
    """Client for the PatentsView PatentSearch API.

    Provides access to USPTO patent data through PatentsView including:
    - Full patent search with advanced query syntax
    - Inventor and assignee disambiguation
    - CPC classification lookups
    - Patent claims and description text
    - Foreign citations

    Rate limit: 45 requests per minute
    """

    def __init__(self):
        self.base_url = config.PATENTSVIEW_BASE_URL
        self.api_key = config.PATENTSVIEW_API_KEY
        self.rate_limit = config.PATENTSVIEW_RATE_LIMIT  # requests per minute

        # Rate limiting state
        self._request_times: List[float] = []
        self._rate_limit_lock = asyncio.Lock()

        self.headers = {
            "User-Agent": config.USER_AGENT,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        if self.api_key:
            self.headers["X-Api-Key"] = self.api_key

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

    async def _check_rate_limit(self):
        """Check and enforce rate limiting (45 requests/minute)."""
        async with self._rate_limit_lock:
            now = time.time()
            # Remove requests older than 60 seconds
            self._request_times = [t for t in self._request_times if now - t < 60]

            if len(self._request_times) >= self.rate_limit:
                # Wait until oldest request expires
                wait_time = 60 - (now - self._request_times[0])
                if wait_time > 0:
                    logger.warning(f"Rate limit reached, waiting {wait_time:.1f}s")
                    await asyncio.sleep(wait_time)
                    self._request_times = []

            self._request_times.append(time.time())

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
        """Make a request to the PatentsView API.

        Args:
            endpoint: API endpoint path
            method: HTTP method (GET or POST)
            params: Query parameters
            data: JSON body for POST requests

        Returns:
            Response JSON dictionary or error dictionary
        """
        await self._check_rate_limit()

        url = f"{self.base_url}{endpoint}"
        logger.info(f"Making {method} request to {url}")

        try:
            if method == HTTPMethods.GET:
                response = await self.client.get(url, params=params)
            else:
                response = await self.client.post(url, json=data)

            # Handle rate limit response
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning(f"Rate limited, waiting {retry_after}s")
                await asyncio.sleep(retry_after)
                # Retry the request
                if method == HTTPMethods.GET:
                    response = await self.client.get(url, params=params)
                else:
                    response = await self.client.post(url, json=data)

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            status_reason = e.response.headers.get("X-Status-Reason", "")
            logger.error(f"HTTP error: {status_code} - {status_reason}")

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
                    response_text=f"{status_reason or e.response.text}"
                )

        except (httpx.TimeoutException, httpx.NetworkError) as e:
            logger.warning(f"Network error (will retry): {str(e)}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return ApiError.from_exception(e, "PatentsView API request failed")

    def _build_query(
        self,
        q: Dict[str, Any],
        f: Optional[List[str]] = None,
        s: Optional[List[Dict[str, str]]] = None,
        o: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build a PatentsView API query object.

        Args:
            q: Query criteria (required)
            f: Fields to return
            s: Sort order
            o: Options (pagination, etc.)

        Returns:
            Query parameters dict
        """
        params = {"q": json.dumps(q)}

        if f:
            params["f"] = json.dumps(f)
        if s:
            params["s"] = json.dumps(s)
        if o:
            params["o"] = json.dumps(o)

        return params

    async def search_patents(
        self,
        query: Dict[str, Any],
        fields: Optional[List[str]] = None,
        sort: Optional[List[Dict[str, str]]] = None,
        size: int = 100,
        after: Optional[str] = None,
        exclude_withdrawn: bool = True,
    ) -> Dict[str, Any]:
        """Search patents using PatentsView query syntax.

        Args:
            query: Query object using PatentsView syntax
                   Example: {"patent_title": "neural network"}
                   Example: {"_and": [{"patent_date": {"_gte": "2020-01-01"}}, {"assignee_organization": "IBM"}]}
            fields: List of fields to return
            sort: Sort order list, e.g., [{"patent_date": "desc"}]
            size: Results per page (max 1000, default 100)
            after: Cursor for pagination from previous response
            exclude_withdrawn: Exclude withdrawn patents (default True)

        Returns:
            Dictionary containing search results
        """
        options = {"size": min(size, 1000)}
        if after:
            options["after"] = after
        if not exclude_withdrawn:
            options["exclude_withdrawn"] = False

        params = self._build_query(query, fields, sort, options)

        return await self._make_request(PatentsViewEndpoints.PATENT, params=params)

    async def get_patent(self, patent_id: str) -> Dict[str, Any]:
        """Get a specific patent by ID.

        Args:
            patent_id: Patent ID (e.g., "7861317")

        Returns:
            Dictionary containing patent details
        """
        return await self._make_request(f"{PatentsViewEndpoints.PATENT}{patent_id}/")

    async def search_by_text(
        self,
        text: str,
        search_type: str = "any",
        fields: Optional[List[str]] = None,
        size: int = 100,
    ) -> Dict[str, Any]:
        """Search patents by full-text in title and abstract.

        Args:
            text: Text to search for
            search_type: "any" (match any word), "all" (match all words), or "phrase" (exact phrase)
            fields: List of fields to return
            size: Results per page (max 1000)

        Returns:
            Dictionary containing search results
        """
        if search_type == "phrase":
            query = {"_or": [
                {"_text_phrase": {"patent_title": text}},
                {"_text_phrase": {"patent_abstract": text}},
            ]}
        elif search_type == "all":
            query = {"_or": [
                {"_text_all": {"patent_title": text}},
                {"_text_all": {"patent_abstract": text}},
            ]}
        else:  # any
            query = {"_or": [
                {"_text_any": {"patent_title": text}},
                {"_text_any": {"patent_abstract": text}},
            ]}

        default_fields = fields or [
            "patent_id", "patent_title", "patent_abstract", "patent_date",
            "patent_type", "patent_num_claims",
            "assignees.assignee_organization", "assignees.assignee_type",
            "inventors.inventor_name_first", "inventors.inventor_name_last",
            "cpcs.cpc_group_id", "cpcs.cpc_group_title",
        ]

        return await self.search_patents(query, fields=default_fields, size=size)

    async def search_assignees(
        self,
        query: Dict[str, Any],
        fields: Optional[List[str]] = None,
        size: int = 100,
    ) -> Dict[str, Any]:
        """Search disambiguated assignees.

        Args:
            query: Query object for assignee search
                   Example: {"assignee_organization": {"_contains": "IBM"}}
            fields: List of fields to return
            size: Results per page

        Returns:
            Dictionary containing assignee search results
        """
        options = {"size": min(size, 1000)}
        params = self._build_query(query, fields, o=options)

        return await self._make_request(PatentsViewEndpoints.ASSIGNEE, params=params)

    async def get_assignee(self, assignee_id: str) -> Dict[str, Any]:
        """Get a specific assignee by ID.

        Args:
            assignee_id: Disambiguated assignee ID

        Returns:
            Dictionary containing assignee details
        """
        return await self._make_request(f"{PatentsViewEndpoints.ASSIGNEE}{assignee_id}/")

    async def search_inventors(
        self,
        query: Dict[str, Any],
        fields: Optional[List[str]] = None,
        size: int = 100,
    ) -> Dict[str, Any]:
        """Search disambiguated inventors.

        Args:
            query: Query object for inventor search
                   Example: {"inventor_name_last": "Smith"}
            fields: List of fields to return
            size: Results per page

        Returns:
            Dictionary containing inventor search results
        """
        options = {"size": min(size, 1000)}
        params = self._build_query(query, fields, o=options)

        return await self._make_request(PatentsViewEndpoints.INVENTOR, params=params)

    async def get_inventor(self, inventor_id: str) -> Dict[str, Any]:
        """Get a specific inventor by ID.

        Args:
            inventor_id: Disambiguated inventor ID

        Returns:
            Dictionary containing inventor details
        """
        return await self._make_request(f"{PatentsViewEndpoints.INVENTOR}{inventor_id}/")

    async def get_patent_claims(
        self,
        patent_id: str,
        fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Get claims for a specific patent.

        Args:
            patent_id: Patent ID
            fields: List of fields to return

        Returns:
            Dictionary containing patent claims
        """
        query = {"patent_id": patent_id}
        default_fields = fields or ["patent_id", "claim_sequence", "claim_text"]
        params = self._build_query(query, default_fields)

        return await self._make_request(PatentsViewEndpoints.CLAIMS, params=params)

    async def get_patent_summary(
        self,
        patent_id: str,
    ) -> Dict[str, Any]:
        """Get brief summary text for a specific patent.

        Args:
            patent_id: Patent ID

        Returns:
            Dictionary containing patent brief summary
        """
        query = {"patent_id": patent_id}
        params = self._build_query(query)

        return await self._make_request(PatentsViewEndpoints.BRIEF_SUMMARY, params=params)

    async def get_patent_description(
        self,
        patent_id: str,
    ) -> Dict[str, Any]:
        """Get detailed description text for a specific patent.

        Args:
            patent_id: Patent ID

        Returns:
            Dictionary containing patent detailed description
        """
        query = {"patent_id": patent_id}
        params = self._build_query(query)

        return await self._make_request(PatentsViewEndpoints.DESCRIPTION, params=params)

    async def search_by_cpc(
        self,
        cpc_code: str,
        fields: Optional[List[str]] = None,
        size: int = 100,
    ) -> Dict[str, Any]:
        """Search patents by CPC classification code.

        Args:
            cpc_code: CPC code (e.g., "G06N3/08")
            fields: List of fields to return
            size: Results per page

        Returns:
            Dictionary containing patent search results
        """
        # Handle both exact match and prefix match
        if "/" in cpc_code:
            query = {"cpcs.cpc_subgroup_id": cpc_code}
        else:
            query = {"cpcs.cpc_group_id": {"_begins": cpc_code}}

        default_fields = fields or [
            "patent_id", "patent_title", "patent_date",
            "cpcs.cpc_group_id", "cpcs.cpc_group_title",
            "assignees.assignee_organization",
        ]

        return await self.search_patents(query, fields=default_fields, size=size)

    async def lookup_cpc_class(self, cpc_class: str) -> Dict[str, Any]:
        """Look up CPC class information.

        Args:
            cpc_class: CPC class code (e.g., "G06")

        Returns:
            Dictionary containing CPC class details
        """
        return await self._make_request(f"{PatentsViewEndpoints.CPC_CLASS}{cpc_class}/")

    async def lookup_cpc_group(self, cpc_group: str) -> Dict[str, Any]:
        """Look up CPC group information.

        Args:
            cpc_group: CPC group code (e.g., "G06N3/08")

        Returns:
            Dictionary containing CPC group details
        """
        return await self._make_request(f"{PatentsViewEndpoints.CPC_GROUP}{cpc_group}/")

    async def search_publications(
        self,
        query: Dict[str, Any],
        fields: Optional[List[str]] = None,
        size: int = 100,
    ) -> Dict[str, Any]:
        """Search pregrant publications.

        Args:
            query: Query object for publication search
            fields: List of fields to return
            size: Results per page

        Returns:
            Dictionary containing publication search results
        """
        options = {"size": min(size, 1000)}
        params = self._build_query(query, fields, o=options)

        return await self._make_request(PatentsViewEndpoints.PUBLICATION, params=params)

    async def get_foreign_citations(
        self,
        patent_id: str,
        fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Get foreign citations for a specific patent.

        Args:
            patent_id: Patent ID
            fields: List of fields to return

        Returns:
            Dictionary containing foreign citations
        """
        query = {"patent_id": patent_id}
        params = self._build_query(query, fields)

        return await self._make_request(PatentsViewEndpoints.FOREIGN_CITATION, params=params)

    async def search_attorneys(
        self,
        query: Dict[str, Any],
        fields: Optional[List[str]] = None,
        size: int = 100,
    ) -> Dict[str, Any]:
        """Search patent attorneys.

        Args:
            query: Query object for attorney search
                   Example: {"attorney_name_last": "Smith"}
                   Example: {"attorney_organization": {"_contains": "LLP"}}
            fields: List of fields to return
            size: Results per page

        Returns:
            Dictionary containing attorney search results
        """
        options = {"size": min(size, 1000)}
        params = self._build_query(query, fields, o=options)

        return await self._make_request(PatentsViewEndpoints.ATTORNEY, params=params)

    async def get_attorney(self, attorney_id: str) -> Dict[str, Any]:
        """Get a specific attorney by ID.

        Args:
            attorney_id: Attorney ID

        Returns:
            Dictionary containing attorney details
        """
        return await self._make_request(f"{PatentsViewEndpoints.ATTORNEY}{attorney_id}/")

    async def search_ipc(
        self,
        query: Dict[str, Any],
        fields: Optional[List[str]] = None,
        size: int = 100,
    ) -> Dict[str, Any]:
        """Search IPC (International Patent Classification) codes.

        Args:
            query: Query object for IPC search
                   Example: {"ipc_class": "G06"}
                   Example: {"ipc_subclass": {"_begins": "G06F"}}
            fields: List of fields to return
            size: Results per page

        Returns:
            Dictionary containing IPC search results
        """
        options = {"size": min(size, 1000)}
        params = self._build_query(query, fields, o=options)

        return await self._make_request(PatentsViewEndpoints.IPC, params=params)

    async def lookup_ipc(self, ipc_code: str) -> Dict[str, Any]:
        """Look up IPC classification information.

        Args:
            ipc_code: IPC code (e.g., "G06F")

        Returns:
            Dictionary containing IPC classification details
        """
        return await self._make_request(f"{PatentsViewEndpoints.IPC}{ipc_code}/")

    async def close(self):
        """Close the client connections."""
        logger.info("Closing PatentsView client connections")
        await self.client.aclose()
