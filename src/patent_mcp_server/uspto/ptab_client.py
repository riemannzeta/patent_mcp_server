"""
USPTO PTAB API Client — live on the Open Data Portal (ODP v3.0).

PTAB data is served from https://api.uspto.gov under three search endpoints:

  - /api/v1/patent/trials/proceedings/search   (trial proceedings: IPR/PGR/CBM/DER)
  - /api/v1/patent/trials/documents/search     (documents filed in a proceeding)
  - /api/v1/patent/trials/decisions/search     (trial decisions)
  - /api/v1/patent/appeals/decisions/search    (ex parte appeal decisions)

Key contract facts (verified live 2026-05-18, see docs/plans/ptab-field-findings.md):

  * Appeals are NOT under /trials — they have their own /appeals base path.
  * There are no single-record /{id} routes. A specific proceeding/decision/
    appeal is fetched by issuing the corresponding search with a single
    `field:value` clause (trialNumber / appealNumber).
  * Filtering is done with a single `q=` parameter built from verified nested
    field names (trialMetaData.*, regularPetitionerData.*, patentOwnerData.*,
    appellantData.*, decisionData.*) plus optional free text. Flat parameter
    names (trialType, patentNumber, ...) do not exist on this API.
  * Interference proceedings are not offered on ODP (return 501).
"""

import logging
from typing import Any, Optional, Dict, List, Tuple

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
from patent_mcp_server.constants import Defaults, PTABFields

logger = logging.getLogger('ptab_client')


