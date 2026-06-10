"""Unit tests for TmAssignmentClient (ODP-first with legacy XML fallback)."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from patent_mcp_server.uspto.tm_assignment_client import (
    TmAssignmentClient, ODP_SEARCH_PATH, LEGACY_SEARCH_PATH
)
from patent_mcp_server.config import config

from test.fixtures.tm_assignment_responses import (
    MOCK_TM_ASSIGNMENT_ODP_RESPONSE,
    MOCK_TM_ASSIGNMENT_LEGACY_XML,
)


@pytest.fixture
async def tm_client():
    """Create a TmAssignmentClient instance for testing."""
    client = TmAssignmentClient()
    yield client
    await client.close()


def _mock_response(status_code=200, json_data=None, text=""):
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.text = text
    if json_data is not None:
        response.json.return_value = json_data
        import json as _json
        response.text = _json.dumps(json_data)
    else:
        response.json.side_effect = ValueError("no json")
    return response


# ============================================================================
# Initialization Tests
# ============================================================================

@pytest.mark.unit
async def test_client_initialization():
    """Client sends the X-API-KEY header for the ODP backend."""
    client = TmAssignmentClient()

    assert "X-API-KEY" in client.headers
    assert client._backend is None

    await client.close()


@pytest.mark.unit
async def test_client_context_manager():
    async with TmAssignmentClient() as client:
        assert client is not None


# ============================================================================
# Filter Validation Tests
# ============================================================================

@pytest.mark.unit
async def test_at_least_one_filter_required(tm_client):
    """No filters at all returns a MISSING_FILTER error without a request."""
    result = await tm_client.search_assignments()

    assert result["error"] is True
    assert result["error_code"] == "MISSING_FILTER"


# ============================================================================
# Backend Selection Tests
# ============================================================================

@pytest.mark.unit
async def test_odp_tried_first_and_used_on_success(tm_client):
    """A working ODP endpoint is used and cached as the backend."""
    with patch.object(tm_client, "_get", new_callable=AsyncMock) as m:
        m.return_value = _mock_response(200, json_data=MOCK_TM_ASSIGNMENT_ODP_RESPONSE)
        result = await tm_client.search_assignments(registration_number="3500027")

    assert result["backend"] == "odp"
    assert tm_client._backend == "odp"
    assert result["total"] == 1
    assert result["results"][0]["reelNumber"] == "1234"

    called_url = m.call_args[0][0]
    assert called_url.startswith(f"{config.API_BASE_URL}{ODP_SEARCH_PATH}")


@pytest.mark.unit
async def test_404_triggers_legacy_fallback(tm_client):
    """ODP 404 falls back to the legacy XML API."""
    odp_404 = _mock_response(404, text="Not found")
    legacy_ok = _mock_response(200, text=MOCK_TM_ASSIGNMENT_LEGACY_XML)

    with patch.object(tm_client, "_get", new_callable=AsyncMock) as m:
        m.side_effect = [odp_404, legacy_ok]
        result = await tm_client.search_assignments(assignee_name="New Owner LLC")

    assert result["backend"] == "legacy"
    assert tm_client._backend == "legacy"
    assert result["total"] == 2
    assert m.call_count == 2

    legacy_url = m.call_args_list[1][0][0]
    assert legacy_url.startswith(f"{config.TM_ASSIGNMENT_BASE_URL}{LEGACY_SEARCH_PATH}")


@pytest.mark.unit
async def test_legacy_backend_cached_skips_odp(tm_client):
    """Once legacy is cached, ODP is not probed again."""
    tm_client._backend = "legacy"

    with patch.object(tm_client, "_get", new_callable=AsyncMock) as m:
        m.return_value = _mock_response(200, text=MOCK_TM_ASSIGNMENT_LEGACY_XML)
        result = await tm_client.search_assignments(assignor_name="Old Owner Corp")

    assert m.call_count == 1
    assert result["backend"] == "legacy"
    called_url = m.call_args[0][0]
    assert called_url.startswith(config.TM_ASSIGNMENT_BASE_URL)


@pytest.mark.unit
async def test_odp_non_404_error_does_not_fall_back(tm_client):
    """A real ODP error (e.g. 403) is surfaced, not masked by fallback."""
    with patch.object(tm_client, "_get", new_callable=AsyncMock) as m:
        m.return_value = _mock_response(403, text="Forbidden")
        result = await tm_client.search_assignments(registration_number="3500027")

    assert result["error"] is True
    assert result["status_code"] == 403
    assert m.call_count == 1


# ============================================================================
# Legacy XML Parsing Tests
# ============================================================================

@pytest.mark.unit
async def test_parse_legacy_xml(tm_client):
    """Solr-style XML docs are converted into dicts with arrays."""
    parsed = tm_client._parse_legacy_xml(MOCK_TM_ASSIGNMENT_LEGACY_XML)

    assert parsed["total"] == 2
    first = parsed["results"][0]
    assert first["reelNo"] == "1234"
    assert first["assignorName"] == ["Old Owner Corp"]
    assert first["assigneeName"] == ["New Owner LLC"]


@pytest.mark.unit
async def test_parse_legacy_xml_invalid(tm_client):
    """Invalid XML returns an error dict."""
    parsed = tm_client._parse_legacy_xml("this is not xml <<<")
    assert parsed["error"] is True


@pytest.mark.unit
async def test_parse_legacy_xml_no_results(tm_client):
    """XML without a result element returns empty results."""
    parsed = tm_client._parse_legacy_xml("<response></response>")
    assert parsed == {"results": [], "total": 0}


# ============================================================================
# ODP Query Building Tests
# ============================================================================

@pytest.mark.unit
async def test_odp_query_clauses(tm_client):
    """All filters land in the Lucene q= parameter."""
    with patch.object(tm_client, "_get", new_callable=AsyncMock) as m:
        m.return_value = _mock_response(200, json_data={"count": 0, "results": []})
        await tm_client.search_assignments(
            serial_number="78787878",
            assignee_name="New Owner LLC",
        )

    called_url = m.call_args[0][0]
    assert "applicationNumberText%3A78787878" in called_url
    assert "assigneeName" in called_url
