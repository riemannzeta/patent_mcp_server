"""Unit tests for TmSearchClient (tmsearch.uspto.gov internal API)."""
import pytest
from unittest.mock import AsyncMock, patch

from patent_mcp_server.uspto.tmsearch_client import TmSearchClient, SEARCH_PATH
from patent_mcp_server.constants import TmSearchFields, TrademarkDefaults
from patent_mcp_server.config import config

from test.fixtures.tmsearch_responses import (
    MOCK_TMSEARCH_RESPONSE,
    MOCK_TMSEARCH_ES7_RESPONSE,
    MOCK_TMSEARCH_RESPONSE_INT_TOTAL,
    MOCK_TMSEARCH_EMPTY_RESPONSE,
)


@pytest.fixture
async def tmsearch_client():
    """Create a TmSearchClient instance for testing."""
    client = TmSearchClient()
    yield client
    await client.close()


# ============================================================================
# Initialization Tests
# ============================================================================

@pytest.mark.unit
async def test_client_initialization():
    """Client sends browser-like headers and no API key."""
    client = TmSearchClient()

    assert client.headers["Accept"] == "application/json, text/plain, */*"
    assert client.headers["Origin"] == config.TMSEARCH_BASE_URL
    assert "X-API-KEY" not in client.headers
    assert "USPTO-API-KEY" not in client.headers

    await client.close()


@pytest.mark.unit
async def test_client_context_manager():
    """Test client context manager protocol."""
    async with TmSearchClient() as client:
        assert client is not None


# ============================================================================
# build_search_body Tests (pure function, offline)
# ============================================================================

@pytest.mark.unit
def test_build_body_mark_text():
    body = TmSearchClient.build_search_body(mark_text="ACME")
    must = body["query"]["bool"]["must"]
    assert {"match": {TmSearchFields.WORDMARK: "ACME"}} in must


@pytest.mark.unit
def test_build_body_owner_name():
    body = TmSearchClient.build_search_body(owner_name="Acme Corp")
    must = body["query"]["bool"]["must"]
    assert {"match": {TmSearchFields.OWNER: "Acme Corp"}} in must


@pytest.mark.unit
def test_build_body_serial_and_registration():
    body = TmSearchClient.build_search_body(
        serial_number="78787878", registration_number="3500027"
    )
    must = body["query"]["bool"]["must"]
    assert {"term": {TmSearchFields.SERIAL_NUMBER: "78787878"}} in must
    assert {"term": {TmSearchFields.REGISTRATION_NUMBER: "3500027"}} in must


@pytest.mark.unit
def test_build_body_raw_query():
    body = TmSearchClient.build_search_body(query="wordmark:ACME*")
    must = body["query"]["bool"]["must"]
    assert must[0]["query_string"]["query"] == "wordmark:ACME*"


@pytest.mark.unit
def test_build_body_class_and_status_filters():
    body = TmSearchClient.build_search_body(
        mark_text="ACME", international_class="9", status_filter="live"
    )
    filters = body["query"]["bool"]["filter"]
    # Class numbers are zero-padded to 3 digits ("IC 009"-style index tokens)
    assert {"term": {TmSearchFields.INTERNATIONAL_CLASS: "009"}} in filters
    assert {"term": {TmSearchFields.ALIVE: True}} in filters

    body_dead = TmSearchClient.build_search_body(
        mark_text="ACME", status_filter="dead"
    )
    assert {"term": {TmSearchFields.ALIVE: False}} in body_dead["query"]["bool"]["filter"]


@pytest.mark.unit
def test_build_body_goods_services():
    body = TmSearchClient.build_search_body(goods_services="athletic footwear")
    must = body["query"]["bool"]["must"]
    assert {"match": {TmSearchFields.GOODS_AND_SERVICES: "athletic footwear"}} in must


@pytest.mark.unit
def test_build_body_class_not_padded_when_non_numeric():
    """Pre-formatted class terms pass through unchanged."""
    body = TmSearchClient.build_search_body(international_class="IC 009")
    filters = body["query"]["bool"]["filter"]
    assert {"term": {TmSearchFields.INTERNATIONAL_CLASS: "IC 009"}} in filters


@pytest.mark.unit
def test_build_body_pagination():
    body = TmSearchClient.build_search_body(mark_text="ACME", offset=50, limit=10)
    assert body["from"] == 50
    assert body["size"] == 10


@pytest.mark.unit
def test_build_body_limit_capped():
    body = TmSearchClient.build_search_body(mark_text="ACME", limit=9999)
    assert body["size"] == TrademarkDefaults.SEARCH_LIMIT_MAX


@pytest.mark.unit
def test_build_body_no_filters_is_match_all():
    body = TmSearchClient.build_search_body()
    assert body["query"]["bool"]["must"] == [{"match_all": {}}]


# ============================================================================
# parse_search_response Tests
# ============================================================================

