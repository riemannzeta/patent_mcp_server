"""Integration tests for the federal litigation (CourtListener / RECAP) tools.

These make real network calls to CourtListener and are skipped by default.
Run with: pytest test/integration/test_litigation_integration.py -m integration

A COURTLISTENER_API_KEY is not strictly required (the API serves
unauthenticated requests at a lower rate limit), so these tests run without one
but will tolerate rate-limit / transient errors gracefully.
"""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

from patent_mcp_server.patents import (
    litigation_search_opinions,
    litigation_search_cases,
    litigation_get_opinion,
)


def _skip_if_unreachable(result):
    if isinstance(result, dict) and result.get("error"):
        pytest.skip(f"CourtListener unavailable/rate-limited: {result.get('message')}")


async def test_search_cafc_opinions_live():
    """Search Federal Circuit opinions for a patent topic."""
    result = await litigation_search_opinions(
        query="claim construction", court="cafc", limit=5)
    _skip_if_unreachable(result)
    assert result["success"] is True
    assert result["source"] == "courtlistener"
    assert isinstance(result["results"], list)


async def test_search_cases_by_patent_live():
    """Search dockets referencing a well-litigated patent number."""
    result = await litigation_search_cases(patent_number="7479949", limit=5)
    _skip_if_unreachable(result)
    assert result["success"] is True
    assert result["source"] == "courtlistener"


async def test_get_opinion_round_trip_live():
    """Search for an opinion, then fetch its full text by id."""
    search = await litigation_search_opinions(
        query="patent infringement", court="cafc", limit=5)
    _skip_if_unreachable(search)
    results = search.get("results") or []
    if not results:
        pytest.skip("No opinions returned to round-trip")
    # CourtListener search results expose the opinion id under "id" or "cluster_id"
    opinion_id = results[0].get("id") or results[0].get("cluster_id")
    if not opinion_id:
        pytest.skip("Search result had no opinion id to fetch")
    detail = await litigation_get_opinion(opinion_id=str(opinion_id))
    _skip_if_unreachable(detail)
    assert detail["success"] is True
