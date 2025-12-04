"""Unit tests for OfficeActionClient."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from patent_mcp_server.uspto.office_action_client import OfficeActionClient


@pytest.fixture
async def oa_client():
    """Create an OfficeActionClient instance for testing."""
    client = OfficeActionClient()
    yield client
    await client.close()


# ============================================================================
# Initialization Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_client_initialization():
    """Test client initialization."""
    client = OfficeActionClient()

    assert "User-Agent" in client.headers
    assert "X-API-KEY" in client.headers
    assert client.client is not None

    await client.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_client_context_manager():
    """Test client context manager protocol."""
    async with OfficeActionClient() as client:
        assert client is not None
        assert client.client is not None


# ============================================================================
# Office Action Text Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_office_action_text(oa_client):
    """Test getting office action text."""
    with patch.object(oa_client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"officeActions": [], "total": 0}

        result = await oa_client.get_office_action_text("12345678")

        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert "/ds-api/oa-text/v1/search" in call_args[0][0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_office_action_text_with_date(oa_client):
    """Test getting office action text with mail date filter."""
    with patch.object(oa_client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"officeActions": [], "total": 0}

        result = await oa_client.get_office_action_text("12345678", mail_date="2023-06-15")

        mock_request.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_office_actions(oa_client):
    """Test searching office actions."""
    with patch.object(oa_client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"results": [], "total": 0}

        result = await oa_client.search_office_actions(
            query="obviousness",
            examiner_name="Smith",
            art_unit="3600"
        )

        mock_request.assert_called_once()


# ============================================================================
# Office Action Citations Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_office_action_citations(oa_client):
    """Test getting office action citations."""
    with patch.object(oa_client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"citations": [], "total": 0}

        result = await oa_client.get_office_action_citations("12345678")

        mock_request.assert_called_once()
        assert "/ds-api/oa-citations/v2/search" in mock_request.call_args[0][0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_citations(oa_client):
    """Test searching office action citations."""
    with patch.object(oa_client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"results": [], "total": 0}

        result = await oa_client.search_citations(
            cited_patent_number="7654321",
            citation_type="US Patent"
        )

        mock_request.assert_called_once()


# ============================================================================
# Office Action Rejections Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_office_action_rejections(oa_client):
    """Test getting office action rejections."""
    with patch.object(oa_client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"rejections": [], "total": 0}

        result = await oa_client.get_office_action_rejections("12345678")

        mock_request.assert_called_once()
        assert "/ds-api/oa-rejections/v2/search" in mock_request.call_args[0][0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_rejections(oa_client):
    """Test searching office action rejections."""
    with patch.object(oa_client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"results": [], "total": 0}

        result = await oa_client.search_rejections(
            rejection_type="103",
            rejection_basis="obviousness",
            claim_number=1
        )

        mock_request.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_rejections_with_date_range(oa_client):
    """Test searching rejections with date range."""
    with patch.object(oa_client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"results": [], "total": 0}

        result = await oa_client.search_rejections(
            mail_date_from="2023-01-01",
            mail_date_to="2023-12-31"
        )

        mock_request.assert_called_once()


# ============================================================================
# Bulk Download Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_weekly_zip_url(oa_client):
    """Test getting weekly zip URL."""
    result = await oa_client.get_weekly_zip_url("2023-11-19")

    assert "download_url" in result
    assert "2023-11-19" in result["download_url"]
    assert "developer-hub.s3.amazonaws.com" in result["download_url"]


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_http_error_handling(oa_client):
    """Test handling of HTTP errors."""
    with patch.object(oa_client.client, 'get', new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_response.json.return_value = {"error": "Not found"}

        error = httpx.HTTPStatusError("Not Found", request=MagicMock(), response=mock_response)
        mock_get.side_effect = error

        result = await oa_client._make_request("/test")

        assert result.get("error") is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_network_error_retry(oa_client):
    """Test network error retry logic."""
    with patch.object(oa_client.client, 'get', new_callable=AsyncMock) as mock_get:
        mock_success = MagicMock()
        mock_success.status_code = 200
        mock_success.json.return_value = {"result": "success"}
        mock_success.raise_for_status = MagicMock()

        mock_get.side_effect = [
            httpx.NetworkError("Connection failed"),
            mock_success
        ]

        result = await oa_client._make_request("/test")

        assert result == {"result": "success"}
        assert mock_get.call_count == 2


# ============================================================================
# Cleanup Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_close():
    """Test client cleanup."""
    client = OfficeActionClient()

    with patch.object(client.client, 'aclose', new_callable=AsyncMock) as mock_close:
        await client.close()
        mock_close.assert_called_once()
