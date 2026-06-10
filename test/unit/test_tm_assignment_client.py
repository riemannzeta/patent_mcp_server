"""Unit tests for TmAssignmentClient (USPTO Assignment Center backend)."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from patent_mcp_server.uspto.tm_assignment_client import (
    TmAssignmentClient, SEARCH_PATH, MAX_ROWS_PER_REQUEST
)
from patent_mcp_server.config import config

from test.fixtures.tm_assignment_responses import (
    MOCK_TM_ASSIGNMENT_RESPONSE,
    MOCK_TM_ASSIGNMENT_EMPTY_RESPONSE,
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
    """Assignment Center is a public API — no API key header is sent."""
    client = TmAssignmentClient()

    assert "X-API-KEY" not in client.headers
    assert client.headers["Content-Type"] == "application/json"

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
# Search Criteria Building Tests (pure function)
# ============================================================================

@pytest.mark.unit
def test_build_search_criteria_single_filter():
    """A single filter maps to its Assignment Center searchBy name."""
    criteria = TmAssignmentClient.build_search_criteria(
        {"assignee_name": "New Owner LLC"}, offset=0, limit=25
    )

    assert {"property": "New Owner LLC", "searchBy": "assigneeName"} in criteria
    assert {"property": "25", "searchBy": "rowsNeeded"} in criteria
    # No startRow/endRow when offset is 0
    assert not any(c["searchBy"] in ("startRow", "endRow") for c in criteria)


@pytest.mark.unit
def test_build_search_criteria_all_filters():
    """All filters land in the criteria list with correct field names."""
    criteria = TmAssignmentClient.build_search_criteria(
        {
            "serial_number": "78787878",
            "registration_number": "3500027",
            "assignee_name": "New Owner LLC",
            "assignor_name": "Old Owner Corp",
            "reel_frame": "1234/0567",
        },
        offset=0,
        limit=10,
    )

    search_bys = {c["searchBy"] for c in criteria}
    assert {"serialNumber", "registrationNumber", "assigneeName",
            "assignorName", "reelFrame", "rowsNeeded"} <= search_bys


@pytest.mark.unit
def test_build_search_criteria_pagination():
    """Offset converts to 1-based startRow/endRow criteria."""
    criteria = TmAssignmentClient.build_search_criteria(
        {"assignee_name": "X"}, offset=50, limit=25
    )

    assert {"property": "51", "searchBy": "startRow"} in criteria
    assert {"property": "75", "searchBy": "endRow"} in criteria
    assert {"property": "25", "searchBy": "rowsNeeded"} in criteria


@pytest.mark.unit
def test_build_search_criteria_caps_limit():
    """Limits above the API maximum are capped."""
    criteria = TmAssignmentClient.build_search_criteria(
        {"assignee_name": "X"}, offset=0, limit=99999
    )

    assert {"property": str(MAX_ROWS_PER_REQUEST), "searchBy": "rowsNeeded"} in criteria


# ============================================================================
# Response Parsing Tests (pure function)
# ============================================================================

@pytest.mark.unit
def test_parse_search_response():
    """The list-wrapped envelope is unwrapped into results/total."""
    parsed = TmAssignmentClient.parse_search_response(MOCK_TM_ASSIGNMENT_RESPONSE)

    assert parsed["total"] == 2
    assert parsed["results"][0]["reelNumber"] == 1234
    assert parsed["results"][0]["assignees"] == ["New Owner LLC"]


@pytest.mark.unit
def test_parse_search_response_empty():
    """Empty data list parses to zero results."""
    parsed = TmAssignmentClient.parse_search_response(MOCK_TM_ASSIGNMENT_EMPTY_RESPONSE)

    assert parsed == {"results": [], "total": 0}


@pytest.mark.unit
def test_parse_search_response_unexpected_shape():
    """Garbage input degrades to empty results, not an exception."""
    assert TmAssignmentClient.parse_search_response(None) == {"results": [], "total": 0}
    assert TmAssignmentClient.parse_search_response([]) == {"results": [], "total": 0}
    assert TmAssignmentClient.parse_search_response("nope") == {"results": [], "total": 0}


# ============================================================================
# Search Flow Tests
# ============================================================================

@pytest.mark.unit
async def test_search_assignments_success(tm_client):
    """A successful search POSTs to the Assignment Center endpoint."""
    with patch.object(tm_client, "_post", new_callable=AsyncMock) as m:
        m.return_value = _mock_response(200, json_data=MOCK_TM_ASSIGNMENT_RESPONSE)
        result = await tm_client.search_assignments(assignee_name="New Owner LLC")

    assert result["backend"] == "assignment-center"
    assert result["total"] == 2
    assert result["results"][0]["reelNumber"] == 1234

    called_url = m.call_args[0][0]
    assert called_url == f"{config.TM_ASSIGNMENT_BASE_URL}{SEARCH_PATH}"
    body = m.call_args[0][1]
    assert {"property": "New Owner LLC", "searchBy": "assigneeName"} in body["searchCriteria"]


@pytest.mark.unit
async def test_search_assignments_combined_filters(tm_client):
    """Multiple filters all appear in the request body (AND semantics)."""
    with patch.object(tm_client, "_post", new_callable=AsyncMock) as m:
        m.return_value = _mock_response(200, json_data=MOCK_TM_ASSIGNMENT_EMPTY_RESPONSE)
        await tm_client.search_assignments(
            serial_number="78787878",
            assignee_name="New Owner LLC",
        )

    body = m.call_args[0][1]
    search_bys = {c["searchBy"] for c in body["searchCriteria"]}
    assert "serialNumber" in search_bys
    assert "assigneeName" in search_bys


@pytest.mark.unit
async def test_search_assignments_http_error(tm_client):
    """HTTP errors surface as error dicts."""
    with patch.object(tm_client, "_post", new_callable=AsyncMock) as m:
        m.return_value = _mock_response(500, text="Server error")
        result = await tm_client.search_assignments(assignee_name="X")

    assert result["error"] is True
    assert result["status_code"] == 500


@pytest.mark.unit
async def test_search_assignments_non_json(tm_client):
    """A non-JSON 200 response surfaces as an error dict."""
    with patch.object(tm_client, "_post", new_callable=AsyncMock) as m:
        m.return_value = _mock_response(200, json_data=None, text="<html>")
        result = await tm_client.search_assignments(assignee_name="X")

    assert result["error"] is True


@pytest.mark.unit
async def test_search_assignments_reel_frame(tm_client):
    """reel_frame is a supported search axis."""
    with patch.object(tm_client, "_post", new_callable=AsyncMock) as m:
        m.return_value = _mock_response(200, json_data=MOCK_TM_ASSIGNMENT_RESPONSE)
        result = await tm_client.search_assignments(reel_frame="1234/0567")

    assert result["total"] == 2
    body = m.call_args[0][1]
    assert {"property": "1234/0567", "searchBy": "reelFrame"} in body["searchCriteria"]