@pytest.mark.unit
def test_parse_response_live_shape():
    """The live envelope (totalValue + source) parses correctly."""
    parsed = TmSearchClient.parse_search_response(MOCK_TMSEARCH_RESPONSE)
    assert parsed["total"] == 2
    assert len(parsed["results"]) == 2
    assert parsed["results"][0]["wordmark"] == "TESTMARK"
    assert parsed["results"][0]["id"] == "78787878"


@pytest.mark.unit
def test_parse_response_es7_fallback():
    """A standard ES7 envelope (total object + _source) still parses."""
    parsed = TmSearchClient.parse_search_response(MOCK_TMSEARCH_ES7_RESPONSE)
    assert parsed["total"] == 1
    assert parsed["results"][0]["wordmark"] == "TESTMARK"


@pytest.mark.unit
def test_parse_response_int_total():
    parsed = TmSearchClient.parse_search_response(MOCK_TMSEARCH_RESPONSE_INT_TOTAL)
    assert parsed["total"] == 1
    assert parsed["results"][0]["wordmark"] == "TESTMARK"


@pytest.mark.unit
def test_parse_response_empty():
    parsed = TmSearchClient.parse_search_response(MOCK_TMSEARCH_EMPTY_RESPONSE)
    assert parsed == {"results": [], "total": 0}


@pytest.mark.unit
def test_parse_response_malformed():
    assert TmSearchClient.parse_search_response({}) == {"results": [], "total": 0}
    assert TmSearchClient.parse_search_response({"hits": "garbage"}) == {
        "results": [], "total": 0
    }


# ============================================================================
# Request Wiring Tests
# ============================================================================

@pytest.mark.unit
async def test_search_posts_to_search_path(tmsearch_client):
    """search() POSTs the built body to SEARCH_PATH and parses the result."""
    with patch.object(tmsearch_client, "make_request", new_callable=AsyncMock) as m:
        m.return_value = MOCK_TMSEARCH_RESPONSE
        result = await tmsearch_client.search(mark_text="TESTMARK")

    assert result["total"] == 2
    body = m.call_args[0][0]
    assert body["query"]["bool"]["must"] == [
        {"match": {TmSearchFields.WORDMARK: "TESTMARK"}}
    ]


@pytest.mark.unit
async def test_search_propagates_error(tmsearch_client):
    """Error dicts from make_request pass through unparsed."""
    with patch.object(tmsearch_client, "make_request", new_callable=AsyncMock) as m:
        m.return_value = {"error": True, "message": "nope", "status_code": 500}
        result = await tmsearch_client.search(mark_text="TESTMARK")

    assert result["error"] is True


@pytest.mark.unit
async def test_get_by_serial(tmsearch_client):
    """get_by_serial issues a single-term serial search."""
    with patch.object(tmsearch_client, "make_request", new_callable=AsyncMock) as m:
        m.return_value = MOCK_TMSEARCH_RESPONSE_INT_TOTAL
        result = await tmsearch_client.get_by_serial("78787878")

    body = m.call_args[0][0]
    assert {"term": {TmSearchFields.SERIAL_NUMBER: "78787878"}} in body["query"]["bool"]["must"]
    assert body["size"] == 1
    assert result["total"] == 1


@pytest.mark.unit
@pytest.mark.parametrize("waf_status", [202, 403])
async def test_waf_rejection_returns_actionable_error(tmsearch_client, waf_status):
    """AWS WAF rejections (403 blocked / 202 challenge) get a hint."""
    from unittest.mock import MagicMock
    import httpx

    waf_response = MagicMock(spec=httpx.Response)
    waf_response.status_code = waf_status
    waf_response.text = "<html>challenge</html>"

    with patch.object(
        tmsearch_client.client, "post", new_callable=AsyncMock
    ) as m:
        m.return_value = waf_response
        result = await tmsearch_client.make_request({"query": {}})

    assert result["error"] is True
    assert "TMSEARCH_WAF_TOKEN" in result["hint"]


@pytest.mark.unit
async def test_non_json_200_is_waf_challenge(tmsearch_client):
    """A 200 with non-JSON content is reported as a WAF challenge."""
    from unittest.mock import MagicMock
    import httpx

    challenge = MagicMock(spec=httpx.Response)
    challenge.status_code = 200
    challenge.text = "<html>verify you are human</html>"
    challenge.raise_for_status.return_value = None
    challenge.json.side_effect = ValueError("not json")

    with patch.object(
        tmsearch_client.client, "post", new_callable=AsyncMock
    ) as m:
        m.return_value = challenge
        result = await tmsearch_client.make_request({"query": {}})

    assert result["error"] is True
    assert result["error_code"] == "WAF_CHALLENGE"


@pytest.mark.unit
async def test_make_request_url(tmsearch_client):
    """make_request targets TMSEARCH_BASE_URL + SEARCH_PATH."""
    captured = {}

    async def fake_post(url, json=None, timeout=None):
        captured["url"] = url
        raise RuntimeError("stop here")

    with patch.object(tmsearch_client.client, "post", side_effect=fake_post):
        result = await tmsearch_client.make_request({"query": {}})

    assert captured["url"] == f"{config.TMSEARCH_BASE_URL}{SEARCH_PATH}"
    assert result["error"] is True
