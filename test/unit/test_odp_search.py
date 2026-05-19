"""Unit tests for odp_search_applications.

Covers:
- Post-slicing to honor user limit (issue #18).
- Lucene-`q` POST request shape for assignee/inventor/date/etc. filters
  (issue #21 — the GET query-string filters were silently dropped upstream).
"""

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


# ---------------------------------------------------------------------------
# Issue #21: filters must be sent in a Lucene `q` POST body, not GET params.
# ---------------------------------------------------------------------------

@pytest.mark.unit
async def test_assignee_filter_sent_as_lucene_post():
    """assignee_name must produce a POST with a Lucene clause on
    applicationMetaData.firstApplicantName (issue #21)."""
    mock_request = AsyncMock(return_value=_fake_upstream_response(0))
    with patch(
        "patent_mcp_server.patents.api_client.make_request",
        new=mock_request,
    ):
        await odp_search_applications(assignee_name="IBM", limit=5)

    args, kwargs = mock_request.call_args
    assert kwargs.get("method") == "POST"
    body = kwargs.get("data")
    assert body is not None
    assert 'applicationMetaData.firstApplicantName:"IBM"' in body["q"]
    assert body["pagination"] == {"offset": 0, "limit": 5}


@pytest.mark.unit
async def test_multiple_filters_are_ANDed_in_q():
    """Multiple typed filters must be AND-ed in the Lucene `q` string."""
    mock_request = AsyncMock(return_value=_fake_upstream_response(0))
    with patch(
        "patent_mcp_server.patents.api_client.make_request",
        new=mock_request,
    ):
        await odp_search_applications(
            assignee_name="NVIDIA Corporation",
            inventor_name="Smith",
            filing_date_from="2024-01-01",
            filing_date_to="2024-12-31",
            limit=5,
        )

    body = mock_request.call_args.kwargs["data"]
    q = body["q"]
    assert ' AND ' in q
    assert 'applicationMetaData.firstApplicantName:"NVIDIA Corporation"' in q
    assert 'applicationMetaData.firstInventorName:"Smith"' in q
    assert 'applicationMetaData.filingDate:[2024-01-01 TO 2024-12-31]' in q


@pytest.mark.unit
async def test_free_text_query_is_wrapped_and_combined():
    """A free-text `query` should be parenthesised and AND-combined with
    typed filters so it doesn't accidentally bind to the wrong clause."""
    mock_request = AsyncMock(return_value=_fake_upstream_response(0))
    with patch(
        "patent_mcp_server.patents.api_client.make_request",
        new=mock_request,
    ):
        await odp_search_applications(
            query="neural network",
            assignee_name="IBM",
            limit=5,
        )

    q = mock_request.call_args.kwargs["data"]["q"]
    assert "(neural network)" in q
    assert 'applicationMetaData.firstApplicantName:"IBM"' in q
    assert ' AND ' in q


@pytest.mark.unit
async def test_quotes_in_value_are_escaped():
    """Embedded quotes in a filter value must be escaped, not break the
    Lucene query."""
    mock_request = AsyncMock(return_value=_fake_upstream_response(0))
    with patch(
        "patent_mcp_server.patents.api_client.make_request",
        new=mock_request,
    ):
        await odp_search_applications(assignee_name='ACME "BIG" CORP', limit=5)

    q = mock_request.call_args.kwargs["data"]["q"]
    # Embedded quotes must be backslash-escaped inside the surrounding quotes.
    assert r'applicationMetaData.firstApplicantName:"ACME \"BIG\" CORP"' in q


@pytest.mark.unit
async def test_no_filters_returns_missing_filter_error():
    """Without any filter we'd dump the entire 12.8M-record corpus, so the
    tool must refuse (issue #21)."""
    mock_request = AsyncMock(return_value=_fake_upstream_response(0))
    with patch(
        "patent_mcp_server.patents.api_client.make_request",
        new=mock_request,
    ):
        result = await odp_search_applications()

    assert result.get("error") is True
    assert result.get("error_code") == "MISSING_FILTER"
    # And we must not have called upstream.
    mock_request.assert_not_called()
