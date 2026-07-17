"""Unit tests for CourtListenerClient (CourtListener / RECAP v4 contract).

These assert the request shaping (paths, `type` codes, `q` building, dropped
None params), the PACER-fallback credential guard, and the friendly 401/403
auth message shown when no API token is configured. No network access.
"""
import pytest
from unittest.mock import AsyncMock, patch
import httpx

from patent_mcp_server.uspto.courtlistener_client import CourtListenerClient
from patent_mcp_server.constants import LitigationDefaults


@pytest.fixture
async def cl_client():
    client = CourtListenerClient()
    yield client
    await client.close()


@pytest.mark.unit
async def test_client_initialization():
    client = CourtListenerClient()
    assert "User-Agent" in client.headers
    assert client.base_url.endswith("/api/rest/v4")
    await client.close()


@pytest.mark.unit
def test_build_q_quotes_phrases_and_drops_empties():
    assert CourtListenerClient._build_q(None, "", "  ") is None
    assert CourtListenerClient._build_q("estoppel") == "estoppel"
    q = CourtListenerClient._build_q("claim construction", "8123456")
    assert '"claim construction"' in q
    assert "8123456" in q


@pytest.mark.unit
async def test_search_dockets_shapes_params(cl_client):
    with patch.object(cl_client, "_request", new_callable=AsyncMock) as m:
        m.return_value = {"count": 0, "results": []}
        await cl_client.search_dockets(
            patent_number="8123456", court="cafc", filed_after="2020-01-01")
    endpoint, kwargs = m.call_args.args[0], m.call_args.kwargs
    assert endpoint == "/search/"
    params = kwargs["params"]
    assert params["type"] == LitigationDefaults.SEARCH_TYPE_DOCKETS
    assert params["court"] == "cafc"
    assert params["q"] == "8123456"
    assert params["filed_after"] == "2020-01-01"


@pytest.mark.unit
async def test_search_recap_documents_uses_rd_type_and_docket(cl_client):
    with patch.object(cl_client, "_request", new_callable=AsyncMock) as m:
        m.return_value = {"count": 0, "results": []}
        await cl_client.search_recap_documents(docket_id="42", query="brief")
    params = m.call_args.kwargs["params"]
    assert params["type"] == LitigationDefaults.SEARCH_TYPE_RECAP_DOCS
    assert params["docket_id"] == "42"
    assert params["q"] == "brief"


@pytest.mark.unit
async def test_get_endpoints_paths(cl_client):
    with patch.object(cl_client, "_request", new_callable=AsyncMock) as m:
        m.return_value = {"id": 1}
        await cl_client.get_docket("42")
        await cl_client.get_recap_document("7")
        await cl_client.get_opinion("99")
    paths = [c.args[0] for c in m.call_args_list]
    assert paths == ["/dockets/42/", "/recap-documents/7/", "/opinions/99/"]


@pytest.mark.unit
async def test_fetch_from_pacer_guard_without_credentials(cl_client):
    with patch("patent_mcp_server.uspto.courtlistener_client.config") as cfg:
        cfg.PACER_USERNAME = None
        cfg.PACER_PASSWORD = None
        result = await cl_client.fetch_from_pacer(recap_document_id="7")
    assert result["error"] is True
    assert result["error_code"] == "PACER_NOT_CONFIGURED"


@pytest.mark.unit
async def test_request_drops_none_params(cl_client):
    """None-valued query params are stripped before the GET."""
    mock_resp = AsyncMock()
    captured = {}

    async def fake_get(url, params=None):
        captured["params"] = params
        resp = httpx.Response(200, json={"count": 0, "results": []},
                              request=httpx.Request("GET", url))
        return resp

    with patch.object(cl_client.client, "get", side_effect=fake_get):
        await cl_client._request("/search/", params={"q": "x", "court": None})
    assert captured["params"] == {"q": "x"}


@pytest.mark.unit
async def test_401_without_token_returns_friendly_auth_error(cl_client):
    """A 401 with no token configured maps to COURTLISTENER_AUTH_REQUIRED."""
    request = httpx.Request("GET", "https://www.courtlistener.com/api/rest/v4/opinions/1/")
    response = httpx.Response(401, json={"detail": "Authentication credentials were not provided."},
                             request=request)

    async def fake_get(url, params=None):
        return response

    with patch("patent_mcp_server.uspto.courtlistener_client.config") as cfg:
        cfg.COURTLISTENER_API_KEY = None
        with patch.object(cl_client.client, "get", side_effect=fake_get):
            result = await cl_client._request("/opinions/1/")
    assert result["error"] is True
    assert result["error_code"] == "COURTLISTENER_AUTH_REQUIRED"
    assert "COURTLISTENER_API_KEY" in result["message"]
