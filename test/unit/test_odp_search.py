"""Unit tests for odp_search_applications post-slicing (issue #18)."""

from unittest.mock import AsyncMock, patch

import pytest

from patent_mcp_server.patents import odp_search_applications


def _fake_upstream_response(num_records: int) -> dict:
    """Build a fake ODP /applications/search response with N file wrappers."""
    return {
        "count": num_records,
        "patentFileWrapperDataBag": [
            {
                "applicationNumberText": f"1612345{i}",
                "applicationMetaData": {"filingDate": "2020-01-01"},
                "eventDataBag": [{"event": f"e{i}"}],
            }
            for i in range(num_records)
        ],
    }


@pytest.mark.unit
async def test_search_post_slices_to_user_limit():
    """Upstream returns 20 records but caller asked for limit=3 → 3 returned."""
    upstream = _fake_upstream_response(20)
    with patch(
        "patent_mcp_server.patents.api_client.make_request",
        new=AsyncMock(return_value=upstream),
    ):
        result = await odp_search_applications(query="knowledge graph", limit=3)

    assert result["success"] is True
    assert result["count"] == 3
    assert len(result["results"]) == 3
    assert result["limit"] == 3
    # has_more should reflect that more records exist beyond what we returned.
    assert result["total"] == 20
    assert result["has_more"] is True


@pytest.mark.unit
async def test_search_passes_through_when_upstream_under_limit():
    """If upstream already returns ≤ limit, no slicing changes anything."""
    upstream = _fake_upstream_response(2)
    with patch(
        "patent_mcp_server.patents.api_client.make_request",
        new=AsyncMock(return_value=upstream),
    ):
        result = await odp_search_applications(query="anything", limit=10)

    assert result["count"] == 2
    assert len(result["results"]) == 2


@pytest.mark.unit
async def test_search_propagates_upstream_error():
    """When the API client returns an error dict, we don't try to slice it."""
    error = {"error": True, "message": "boom", "error_code": "HTTP_500"}
    with patch(
        "patent_mcp_server.patents.api_client.make_request",
        new=AsyncMock(return_value=error),
    ):
        result = await odp_search_applications(query="anything", limit=3)

    assert result == error


@pytest.mark.unit
async def test_search_handles_empty_databag():
    """No patentFileWrapperDataBag in response shouldn't crash."""
    upstream = {"count": 0}
    with patch(
        "patent_mcp_server.patents.api_client.make_request",
        new=AsyncMock(return_value=upstream),
    ):
        result = await odp_search_applications(query="nothing", limit=3)

    # Without the bag, from_odp falls through to the "direct data" branch.
    assert result["success"] is True
