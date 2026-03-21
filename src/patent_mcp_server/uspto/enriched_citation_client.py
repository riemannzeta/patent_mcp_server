"""
USPTO Enriched Citation API Client

Provides access to the USPTO Enriched Citation metadata via the DS API
at api.uspto.gov. This Solr-based API contains ~1.2M enriched
citation records extracted from patent office actions (Oct 2017+).

Note: This API was decommissioned at developer.uspto.gov in early 2026.
Pending migration to api.uspto.gov (ODP). The client is preserved for
future reconnection once a replacement endpoint is available.
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

logger = logging.getLogger('enriched_citation_client')

DS_API_BASE = (
    "https://developer.uspto.gov/ds-api"  # Legacy - decommissioned early 2026
    "/enriched_cited_reference_metadata/1"
)


class EnrichedCitationClient:
    """Client for the USPTO Enriched Citation DS API.

    Searches enriched citation metadata extracted from patent
    office actions. Each record links a patent application to a
    cited reference with claim mappings, passage locations, and
    citation categories (X=anticipation, Y=obviousness, A=general).
    """

    def __init__(self):
        self.base_url = DS_API_BASE
        self.headers = {
            "User-Agent": config.USER_AGENT,
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
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.NetworkError)
        ),
        reraise=True
    )
    async def _search(
        self,
        criteria: str,
        start: int = 0,
        rows: int = 25,
    ) -> Dict[str, Any]:
        """Execute a Solr search against the DS API.

        Args:
            criteria: Solr query string (e.g. "patentApplicationNumber:16080156")
            start: Pagination offset
            rows: Number of results to return

        Returns:
            Parsed JSON response with 'response.docs' array.
        """
        url = f"{self.base_url}/records"
        form_data = {
            "criteria": criteria,
            "start": str(start),
            "rows": str(rows),
        }
        logger.info(
            f"DS API search: {criteria} (start={start}, rows={rows})"
        )

        try:
            response = await self.client.post(
                url,
                data=form_data,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            logger.error(
                f"HTTP error: {status_code} - {e.response.text}"
            )
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
            return ApiError.from_exception(
                e, "Enriched Citation DS API request failed"
            )

    def _format_response(
        self, raw: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Normalize DS API response into a consistent envelope."""
        if "error" in raw and raw.get("error"):
            return raw

        resp = raw.get("response", {})
        docs = resp.get("docs", [])
        num_found = resp.get("numFound", 0)

        citations = []
        for doc in docs:
            citations.append({
                "application_number": doc.get(
                    "patentApplicationNumber"
                ),
                "cited_document": doc.get(
                    "citedDocumentIdentifier"
                ),
                "citation_category": doc.get(
                    "citationCategoryCode"
                ),
                "rejected_claims": doc.get(
                    "relatedClaimNumberText"
                ),
                "passage_location": doc.get(
                    "passageLocationText"
                ),
                "office_action_date": doc.get(
                    "officeActionDate"
                ),
                "office_action_category": doc.get(
                    "officeActionCategory"
                ),
                "examiner_cited": doc.get(
                    "examinercitedreferenceindicator", False
                ),
                "inventor": doc.get("inventorNameText"),
                "quality": doc.get("qualitySummaryText"),
            })

        return {
            "result": {
                "error": False,
                "total": num_found,
                "count": len(citations),
                "citations": citations,
            }
        }

    async def get_patent_citations(
        self,
        patent_number: str,
        include_forward: bool = True,
        include_backward: bool = True,
    ) -> Dict[str, Any]:
        """Get enriched citation data for a patent application.

        Searches for all office action citations where this patent
        number appears as either the application or the cited ref.

        Args:
            patent_number: Patent or application number
            include_forward: Include records where this patent is cited
            include_backward: Include records where this patent cites

        Returns:
            Normalized citation data with claims and passages.
        """
        parts = []

        if include_backward:
            parts.append(
                f"patentApplicationNumber:{patent_number}"
            )
        if include_forward:
            parts.append(
                f"citedDocumentIdentifier:*{patent_number}*"
            )

        if not parts:
            return self._format_response(
                {"response": {"docs": [], "numFound": 0}}
            )

        criteria = " OR ".join(parts)
        raw = await self._search(criteria, rows=100)
        return self._format_response(raw)

    async def search_citations(
        self,
        query: Optional[str] = None,
        citing_patent: Optional[str] = None,
        cited_patent: Optional[str] = None,
        citation_category: Optional[str] = None,
        assignee: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        offset: int = 0,
        limit: int = 25,
    ) -> Dict[str, Any]:
        """Search enriched citation records.

        Args:
            query: Free-text Solr query
            citing_patent: Application number that is citing
            cited_patent: Document being cited (supports wildcards)
            citation_category: Category code (X, Y, A, D, etc.)
            assignee: Not available in DS API (ignored)
            date_from: Office action date range start (YYYY-MM-DD)
            date_to: Office action date range end (YYYY-MM-DD)
            offset: Starting position for pagination
            limit: Maximum results to return

        Returns:
            Normalized search results.
        """
        parts = []

        if query:
            parts.append(query)
        if citing_patent:
            parts.append(
                f"patentApplicationNumber:{citing_patent}"
            )
        if cited_patent:
            parts.append(
                f"citedDocumentIdentifier:*{cited_patent}*"
            )
        if citation_category:
            parts.append(
                f"citationCategoryCode:{citation_category}"
            )
        if date_from and date_to:
            parts.append(
                f"officeActionDate:"
                f"[{date_from}T00:00:00 TO {date_to}T23:59:59]"
            )
        elif date_from:
            parts.append(
                f"officeActionDate:"
                f"[{date_from}T00:00:00 TO *]"
            )
        elif date_to:
            parts.append(
                f"officeActionDate:"
                f"[* TO {date_to}T23:59:59]"
            )

        criteria = " AND ".join(parts) if parts else "*:*"
        raw = await self._search(criteria, start=offset, rows=limit)
        return self._format_response(raw)

    async def get_citation_metrics(
        self,
        patent_number: str,
    ) -> Dict[str, Any]:
        """Get citation metrics for a patent.

        Counts forward citations (where this patent is cited as
        prior art) and backward citations (references in this
        patent's office actions).

        Args:
            patent_number: Patent or application number

        Returns:
            Citation counts and category breakdown.
        """
        # Backward: this patent's office action citations
        backward_raw = await self._search(
            f"patentApplicationNumber:{patent_number}",
            rows=0,
        )
        backward_count = (
            backward_raw.get("response", {}).get("numFound", 0)
        )

        # Forward: citations of this patent by others
        forward_raw = await self._search(
            f"citedDocumentIdentifier:*{patent_number}*",
            rows=0,
        )
        forward_count = (
            forward_raw.get("response", {}).get("numFound", 0)
        )

        # Category breakdown (backward only)
        categories = {}
        if backward_count > 0:
            detail_raw = await self._search(
                f"patentApplicationNumber:{patent_number}",
                rows=min(backward_count, 500),
            )
            for doc in detail_raw.get(
                "response", {}
            ).get("docs", []):
                cat = doc.get("citationCategoryCode", "unknown")
                categories[cat] = categories.get(cat, 0) + 1

        return {
            "result": {
                "error": False,
                "patent_number": patent_number,
                "forward_citation_count": forward_count,
                "backward_citation_count": backward_count,
                "category_breakdown": categories,
            }
        }

    async def get_patent_family_citations(
        self,
        family_id: str,
    ) -> Dict[str, Any]:
        """Get citations for a patent family.

        Note: The DS API does not have a family ID field.
        This searches by the family_id as if it were an
        application number. For true family lookups, use
        the PatentsView API instead.

        Args:
            family_id: Patent family identifier or app number

        Returns:
            Citation data for the identifier.
        """
        return await self.get_patent_citations(family_id)

    async def close(self):
        """Close the client connections."""
        logger.info("Closing Enriched Citation client connections")
        await self.client.aclose()