class PTABClient:
    """Client for USPTO PTAB data on the Open Data Portal (api.uspto.gov, v3.0).

    Provides access to Patent Trial and Appeal Board data including:
    - Trial proceedings (IPR, PGR, CBM, DER)
    - Trial documents
    - Trial decisions
    - Ex parte appeal decisions

    Interference proceedings are not available on ODP; the corresponding
    methods return a 501 error envelope.
    """

    def __init__(self):
        # Host only — each method passes the full path after the host.
        self.api_base = config.API_BASE_URL
        self.headers = {
            "User-Agent": config.USER_AGENT,
            "X-API-KEY": config.USPTO_API_KEY if config.USPTO_API_KEY else "",
            # Explicit Accept (sibling api_uspto_gov.py omits it): PTAB ODP
            # endpoints return JSON regardless, but we state the contract
            # explicitly to pin it against future content-negotiation changes.
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

    # ------------------------------------------------------------------ #
    # q= builders
    # ------------------------------------------------------------------ #

    @staticmethod
    def _build_q(
        free_text: Optional[str],
        clauses: List[Tuple[str, Any]],
    ) -> str:
        """Join a free-text term and `field:value` clauses (AND = space).

        Values containing whitespace are double-quoted so the value stays a
        single token. None-valued clauses are skipped.

        Range clauses (e.g. ``field:[A TO B]``) must NOT pass through here —
        their value contains spaces and would be wrongly double-quoted,
        breaking the range. Build them with `_range_clause` and pass them via
        the `raw` list of `_compose_q` instead.
        """
        parts: List[str] = []
        if free_text:
            parts.append(free_text)
        for field, value in clauses:
            if value is None:
                continue
            v = f'"{value}"' if " " in str(value) else str(value)
            parts.append(f"{field}:{v}")
        return " ".join(parts)

    @staticmethod
    def _range_clause(
        field: str,
        date_from: Optional[str],
        date_to: Optional[str],
    ) -> Optional[str]:
        """Build a pre-formatted ODP date-range clause, emitted verbatim.

        Returned string is appended to the q parts as-is (it bypasses
        `_build_q`'s whitespace quoting, which would otherwise wrap the
        bracketed range in double-quotes and break it).

          * both from & to -> ``field:[FROM TO TO]``
          * only from      -> ``field:>FROM``
          * only to        -> ``field:[* TO TO]``
          * neither        -> None

        Both ``[FROM TO TO]`` and ``>FROM`` are verified live. The only-to
        ``[* TO TO]`` form is best-effort (the ``*`` lower bound was not
        explicitly probed in Task 2); it is validated in the live smoke.
        """
        if date_from and date_to:
            return f"{field}:[{date_from} TO {date_to}]"
        if date_from:
            return f"{field}:>{date_from}"
        if date_to:
            return f"{field}:[* TO {date_to}]"
        return None

    @classmethod
    def _compose_q(
        cls,
        free_text: Optional[str],
        clauses: List[Tuple[str, Any]],
        raw: Optional[List[Optional[str]]] = None,
    ) -> str:
        """Compose a full q from free text, field clauses, and raw clauses.

        `raw` entries (typically range clauses) are appended verbatim,
        bypassing `_build_q`'s quoting.
        """
        q = cls._build_q(free_text, clauses)
        raw_parts = [r for r in (raw or []) if r]
        if raw_parts:
            q = " ".join(([q] if q else []) + raw_parts)
        return q

    # ------------------------------------------------------------------ #
    # HTTP
    # ------------------------------------------------------------------ #

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
        path: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make a GET request to the PTAB API.

        PTAB ODP endpoints are GET-only (see module docstring), so this is
        deliberately GET-only — there is no POST/body path.

        Args:
            path: Full API path after the host (e.g.
                ``/api/v1/patent/trials/proceedings/search``)
            params: Query parameters

        Returns:
            Response JSON dictionary or error dictionary
        """
        url = f"{self.api_base}{path}"
        logger.info(f"Making GET request to {url}")

        try:
            response = await self.client.get(url, params=params)
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
            return ApiError.from_exception(e, "PTAB API request failed")

    # ------------------------------------------------------------------ #
    # Trial proceedings
    # ------------------------------------------------------------------ #

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

        Maps logical filters to verified ODP `q=` field clauses
        (see docs/plans/ptab-field-findings.md). `query` is free text.

        Args:
            query: Free-text search term
            trial_type: Trial type code (IPR, PGR, CBM, DER)
            patent_number: Subject patent number
            party_name: Petitioner real-party-in-interest name
            filing_date_from: Petition filing date range start (YYYY-MM-DD)
            filing_date_to: Petition filing date range end (YYYY-MM-DD)
            status: Trial status category (e.g. Terminated, Pending)
            offset: Starting position for pagination
            limit: Maximum results to return

        Returns:
            Dictionary containing search results
        """
        q = self._compose_q(
            query,
            [
                (PTABFields.TRIAL_TYPE, trial_type),
                (PTABFields.PATENT_NUMBER, patent_number),
                (PTABFields.PETITIONER_NAME, party_name),
                (PTABFields.STATUS, status),
            ],
            raw=[
                self._range_clause(
                    PTABFields.PETITION_FILING_DATE,
                    filing_date_from,
                    filing_date_to,
                )
            ],
        )
        params: Dict[str, Any] = {"offset": offset, "limit": limit}
        if q:
            params["q"] = q
        return await self._make_request(
            "/api/v1/patent/trials/proceedings/search", params=params
        )

    async def get_proceeding(self, proceeding_number: str) -> Dict[str, Any]:
        """Get a specific PTAB proceeding.

        No single-record route exists on ODP; this issues a proceedings
        search keyed on the trial number.

        Args:
            proceeding_number: The proceeding/trial number (e.g. IPR2022-00001)

        Returns:
            Dictionary containing the matching proceeding(s)
        """
        params = {
            "q": self._build_q(
                None, [(PTABFields.TRIAL_NUMBER, proceeding_number)]
            )
        }
        return await self._make_request(
            "/api/v1/patent/trials/proceedings/search", params=params
        )

    async def get_proceeding_documents(
        self,
        proceeding_number: str,
        document_type: Optional[str] = None,
        offset: int = Defaults.SEARCH_START,
        limit: int = Defaults.API_LIMIT,
    ) -> Dict[str, Any]:
        """Get documents filed in a PTAB proceeding.

        Uses the documents search endpoint keyed on the trial number.
        `document_type` has no verified field name, so it is folded into the
        free-text portion of `q` (best-effort).

        Args:
            proceeding_number: The proceeding/trial number
            document_type: Document type term (free text — unverified field)
            offset: Starting position for pagination
            limit: Maximum results to return

        Returns:
            Dictionary containing the document list
        """
        # document_type is passed as free text, not phrase-quoted: multi-word
        # unverified terms are deliberately left un-quoted (best-effort loose
        # match until the field name is probed).
        q = self._compose_q(
            document_type,
            [(PTABFields.TRIAL_NUMBER, proceeding_number)],
        )
        params: Dict[str, Any] = {"offset": offset, "limit": limit}
        if q:
            params["q"] = q
        return await self._make_request(
            "/api/v1/patent/trials/documents/search", params=params
        )

    # ------------------------------------------------------------------ #
    # Trial decisions
    # ------------------------------------------------------------------ #

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

        `query` and `decision_type` are free text (decision_type has no
        verified field name). proceeding_number/patent_number/date range map
        to verified clauses.

        Args:
            query: Free-text search term
            decision_type: Decision type term (free text — unverified field)
            proceeding_number: Trial number
            patent_number: Subject patent number
            decision_date_from: Decision issue date range start (YYYY-MM-DD)
            decision_date_to: Decision issue date range end (YYYY-MM-DD)
            offset: Starting position for pagination
            limit: Maximum results to return

        Returns:
            Dictionary containing decision search results
        """
        # decision_type folds into free text, not phrase-quoted: multi-word
        # unverified terms are deliberately left un-quoted (best-effort loose
        # match until the field name is probed).
        free_text = " ".join(t for t in (query, decision_type) if t) or None
        q = self._compose_q(
            free_text,
            [
                (PTABFields.TRIAL_NUMBER, proceeding_number),
                (PTABFields.PATENT_NUMBER, patent_number),
            ],
            raw=[
                self._range_clause(
                    PTABFields.DECISION_ISSUE_DATE,
                    decision_date_from,
                    decision_date_to,
                )
            ],
        )
        params: Dict[str, Any] = {"offset": offset, "limit": limit}
        if q:
            params["q"] = q
        return await self._make_request(
            "/api/v1/patent/trials/decisions/search", params=params
        )

    async def get_decision(self, decision_id: str) -> Dict[str, Any]:
        """Get a specific PTAB trial decision.

        No decision-id route exists on ODP, and decisions are not keyed by a
        standalone decision id — they are keyed by trial number. This issues a
        decisions search on the trial number.

        Args:
            decision_id: The trial number identifying the decision

        Returns:
            Dictionary containing the matching decision(s)
        """
        params = {
            "q": self._build_q(
                None, [(PTABFields.TRIAL_NUMBER, decision_id)]
            )
        }
        return await self._make_request(
            "/api/v1/patent/trials/decisions/search", params=params
        )

    # ------------------------------------------------------------------ #
    # Ex parte appeal decisions (separate /appeals base path)
    # ------------------------------------------------------------------ #

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

        Appeals live under /api/v1/patent/appeals (NOT under /trials) and use
        the appellantData path for application numbers. patentOwnerData.* was
        not verified on this endpoint, so `patent_number` is folded into free
        text rather than shipped as an unverified clause.

        Args:
            query: Free-text search term
            application_number: Appeal application number (appellantData path)
            patent_number: Subject patent number (free text — unverified field)
            appeal_number: The appeal number
            decision_date_from: Decision issue date range start (YYYY-MM-DD)
            decision_date_to: Decision issue date range end (YYYY-MM-DD)
            offset: Starting position for pagination
            limit: Maximum results to return

        Returns:
            Dictionary containing appeal search results
        """
        free_text = " ".join(t for t in (query, patent_number) if t) or None
        q = self._compose_q(
            free_text,
            [
                (PTABFields.APPEAL_NUMBER, appeal_number),
                (PTABFields.APPEAL_APPLICATION_NUMBER, application_number),
            ],
            raw=[
                self._range_clause(
                    PTABFields.DECISION_ISSUE_DATE,
                    decision_date_from,
                    decision_date_to,
                )
            ],
        )
        params: Dict[str, Any] = {"offset": offset, "limit": limit}
        if q:
            params["q"] = q
        return await self._make_request(
            "/api/v1/patent/appeals/decisions/search", params=params
        )

    async def get_appeal_decision(self, appeal_number: str) -> Dict[str, Any]:
        """Get a specific ex parte appeal decision.

        No single-record route exists; issues an appeals search keyed on the
        appeal number.

        Args:
            appeal_number: The appeal number

        Returns:
            Dictionary containing the matching appeal decision(s)
        """
        params = {
            "q": self._build_q(
                None, [(PTABFields.APPEAL_NUMBER, appeal_number)]
            )
        }
        return await self._make_request(
            "/api/v1/patent/appeals/decisions/search", params=params
        )

    # Thin alias — Task 4 wiring calls ptab_client.get_appeal.
    get_appeal = get_appeal_decision

    # ------------------------------------------------------------------ #
    # Interferences — not offered on ODP
    # ------------------------------------------------------------------ #

    async def search_interferences(
        self,
        query: Optional[str] = None,
        interference_number: Optional[str] = None,
        patent_number: Optional[str] = None,
        party_name: Optional[str] = None,
        offset: int = Defaults.SEARCH_START,
        limit: int = Defaults.API_LIMIT,
    ) -> Dict[str, Any]:
        """Search historical interference proceedings.

        Not available: the USPTO Open Data Portal does not expose an
        interference route. Returns a 501 error envelope.
        """
        return ApiError.create(
            message=(
                "PTAB interference proceedings are not available on the "
                "USPTO Open Data Portal."
            ),
            status_code=501,
        )

    async def get_interference(self, interference_number: str) -> Dict[str, Any]:
        """Get a specific interference proceeding.

        Not available: the USPTO Open Data Portal does not expose an
        interference route. Returns a 501 error envelope.
        """
        return ApiError.create(
            message=(
                "PTAB interference proceedings are not available on the "
                "USPTO Open Data Portal."
            ),
            status_code=501,
        )

    async def close(self):
        """Close the client connections."""
        logger.info("Closing PTAB client connections")
        await self.client.aclose()
