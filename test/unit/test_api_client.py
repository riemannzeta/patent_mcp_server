"""Unit tests for ApiUsptoClient."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from patent_mcp_server.uspto.api_uspto_gov import ApiUsptoClient
from patent_mcp_server.constants import HTTPMethods
from test.fixtures.api_responses import (
    MOCK_APP_RESPONSE,
    MOCK_SEARCH_APPS_RESPONSE,
    MOCK_ERROR_NOT_FOUND,
    MOCK_ERROR_UNAUTHORIZED,
    MOCK_ERROR_RATE_LIMITED
)


@pytest.fixture
async def api_client():
    """Create an ApiUsptoClient instance for testing."""
    client = ApiUsptoClient()
    yield client
    await client.close()


# ============================================================================
# Initialization Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_client_initialization():
    """Test client initialization."""
    client = ApiUsptoClient()

    # Check headers are set
    assert "User-Agent" in client.headers
    assert "X-API-KEY" in client.headers
    assert client.client is not None

    await client.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_client_context_manager():
    """Test client context manager protocol."""
    async with ApiUsptoClient() as client:
        assert client is not None
        assert client.client is not None

    # Client should be closed after context


# ============================================================================
# Query String Building Tests
# ============================================================================

@pytest.mark.unit
def test_build_query_string_simple():
    """Test building simple query string."""
    client = ApiUsptoClient()

    params = {"q": "test", "limit": 10}
    query_string = client.build_query_string(params)

    assert "q=test" in query_string
    assert "limit=10" in query_string


@pytest.mark.unit
def test_build_query_string_with_none_values():
    """Test that None values are excluded."""
    client = ApiUsptoClient()

    params = {"q": "test", "limit": None, "offset": 0}
    query_string = client.build_query_string(params)

    assert "q=test" in query_string
    assert "offset=0" in query_string
    assert "limit" not in query_string


@pytest.mark.unit
def test_build_query_string_with_boolean():
    """Test boolean values are converted to lowercase strings."""
    client = ApiUsptoClient()

    params = {"includeFiles": True, "latest": False}
    query_string = client.build_query_string(params)

    assert "includeFiles=true" in query_string
    assert "latest=false" in query_string


@pytest.mark.unit
def test_build_query_string_with_list():
    """Test list values are comma-separated."""
    client = ApiUsptoClient()

    params = {"fields": ["field1", "field2", "field3"]}
    query_string = client.build_query_string(params)

    assert "fields=field1" in query_string
    assert "field2" in query_string
    assert "field3" in query_string


@pytest.mark.unit
def test_build_query_string_url_encoding():
    """Test URL encoding of special characters."""
    client = ApiUsptoClient()

    params = {"q": "test query with spaces"}
    query_string = client.build_query_string(params)

    # Should be URL encoded
    assert "test%20query%20with%20spaces" in query_string


@pytest.mark.unit
def test_build_query_string_empty():
    """Test building query string with empty params."""
    client = ApiUsptoClient()

    params = {}
    query_string = client.build_query_string(params)

    assert query_string == ""


# ============================================================================
# HTTP Request Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_make_request_get_success(api_client):
    """Test successful GET request."""
    with patch.object(api_client.client, 'get', new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = MOCK_APP_RESPONSE
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = await api_client.make_request("http://test.com", method=HTTPMethods.GET)

        assert result == MOCK_APP_RESPONSE
        mock_get.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_make_request_post_success(api_client):
    """Test successful POST request."""
    with patch.object(api_client.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = MOCK_SEARCH_APPS_RESPONSE
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = await api_client.make_request(
            "http://test.com",
            method=HTTPMethods.POST,
            data={"q": "test"}
        )

        assert result == MOCK_SEARCH_APPS_RESPONSE
        mock_post.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_make_request_http_error_404(api_client):
    """Test handling of 404 HTTP error."""
    with patch.object(api_client.client, 'get', new_callable=AsyncMock) as mock_get:
        # Create HTTPStatusError
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_response.json.return_value = MOCK_ERROR_NOT_FOUND

        error = httpx.HTTPStatusError("Not Found", request=MagicMock(), response=mock_response)
        mock_get.side_effect = error

        result = await api_client.make_request("http://test.com")

        # Should return error dictionary
        assert result.get("error") is True
        assert "message" in result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_make_request_http_error_401(api_client):
    """Test handling of 401 Unauthorized error."""
    with patch.object(api_client.client, 'get', new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.json.return_value = MOCK_ERROR_UNAUTHORIZED

        error = httpx.HTTPStatusError("Unauthorized", request=MagicMock(), response=mock_response)
        mock_get.side_effect = error

        result = await api_client.make_request("http://test.com")

        assert result.get("error") is True
        assert "message" in result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_make_request_network_error_retry(api_client):
    """Test network error retry logic."""
    with patch.object(api_client.client, 'get', new_callable=AsyncMock) as mock_get:
        # First attempt: network error
        # Second attempt: success
        mock_success = MagicMock()
        mock_success.status_code = 200
        mock_success.json.return_value = {"result": "success"}
        mock_success.raise_for_status = MagicMock()

        mock_get.side_effect = [
            httpx.NetworkError("Connection failed"),
            mock_success
        ]

        result = await api_client.make_request("http://test.com")

        # Should have retried
        assert result == {"result": "success"}
        assert mock_get.call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_make_request_timeout_error_retry(api_client):
    """Test timeout error retry logic."""
    with patch.object(api_client.client, 'get', new_callable=AsyncMock) as mock_get:
        # First attempt: timeout
        # Second attempt: success
        mock_success = MagicMock()
        mock_success.status_code = 200
        mock_success.json.return_value = {"result": "success"}
        mock_success.raise_for_status = MagicMock()

        mock_get.side_effect = [
            httpx.TimeoutException("Request timeout"),
            mock_success
        ]

        result = await api_client.make_request("http://test.com")

        assert result == {"result": "success"}
        assert mock_get.call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_make_request_unsupported_method(api_client):
    """Test handling of unsupported HTTP method."""
    result = await api_client.make_request("http://test.com", method="DELETE")

    # Should return error
    assert result.get("error") is True
    assert "Unsupported HTTP method" in result.get("message", "")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_make_request_with_headers(api_client):
    """Test that API key header is included."""
    with patch.object(api_client.client, 'get', new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        await api_client.make_request("http://test.com")

        # Check that headers were passed
        call_args = mock_get.call_args
        headers = call_args.kwargs.get("headers", {})
        assert "X-API-KEY" in headers


@pytest.mark.unit
@pytest.mark.asyncio
async def test_make_request_exception_handling(api_client):
    """Test handling of unexpected exceptions."""
    with patch.object(api_client.client, 'get', new_callable=AsyncMock) as mock_get:
        # Simulate unexpected exception
        mock_get.side_effect = Exception("Unexpected error")

        result = await api_client.make_request("http://test.com")

        # Should return error dictionary
        assert result.get("error") is True
        assert "message" in result


# ============================================================================
# Resource Cleanup Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_close():
    """Test client cleanup."""
    client = ApiUsptoClient()

    with patch.object(client.client, 'aclose', new_callable=AsyncMock) as mock_close:
        await client.close()
        mock_close.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_context_manager_cleanup():
    """Test context manager cleanup."""
    async with ApiUsptoClient() as client:
        # Use patch to verify cleanup
        with patch.object(client.client, 'aclose', new_callable=AsyncMock) as mock_close:
            pass

    # Context manager should trigger cleanup
