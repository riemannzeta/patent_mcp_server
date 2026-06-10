"""
USPTO Trademark Search Module (tmsearch.uspto.gov)

This module provides full-text trademark search via the *undocumented internal*
JSON API behind the USPTO trademark search web application (the TESS
replacement at https://tmsearch.uspto.gov). This is the same risk profile as
the PPUBS internal API used by ppubs_uspto_gov.py: it is not an official
public API and may change or break without notice.

CONTRACT STATUS (2026-06-10): VERIFIED LIVE. POST {TMSEARCH_BASE_URL}
/prod-stage-v1-0-0/tmsearch with an Elasticsearch-style query body returns
JSON. Response envelope (non-standard ES): {"took": N, "hits": {"totalValue":
N, "hits": [{"id": "<serial>", "source": {...}}]}}. If the shape drifts
again, the seams to fix are:
  - SEARCH_PATH (module constant below)
  - constants.TmSearchFields (index field names)
  - TmSearchClient.build_search_body / parse_search_response

No API key is required. The service sits behind AWS WAF, which currently
answers plain requests; if USPTO tightens it (403/202 challenge responses),
set TMSEARCH_WAF_TOKEN to a browser session's "aws-waf-token" cookie value.
"""

from typing import Any, Optional, Dict
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
from patent_mcp_server.constants import TmSearchFields, TrademarkDefaults

# Set up logging
logger = logging.getLogger('tmsearch_client')

# POST target for the internal search API, relative to config.TMSEARCH_BASE_URL.
# Single place to fix if the web app's endpoint moves. Verified live 2026-06-10.
SEARCH_PATH = "/prod-stage-v1-0-0/tmsearch"


