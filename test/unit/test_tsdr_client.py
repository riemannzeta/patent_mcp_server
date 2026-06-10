"""Unit tests for TSDRClient (tsdrapi.uspto.gov)."""
import base64
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from patent_mcp_server.uspto.tsdr_client import TSDRClient
from patent_mcp_server.config import config

from test.fixtures.tsdr_responses import (
    MOCK_TSDR_STATUS_RESPONSE,
    MOCK_TSDR_PDF_BYTES,
    MOCK_TSDR_IMAGE_BYTES,
)


@pytest.fixture
async def tsdr_client():
    """Create a TSDRClient instance for testing."""
    client = TSDRClient()
    yield client
    await client.close()


def _mock_response(status_code=200, json_data=None, content=b"", headers=None):
    """Build a MagicMock httpx.Response."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.headers = headers or {}
    response.content = content
    response.text = content.decode("utf-8", errors="replace") if content else ""
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
    """Client sends the USPTO-API-KEY header (not X-API-KEY)."""
    client = TSDRClient()

    assert "User-Agent" in client.headers
    assert "USPTO-API-KEY" in client.headers
    assert "X-API-KEY" not in client.headers
    assert client.client is not None

    await client.close()


@pytest.mark.unit
async def test_client_context_manager():
    """Test client context manager protocol."""
    async with TSDRClient() as client:
        assert client is not None
        assert client.client is not None


# ============================================================================
# URL Building Tests
# ============================================================================

@pytest.mark.unit
async def test_status_url_serial_number(tsdr_client):
    """Serial number builds the sn{N}/info.json URL."""
    url = tsdr_client._status_url("78787878", None)
    assert url == f"{config.TSDR_BASE_URL}/casestatus/sn78787878/info.json"


@pytest.mark.unit
async def test_status_url_registration_number(tsdr_client):
    """Registration number builds the rn{N}/info.json URL."""
    url = tsdr_client._status_url(None, "3500027")
    assert url == f"{config.TSDR_BASE_URL}/casestatus/rn3500027/info.json"


@pytest.mark.unit
async def test_status_url_requires_exactly_one_identifier(tsdr_client):
    """Both or neither identifier returns a validation error."""
    neither = tsdr_client._status_url(None, None)
    both = tsdr_client._status_url("78787878", "3500027")

    for result in (neither, both):
        assert isinstance(result, dict)
        assert result["error"] is True
        assert result["error_code"] == "VALIDATION_ERROR"


# ============================================================================
# JSON Request Tests
# ============================================================================

@pytest.mark.unit
async def test_get_case_status_returns_json(tsdr_client):
    """Successful status request returns parsed JSON."""
    with patch.object(tsdr_client, "_get", new_callable=AsyncMock) as m:
        m.return_value = _mock_response(200, json_data=MOCK_TSDR_STATUS_RESPONSE)
        result = await tsdr_client.get_case_status(serial_number="78787878")

    assert result == MOCK_TSDR_STATUS_RESPONSE
    called_url = m.call_args[0][0]
    assert called_url.endswith("/casestatus/sn78787878/info.json")


@pytest.mark.unit
async def test_get_case_status_http_error(tsdr_client):
    """Non-200 returns an ApiError dict with status code."""
    with patch.object(tsdr_client, "_get", new_callable=AsyncMock) as m:
        m.return_value = _mock_response(401, content=b"Unauthorized")
        result = await tsdr_client.get_case_status(serial_number="78787878")

    assert result["error"] is True
    assert result["status_code"] == 401


@pytest.mark.unit
async def test_get_case_status_non_json_response(tsdr_client):
    """200 with non-JSON body returns an error dict, not an exception."""
    with patch.object(tsdr_client, "_get", new_callable=AsyncMock) as m:
        m.return_value = _mock_response(200, content=b"<html>not json</html>")
        result = await tsdr_client.get_case_status(serial_number="78787878")

    assert result["error"] is True


# ============================================================================
# Binary Request Tests
# ============================================================================

@pytest.mark.unit
async def test_download_case_documents_returns_base64(tsdr_client):
    """PDF bundle is returned base64-encoded with the PPUBS envelope shape."""
    with patch.object(tsdr_client, "_get", new_callable=AsyncMock) as m:
        m.return_value = _mock_response(
            200, content=MOCK_TSDR_PDF_BYTES,
            headers={"content-type": "application/pdf"}
        )
        result = await tsdr_client.download_case_documents("78787878")

    assert result["success"] is True
    assert result["filename"] == "tm-78787878-documents.pdf"
    assert result["content_type"] == "application/pdf"
    assert result["size_bytes"] == len(MOCK_TSDR_PDF_BYTES)
    assert base64.b64decode(result["content"]) == MOCK_TSDR_PDF_BYTES

    called_url = m.call_args[0][0]
    assert "/casedocs/bundle.pdf?sn=78787878" in called_url


@pytest.mark.unit
async def test_download_case_documents_with_filters(tsdr_client):
    """Document type and date filters appear in the query string."""
    with patch.object(tsdr_client, "_get", new_callable=AsyncMock) as m:
        m.return_value = _mock_response(
            200, content=MOCK_TSDR_PDF_BYTES,
            headers={"content-type": "application/pdf"}
        )
        await tsdr_client.download_case_documents(
            "78787878", document_type="OOA",
            date_from="2020-01-01", date_to="2020-12-31"
        )

    called_url = m.call_args[0][0]
    assert "type=OOA" in called_url
    assert "fromDate=2020-01-01" in called_url
    assert "toDate=2020-12-31" in called_url


@pytest.mark.unit
async def test_get_mark_image_returns_base64(tsdr_client):
    """Mark image is returned base64-encoded with content type passthrough."""
    with patch.object(tsdr_client, "_get", new_callable=AsyncMock) as m:
        m.return_value = _mock_response(
            200, content=MOCK_TSDR_IMAGE_BYTES,
            headers={"content-type": "image/png"}
        )
        result = await tsdr_client.get_mark_image("78787878")

    assert result["success"] is True
    assert result["content_type"] == "image/png"
    assert base64.b64decode(result["content"]) == MOCK_TSDR_IMAGE_BYTES

    called_url = m.call_args[0][0]
    assert called_url.endswith("/rawImage/78787878")


@pytest.mark.unit
async def test_binary_request_http_error(tsdr_client):
    """Binary request error returns an ApiError dict."""
    with patch.object(tsdr_client, "_get", new_callable=AsyncMock) as m:
        m.return_value = _mock_response(404, content=b"Not found")
        result = await tsdr_client.get_mark_image("00000000")

    assert result["error"] is True
    assert result["status_code"] == 404


# ============================================================================
# Rate Limit (429) Handling Tests
# ============================================================================

@pytest.mark.unit
async def test_429_retries_after_wait(tsdr_client):
    """A 429 response sleeps per Retry-After and retries once."""
    rate_limited = _mock_response(429, content=b"Too many requests",
                                  headers={"Retry-After": "0"})
    ok = _mock_response(200, json_data=MOCK_TSDR_STATUS_RESPONSE)

    with patch.object(tsdr_client.client, "get", new_callable=AsyncMock) as m, \
         patch("patent_mcp_server.uspto.tsdr_client.asyncio.sleep",
               new_callable=AsyncMock) as sleep_mock:
        m.side_effect = [rate_limited, ok]
        result = await tsdr_client.get_case_status(serial_number="78787878")

    assert result == MOCK_TSDR_STATUS_RESPONSE
    assert m.call_count == 2
    sleep_mock.assert_awaited_once()


@pytest.mark.unit
async def test_unexpected_exception_returns_error_dict(tsdr_client):
    """Unexpected exceptions are wrapped into ApiError dicts."""
    with patch.object(tsdr_client.client, "get", new_callable=AsyncMock) as m:
        m.side_effect = RuntimeError("boom")
        result = await tsdr_client.get_case_status(serial_number="78787878")

    assert result["error"] is True
