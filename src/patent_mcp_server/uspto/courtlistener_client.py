"""
CourtListener / RECAP API client — federal litigation documents.

Wraps the CourtListener REST API v4 (https://www.courtlistener.com/api/rest/v4),
operated by the Free Law Project, to retrieve the public briefs, motions,
judicial orders, and judicial opinions filed in federal patent lawsuits
(district courts) and appeals (Court of Appeals for the Federal Circuit, "cafc").

CourtListener is free and open. An API token is optional but recommended (it
raises the rate limit); set COURTLISTENER_API_KEY. Documents filed on PACER are
mirrored into the free RECAP archive when someone uploads them — coverage of
opinions (esp. CAFC) is excellent, individual district-court filings less so.
For filings not yet in RECAP, the RECAP Fetch endpoint can purchase them from
PACER (requires PACER_USERNAME / PACER_PASSWORD and incurs PACER per-page fees).

Auth: ``Authorization: Token <token>`` header.
Paginated list/search responses use the standard envelope
``{"count": N, "next": <url|null>, "previous": <url|null>, "results": [...]}``
with cursor-based pagination (follow the ``next`` URL's ``cursor`` value).
"""

import logging
from typing import Any, Optional, Dict
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
from patent_mcp_server.constants import HTTPMethods, LitigationDefaults

logger = logging.getLogger('courtlistener_client')