class TmSearchClient:
    """Client for the undocumented trademark search API at tmsearch.uspto.gov.

    Sends browser-like headers (the internal API serves the web app). No
    session management is needed as of the last observation; if the service
    starts requiring a token, copy the get_session() pattern from PpubsClient.

    Supports context manager protocol for proper resource cleanup.
    """

    def __init__(self):
        self.headers = {
            "User-Agent": config.USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Origin": config.TMSEARCH_BASE_URL,
            "Referer": f"{config.TMSEARCH_BASE_URL}/",
            "Content-Type": "application/json",
        }

        # AWS WAF token cookie, if the user supplied one (see module docstring)
        cookies = {}
        if config.TMSEARCH_WAF_TOKEN:
            cookies["aws-waf-token"] = config.TMSEARCH_WAF_TOKEN

        # Create a custom transport that logs all requests and responses
        transport = httpx.AsyncHTTPTransport()
        logging_transport = LoggingTransport(transport)

        self.client = httpx.AsyncClient(
            headers=self.headers,
            cookies=cookies,
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
    def build_search_body(
        query: Optional[str] = None,
        mark_text: Optional[str] = None,
        owner_name: Optional[str] = None,
        serial_number: Optional[str] = None,
        registration_number: Optional[str] = None,
        goods_services: Optional[str] = None,
        international_class: Optional[str] = None,
        status_filter: Optional[str] = None,
        offset: int = 0,
        limit: int = TrademarkDefaults.SEARCH_LIMIT,
    ) -> Dict[str, Any]:
        """Construct the Elasticsearch-style request body.

        Shape verified live 2026-06-10 (see module docstring). Pure function;
        fully unit-testable offline.

        Args:
            query: Raw query string (Elasticsearch query_string syntax)
            mark_text: Word mark text to match
            owner_name: Owner name to match
            serial_number: Exact serial number
            registration_number: Exact registration number
            goods_services: Goods/services description terms to match
            international_class: Nice international class number (e.g. "9");
                zero-padded to 3 digits because the index stores "IC 009"
            status_filter: "live", "dead", or None for both
            offset: Pagination offset
            limit: Maximum results

        Returns:
            Request body dictionary
        """
        must = []
        filters = []

        if query:
            must.append({
                "query_string": {
                    "query": query,
                    "default_field": TmSearchFields.WORDMARK,
                }
            })
        if mark_text:
            must.append({"match": {TmSearchFields.WORDMARK: mark_text}})
        if owner_name:
            must.append({"match": {TmSearchFields.OWNER: owner_name}})
        if serial_number:
            must.append({"term": {TmSearchFields.SERIAL_NUMBER: serial_number}})
        if registration_number:
            must.append({"term": {TmSearchFields.REGISTRATION_NUMBER: registration_number}})
        if goods_services:
            must.append({"match": {TmSearchFields.GOODS_AND_SERVICES: goods_services}})

        if international_class:
            # Index values look like "IC 025"; the term must be zero-padded
            class_term = str(international_class).strip()
            if class_term.isdigit():
                class_term = class_term.zfill(3)
            filters.append({"term": {TmSearchFields.INTERNATIONAL_CLASS: class_term}})
        if status_filter:
            status = status_filter.strip().lower()
            if status == "live":
                filters.append({"term": {TmSearchFields.ALIVE: True}})
            elif status == "dead":
                filters.append({"term": {TmSearchFields.ALIVE: False}})

        bool_query: Dict[str, Any] = {}
        if must:
            bool_query["must"] = must
        if filters:
            bool_query["filter"] = filters
        if not bool_query:
            bool_query["must"] = [{"match_all": {}}]

        return {
            "query": {"bool": bool_query},
            "from": offset,
            "size": min(limit, TrademarkDefaults.SEARCH_LIMIT_MAX),
            "track_total_hits": True,
        }

    @staticmethod
    def parse_search_response(raw: Dict[str, Any]) -> Dict[str, Any]:
        """Extract results and total from the search response envelope.

        The live service (verified 2026-06-10) returns a non-standard
        Elasticsearch envelope: {"hits": {"totalValue": N, "hits": [{"id":
        "<serial>", "source": {...}}]}}. Standard ES envelopes
        ({"total": {"value": N}}, "_source") are handled as fallbacks.

        Args:
            raw: Raw JSON response from the search endpoint

        Returns:
            {"results": [...], "total": N}
        """
        hits_obj = raw.get("hits")
        if not isinstance(hits_obj, dict):
            return {"results": [], "total": 0}

        hits = hits_obj.get("hits", [])
        results = []
        for hit in hits:
            if not isinstance(hit, dict):
                continue
            record = hit.get("source") or hit.get("_source") or hit
            # The serial number lives in the hit id; make sure it's on the record
            if isinstance(record, dict) and not record.get("id") and hit.get("id"):
                record = {**record, "id": hit["id"]}
            results.append(record)

        total = hits_obj.get("totalValue")
        if total is None:
            total = hits_obj.get("total", len(results))
        if isinstance(total, dict):
            total = total.get("value", len(results))

        return {"results": results, "total": total}

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
    async def make_request(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """POST a search body to the internal search endpoint.

        Args:
            body: Request body from build_search_body

        Returns:
            Raw JSON response or error dictionary
        """
        url = f"{config.TMSEARCH_BASE_URL}{SEARCH_PATH}"
        logger.info(f"Making tmsearch request to {url}")

        try:
            response = await self.client.post(
                url,
                json=body,
                timeout=config.REQUEST_TIMEOUT
            )

            # AWS WAF rejections surface as 403 (blocked) or 202 (challenge)
            if response.status_code in (202, 403):
                logger.error(f"AWS WAF rejection: {response.status_code}")
                error = ApiError.from_http_error(
                    status_code=response.status_code,
                    response_text=response.text[:500]
                )
                error["hint"] = (
                    "tmsearch.uspto.gov rejected the request at its AWS WAF "
                    "layer. Open https://tmsearch.uspto.gov in a browser, copy "
                    "the 'aws-waf-token' cookie value, and set the "
                    "TMSEARCH_WAF_TOKEN environment variable (token lasts ~4 "
                    "days). For authoritative status of a known mark, "
                    "tsdr_get_trademark_status does not use this service."
                )
                return error

            response.raise_for_status()

            try:
                return response.json()
            except Exception:
                # A 200 with non-JSON content is also a WAF challenge page
                return ApiError.create(
                    message=(
                        "tmsearch.uspto.gov returned a non-JSON response "
                        "(likely an AWS WAF challenge page). Set "
                        "TMSEARCH_WAF_TOKEN from a browser session and retry."
                    ),
                    status_code=response.status_code,
                    error_code="WAF_CHALLENGE",
                )

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            logger.error(f"HTTP error: {status_code} - {e.response.text}")
            error = ApiError.from_http_error(
                status_code=status_code,
                response_text=e.response.text
            )
            if status_code in (400, 404):
                error["hint"] = (
                    "tmsearch.uspto.gov is an undocumented internal API; this "
                    "failure may mean the endpoint or query shape has changed. "
                    "See the contract notes in tmsearch_client.py."
                )
            return error

        except (httpx.TimeoutException, httpx.NetworkError) as e:
            logger.warning(f"Network error (will retry): {str(e)}")
            raise  # Let tenacity handle the retry

        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return ApiError.from_exception(e, f"Request to {url} failed")

    async def search(
        self,
        query: Optional[str] = None,
        mark_text: Optional[str] = None,
        owner_name: Optional[str] = None,
        serial_number: Optional[str] = None,
        registration_number: Optional[str] = None,
        goods_services: Optional[str] = None,
        international_class: Optional[str] = None,
        status_filter: Optional[str] = None,
        offset: int = 0,
        limit: int = TrademarkDefaults.SEARCH_LIMIT,
    ) -> Dict[str, Any]:
        """Search trademarks and return a parsed {"results", "total"} dict.

        Returns:
            {"results": [...], "total": N} or error dictionary
        """
        body = self.build_search_body(
            query=query,
            mark_text=mark_text,
            owner_name=owner_name,
            serial_number=serial_number,
            registration_number=registration_number,
            goods_services=goods_services,
            international_class=international_class,
            status_filter=status_filter,
            offset=offset,
            limit=limit,
        )

        raw = await self.make_request(body)
        if raw.get("error", False) is True:
            return raw

        return self.parse_search_response(raw)

    async def get_by_serial(self, serial_number: str) -> Dict[str, Any]:
        """Get a trademark's search-index record by serial number.

        Args:
            serial_number: 8-digit application serial number

        Returns:
            {"results": [...], "total": N} or error dictionary
        """
        return await self.search(serial_number=serial_number, limit=1)

    async def close(self):
        """Close the client connections and clean up resources."""
        logger.info("Closing tmsearch client connections")
        await self.client.aclose()
