"""
USPTO Office Action Citations and Rejections (ODP)

The two claim-level office action datasets answer on the Open Data Portal
(verified live 2026-10-15):

    POST {API_BASE_URL}/api/v1/patent/oa/oa_rejections/v2/records
    POST {API_BASE_URL}/api/v1/patent/oa/oa_citations/v2/records

Both take a form-encoded Solr query (``criteria``, ``start``, ``rows``) and
answer ``{"response": {"start", "numFound", "docs": [...]}}``. A query that
matches nothing answers 200 with ``numFound`` 0; a query Solr cannot parse
answers 200 with ``{}``. ``rows`` has no server-side cap, so callers clamp it.

Rejections hold ~93M rows from 2012 on, several per office action: one per
claim group and statute, extracted by machine from the action's text.
Citations hold one row per reference an action cites. Rows appear about a
week after the action is mailed.

The developer.uspto.gov paths this client used to call
(``/ds-api/oa-text/v1``, ``/ds-api/oa-citations/v2/search``,
``/ds-api/oa-rejections/v2/search``) were decommissioned in early 2026.
Office action text now comes from ``odp_search_office_actions`` and
``odp_download_document``.
"""

import asyncio
import logging
from typing import Any, Dict

import httpx2
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from patent_mcp_server.util.logging import LoggingTransport
from patent_mcp_server.util.errors import ApiError, retry_after_seconds
from patent_mcp_server.config import config

logger = logging.getLogger('office_action_client')

REJECTIONS = "oa_rejections"
CITATIONS = "oa_citations"


class OfficeActionClient:
    """Client for the ODP office action rejection and citation datasets."""

    def __init__(self):
        self.base_url = config.API_BASE_URL
        self.headers = {
            "User-Agent": config.USER_AGENT,
            "Accept": "application/json",
        }

        transport = httpx2.AsyncHTTPTransport()
        logging_transport = LoggingTransport(transport)

        self.client = httpx2.AsyncClient(
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

    def records_url(self, dataset: str) -> str:
        return f"{self.base_url}/api/v1/patent/oa/{dataset}/v2/records"

    @retry(
        stop=stop_after_attempt(config.MAX_RETRIES),
        wait=wait_exponential(
            multiplier=config.RETRY_DELAY,
            min=config.RETRY_MIN_WAIT,
            max=config.RETRY_MAX_WAIT
        ),
        retry=retry_if_exception_type((httpx2.TimeoutException, httpx2.NetworkError)),
        reraise=True
    )
    async def search_records(
        self,
        dataset: str,
        criteria: str,
        start: int = 0,
        rows: int = 25,
    ) -> Dict[str, Any]:
        """Run a Solr query against one dataset.

        Args:
            dataset: REJECTIONS or CITATIONS
            criteria: Solr/Lucene query (e.g. patentApplicationNumber:"18402543")
            start: Offset of the first row
            rows: Number of rows to return

        Returns:
            {"total": numFound, "docs": [...]} or an error dictionary
        """
        url = self.records_url(dataset)
        # The API key goes per request so a key set after import still works.
        headers = {"X-API-KEY": config.USPTO_API_KEY or ""}
        form = {"criteria": criteria, "start": str(start), "rows": str(rows)}
        logger.info(f"POST {url} criteria={criteria!r} start={start} rows={rows}")

        try:
            for attempt in range(config.MAX_RETRIES):
                response = await self.client.post(url, headers=headers, data=form)
                # api.uspto.gov rate-limits per key; wait and try again.
                if response.status_code == 429 and attempt < config.MAX_RETRIES - 1:
                    delay = retry_after_seconds(response, attempt)
                    logger.warning(f"ODP API rate limit (429); retrying in {delay:.0f}s")
                    await asyncio.sleep(delay)
                    continue
                response.raise_for_status()
                break
            payload = response.json()

        except httpx2.HTTPStatusError as e:
            status_code = e.response.status_code
            logger.error(f"HTTP error: {status_code} - {e.response.text}")
            try:
                return ApiError.from_http_error(
                    status_code=status_code,
                    response_text=e.response.text,
                    response_json=e.response.json(),
                )
            except Exception:
                return ApiError.from_http_error(
                    status_code=status_code,
                    response_text=e.response.text,
                )

        except (httpx2.TimeoutException, httpx2.NetworkError) as e:
            logger.warning(f"Network error (will retry): {str(e)}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return ApiError.from_exception(e, "Office action dataset request failed")

        body = payload.get("response") if isinstance(payload, dict) else None
        if not isinstance(body, dict):
            # Solr answers an unparseable query with 200 and an empty object.
            return ApiError.create(
                message=f"The {dataset} dataset could not parse the query: {criteria}",
                error_code="QUERY_ERROR",
                status_code=400,
            )
        return {"total": body.get("numFound", 0), "docs": body.get("docs") or []}

    async def close(self):
        """Close the client connections."""
        logger.info("Closing Office Action client connections")
        await self.client.aclose()