class CourtListenerClient:
    """Client for the CourtListener REST API v4 (Free Law Project)."""

    def __init__(self):
        self.base_url = f"{config.COURTLISTENER_BASE_URL}/api/rest/v4"
        self.headers = {
            "User-Agent": config.USER_AGENT,
            "Accept": "application/json",
        }
        # Token is optional — unauthenticated requests work at a lower rate limit.
        if config.COURTLISTENER_API_KEY:
            self.headers["Authorization"] = f"Token {config.COURTLISTENER_API_KEY}"

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
    async def _request(
        self,
        endpoint: str,
        method: str = HTTPMethods.GET,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make a request to the CourtListener API.

        Args:
            endpoint: API path beneath the v4 base (e.g. "/search/")
            method: HTTP method (GET for reads, POST for RECAP Fetch)
            params: Query parameters for GET requests (None values dropped)
            data: Form body for POST requests

        Returns:
            Response JSON dictionary or a standardized error dictionary.
        """
        url = f"{self.base_url}{endpoint}"
        if params:
            params = {k: v for k, v in params.items() if v is not None}
        logger.info(f"Making {method} request to {url}")

        try:
            if method == HTTPMethods.GET:
                response = await self.client.get(url, params=params)
            else:
                response = await self.client.post(url, data=data)

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            logger.error(f"HTTP error: {status_code} - {e.response.text}")
            # CourtListener serves search anonymously but requires a token for
            # detail endpoints (opinions, dockets, recap documents). Give a
            # clear, actionable message when the token is the likely cause.
            if status_code in (401, 403) and not config.COURTLISTENER_API_KEY:
                return ApiError.create(
                    message=(
                        "CourtListener returned an authentication error. This "
                        "endpoint requires a (free) API token. Get one at "
                        "https://www.courtlistener.com/profile/apis and set "
                        "COURTLISTENER_API_KEY. (Full-text search works without "
                        "a token; document/opinion/case retrieval does not.)"
                    ),
                    status_code=status_code,
                    error_code="COURTLISTENER_AUTH_REQUIRED",
                )
            try:
                error_json = e.response.json()
                return ApiError.from_http_error(
                    status_code=status_code,
                    response_text=e.response.text,
                    response_json=error_json,
                )
            except Exception:
                return ApiError.from_http_error(
                    status_code=status_code,
                    response_text=e.response.text,
                )

        except (httpx.TimeoutException, httpx.NetworkError) as e:
            logger.warning(f"Network error (will retry): {str(e)}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return ApiError.from_exception(e, "CourtListener API request failed")

    @staticmethod
    def _build_q(*terms: Optional[str]) -> Optional[str]:
        """Join free-text query terms into a single CourtListener `q` string.

        Multi-word terms (party names, patent numbers) are quoted so they are
        matched as phrases. Returns None when no terms are supplied.
        """
        parts = []
        for term in terms:
            if not term:
                continue
            term = str(term).strip()
            if not term:
                continue
            parts.append(f'"{term}"' if " " in term else term)
        return " ".join(parts) if parts else None

    # ------------------------------------------------------------------
    # Search endpoints (GET /search/?type=...)
    # ------------------------------------------------------------------

    async def search_dockets(
        self,
        query: Optional[str] = None,
        patent_number: Optional[str] = None,
        party: Optional[str] = None,
        court: Optional[str] = None,
        filed_after: Optional[str] = None,
        filed_before: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: int = LitigationDefaults.SEARCH_LIMIT,
    ) -> Dict[str, Any]:
        """Search federal dockets (cases) in the RECAP archive."""
        params = {
            "type": LitigationDefaults.SEARCH_TYPE_DOCKETS,
            "q": self._build_q(query, patent_number, party),
            "court": court,
            "filed_after": filed_after,
            "filed_before": filed_before,
            "cursor": cursor,
        }
        return await self._request("/search/", params=params)

    async def search_opinions(
        self,
        query: Optional[str] = None,
        patent_number: Optional[str] = None,
        court: Optional[str] = None,
        filed_after: Optional[str] = None,
        filed_before: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: int = LitigationDefaults.SEARCH_LIMIT,
    ) -> Dict[str, Any]:
        """Search judicial opinions (district court + Federal Circuit)."""
        params = {
            "type": LitigationDefaults.SEARCH_TYPE_OPINIONS,
            "q": self._build_q(query, patent_number),
            "court": court,
            "filed_after": filed_after,
            "filed_before": filed_before,
            "cursor": cursor,
        }
        return await self._request("/search/", params=params)

    async def search_recap_documents(
        self,
        docket_id: Optional[str] = None,
        query: Optional[str] = None,
        court: Optional[str] = None,
        filed_after: Optional[str] = None,
        filed_before: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: int = LitigationDefaults.SEARCH_LIMIT,
    ) -> Dict[str, Any]:
        """Search individual RECAP documents (briefs, motions, orders).

        Scope to one case with ``docket_id``; narrow by filing type with a
        keyword ``query`` (e.g. "brief", "order", "motion to dismiss").
        """
        params = {
            "type": LitigationDefaults.SEARCH_TYPE_RECAP_DOCS,
            "docket_id": docket_id,
            "q": self._build_q(query),
            "court": court,
            "filed_after": filed_after,
            "filed_before": filed_before,
            "cursor": cursor,
        }
        return await self._request("/search/", params=params)

    # ------------------------------------------------------------------
    # Detail endpoints
    # ------------------------------------------------------------------

    async def get_docket(self, docket_id: str) -> Dict[str, Any]:
        """Get a single docket (case) record by CourtListener docket id."""
        return await self._request(f"/dockets/{docket_id}/")

    async def list_docket_entries(
        self,
        docket_id: str,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List docket entries for a case (each entry nests its RECAP documents)."""
        params = {
            "docket": docket_id,
            "order_by": "recap_sequence_number",
            "cursor": cursor,
        }
        return await self._request("/docket-entries/", params=params)

    async def get_recap_document(self, recap_document_id: str) -> Dict[str, Any]:
        """Get a single RECAP document (one filing) by id.

        The record includes ``plain_text`` (extracted text, when available),
        ``filepath_local`` (PDF path), ``is_available`` (whether the PDF is in
        the archive), and PACER metadata.
        """
        return await self._request(f"/recap-documents/{recap_document_id}/")

    async def get_opinion(self, opinion_id: str) -> Dict[str, Any]:
        """Get a single judicial opinion by id (includes text and download URL)."""
        return await self._request(f"/opinions/{opinion_id}/")

    # ------------------------------------------------------------------
    # PACER fallback (RECAP Fetch) — purchases documents not yet in RECAP
    # ------------------------------------------------------------------

    async def fetch_from_pacer(
        self,
        recap_document_id: Optional[str] = None,
        docket_number: Optional[str] = None,
        court: Optional[str] = None,
        request_type: int = 2,
    ) -> Dict[str, Any]:
        """Queue a RECAP Fetch from PACER (credential-gated, incurs PACER fees).

        request_type: 1 = docket sheet, 2 = single PDF, 3 = attachment page.
        Returns the processing-queue record (poll its id later) or a clear
        error if PACER credentials are not configured.
        """
        if not (config.PACER_USERNAME and config.PACER_PASSWORD):
            return ApiError.create(
                message=(
                    "PACER credentials are not configured, so this document "
                    "cannot be fetched from PACER. It is not yet in the free "
                    "RECAP archive. Set PACER_USERNAME and PACER_PASSWORD to "
                    "enable on-demand fetches (note: PACER charges per page)."
                ),
                error_code="PACER_NOT_CONFIGURED",
            )

        data = {
            "request_type": request_type,
            "pacer_username": config.PACER_USERNAME,
            "pacer_password": config.PACER_PASSWORD,
        }
        if recap_document_id is not None:
            data["recap_document"] = recap_document_id
        if docket_number is not None:
            data["docket_number"] = docket_number
        if court is not None:
            data["court"] = court

        return await self._request(
            "/recap-fetch/", method=HTTPMethods.POST, data=data
        )

    async def close(self):
        """Close the client connections."""
        logger.info("Closing CourtListener client connections")
        await self.client.aclose()
