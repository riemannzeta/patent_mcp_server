"""Unit tests for OfficeActionClient (ODP rejection and citation datasets)."""
import copy
from unittest.mock import AsyncMock, MagicMock, patch

import httpx2
import pytest

from patent_mcp_server.config import config
from patent_mcp_server.uspto.office_action_client import (
    CITATIONS, REJECTIONS, OfficeActionClient,
)
from test.fixtures.odp_oa_dataset_responses import REJECTION_RECORDS_RESPONSE

SLEEP = "patent_mcp_server.uspto.office_action_client.asyncio.sleep"


@pytest.fixture
async def oa_client():
    client = OfficeActionClient()
    yield client
    await client.close()


def _ok(payload):
    response = MagicMock(status_code=200, headers={})
    response.json.return_value = copy.deepcopy(payload)
    return response


def _status(code, text="error"):
    response = MagicMock(status_code=code, headers={}, text=text)
    response.json.side_effect = ValueError("not json")
    response.raise_for_status.side_effect = httpx2.HTTPStatusError(
        str(code), request=MagicMock(), response=response
    )
    return response


@pytest.mark.unit
@pytest.mark.asyncio
async def test_client_targets_odp():
    async with OfficeActionClient() as client:
        assert client.base_url == config.API_BASE_URL
        assert client.records_url(REJECTIONS).endswith("/api/v1/patent/oa/oa_rejections/v2/records")
        assert client.records_url(CITATIONS).endswith("/api/v1/patent/oa/oa_citations/v2/records")
        assert "developer.uspto.gov" not in client.records_url(REJECTIONS)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_records_posts_form(oa_client, monkeypatch):
    """criteria, start and rows go form-encoded, with the key per request."""
    monkeypatch.setattr(config, "USPTO_API_KEY", "test-key")
    with patch.object(oa_client.client, "post", new_callable=AsyncMock,
                      return_value=_ok(REJECTION_RECORDS_RESPONSE)) as post:
        result = await oa_client.search_records(
            REJECTIONS, 'patentApplicationNumber:"18402543"', start=10, rows=5,
        )

    url = post.call_args.args[0]
    assert url == oa_client.records_url(REJECTIONS)
    assert post.call_args.kwargs["data"] == {
        "criteria": 'patentApplicationNumber:"18402543"', "start": "10", "rows": "5",
    }
    assert "json" not in post.call_args.kwargs
    assert post.call_args.kwargs["headers"]["X-API-KEY"] == "test-key"
    assert result["total"] == 11
    assert len(result["docs"]) == len(REJECTION_RECORDS_RESPONSE["response"]["docs"])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_no_match_is_an_empty_page(oa_client):
    empty = {"response": {"start": 0, "numFound": 0, "docs": []}}
    with patch.object(oa_client.client, "post", new_callable=AsyncMock, return_value=_ok(empty)):
        result = await oa_client.search_records(CITATIONS, "nosuchfield:1")
    assert result == {"total": 0, "docs": []}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_unparseable_query_is_an_error(oa_client):
    """Solr answers a query it cannot parse with 200 and {}."""
    with patch.object(oa_client.client, "post", new_callable=AsyncMock, return_value=_ok({})):
        result = await oa_client.search_records(REJECTIONS, "foo:(")
    assert result["error"] is True
    assert result["error_code"] == "QUERY_ERROR"
    assert "foo:(" in result["message"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_http_error_is_returned(oa_client):
    with patch.object(oa_client.client, "post", new_callable=AsyncMock,
                      return_value=_status(403, "Forbidden")):
        result = await oa_client.search_records(REJECTIONS, "x:1")
    assert result["error"] is True
    assert result["status_code"] == 403


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retries_after_429(oa_client):
    limited = _status(429, "Too Many Requests")
    limited.headers = {"retry-after": "2"}
    with patch.object(oa_client.client, "post", new_callable=AsyncMock,
                      side_effect=[limited, _ok(REJECTION_RECORDS_RESPONSE)]) as post, \
         patch(SLEEP, new_callable=AsyncMock) as sleep:
        result = await oa_client.search_records(REJECTIONS, "x:1")

    assert result["total"] == 11
    assert post.await_count == 2
    sleep.assert_awaited_once_with(2.0)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_close(oa_client):
    with patch.object(oa_client.client, "aclose", new_callable=AsyncMock) as aclose:
        await oa_client.close()
        aclose.assert_called_once()
