"""Unit tests for PatentsViewClient."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from patent_mcp_server.patentsview.patentsview_client import PatentsViewClient
from patent_mcp_server.constants import PatentsViewEndpoints


@pytest.fixture
async def patentsview_client():
    """Create a PatentsViewClient instance for testing."""
    client = PatentsViewClient()
    yield client
    await client.close()


# ============================================================================
# Initialization Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_client_initialization():
    """Test client initialization."""
    client = PatentsViewClient()

    assert "User-Agent" in client.headers
    assert "Accept" in client.headers
    assert client.client is not None
    assert client.rate_limit == 45  # Default rate limit

    await client.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_client_context_manager():
    """Test client context manager protocol."""
    async with PatentsViewClient() as client:
        assert client is not None
        assert client.client is not None


# ============================================================================
# Patent Search Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_by_text(patentsview_client):
    """Test full-text patent search."""
    with patch.object(patentsview_client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"patents": [], "count": 0, "total_hits": 0}

        result = await patentsview_client.search_by_text("neural network", search_type="any")

        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert PatentsViewEndpoints.PATENT in call_args[0][0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_by_text_phrase(patentsview_client):
    """Test exact phrase search."""
    with patch.object(patentsview_client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"patents": [], "count": 0, "total_hits": 0}

        await patentsview_client.search_by_text("machine learning", search_type="phrase")

        mock_request.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_patent(patentsview_client):
    """Test getting a specific patent."""
    with patch.object(patentsview_client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"patent_id": "7861317"}

        result = await patentsview_client.get_patent("7861317")

        mock_request.assert_called_once()
        assert "/7861317/" in mock_request.call_args[0][0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_patents_with_query(patentsview_client):
    """Test search with complex query object."""
    with patch.object(patentsview_client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"patents": [], "count": 0, "total_hits": 0}

        query = {"_and": [
            {"patent_date": {"_gte": "2020-01-01"}},
            {"assignee_organization": "IBM"}
        ]}

        result = await patentsview_client.search_patents(query, size=50)

        mock_request.assert_called_once()


# ============================================================================
# Assignee Search Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_assignees(patentsview_client):
    """Test assignee search."""
    with patch.object(patentsview_client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"assignees": [], "count": 0}

        query = {"assignee_organization": {"_contains": "Apple"}}
        result = await patentsview_client.search_assignees(query)

        mock_request.assert_called_once()
        assert PatentsViewEndpoints.ASSIGNEE in mock_request.call_args[0][0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_assignee(patentsview_client):
    """Test getting a specific assignee."""
    with patch.object(patentsview_client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"assignee_id": "abc123"}

        result = await patentsview_client.get_assignee("abc123")

        mock_request.assert_called_once()


# ============================================================================
# Inventor Search Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_inventors(patentsview_client):
    """Test inventor search."""
    with patch.object(patentsview_client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"inventors": [], "count": 0}

        query = {"inventor_name_last": "Smith"}
        result = await patentsview_client.search_inventors(query)

        mock_request.assert_called_once()
        assert PatentsViewEndpoints.INVENTOR in mock_request.call_args[0][0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_inventor(patentsview_client):
    """Test getting a specific inventor."""
    with patch.object(patentsview_client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"inventor_id": "xyz789"}

        result = await patentsview_client.get_inventor("xyz789")

        mock_request.assert_called_once()


# ============================================================================
# Claims and Description Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_patent_claims(patentsview_client):
    """Test getting patent claims."""
    with patch.object(patentsview_client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"claims": [], "count": 0}

        result = await patentsview_client.get_patent_claims("7861317")

        mock_request.assert_called_once()
        assert PatentsViewEndpoints.CLAIMS in mock_request.call_args[0][0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_patent_description(patentsview_client):
    """Test getting patent description."""
    with patch.object(patentsview_client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"descriptions": [], "count": 0}

        result = await patentsview_client.get_patent_description("7861317")

        mock_request.assert_called_once()
        assert PatentsViewEndpoints.DESCRIPTION in mock_request.call_args[0][0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_patent_summary(patentsview_client):
    """Test getting patent brief summary."""
    with patch.object(patentsview_client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"summaries": [], "count": 0}

        result = await patentsview_client.get_patent_summary("7861317")

        mock_request.assert_called_once()
        assert PatentsViewEndpoints.BRIEF_SUMMARY in mock_request.call_args[0][0]


# ============================================================================
# CPC Classification Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_by_cpc(patentsview_client):
    """Test CPC classification search."""
    with patch.object(patentsview_client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"patents": [], "count": 0}

        result = await patentsview_client.search_by_cpc("G06N3/08")

        mock_request.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_lookup_cpc_class(patentsview_client):
    """Test CPC class lookup."""
    with patch.object(patentsview_client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"cpc_class": "G06"}

        result = await patentsview_client.lookup_cpc_class("G06")

        mock_request.assert_called_once()
        assert "G06" in mock_request.call_args[0][0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_lookup_cpc_group(patentsview_client):
    """Test CPC group lookup."""
    with patch.object(patentsview_client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"cpc_group": "G06N3/08"}

        result = await patentsview_client.lookup_cpc_group("G06N3/08")

        mock_request.assert_called_once()


# ============================================================================
# Rate Limiting Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limit_check(patentsview_client):
    """Test rate limit checking doesn't block within limit."""
    # Should not block when under the limit
    await patentsview_client._check_rate_limit()

    # Request times list should have one entry
    assert len(patentsview_client._request_times) == 1


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_http_error_handling(patentsview_client):
    """Test handling of HTTP errors."""
    with patch.object(patentsview_client.client, 'get', new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_response.headers = {"X-Status-Reason": "Invalid API Key"}
        mock_response.json.return_value = {"error": True}

        error = httpx.HTTPStatusError("Forbidden", request=MagicMock(), response=mock_response)
        mock_get.side_effect = error

        # Clear rate limit state first
        patentsview_client._request_times = []

        result = await patentsview_client._make_request("/test")

        assert result.get("error") is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limit_429_handling(patentsview_client):
    """Test handling of 429 rate limit response."""
    with patch.object(patentsview_client.client, 'get', new_callable=AsyncMock) as mock_get:
        # First call returns 429, second returns success
        mock_429_response = MagicMock()
        mock_429_response.status_code = 429
        mock_429_response.headers = {"Retry-After": "1"}
        mock_429_response.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError(
            "Rate Limited", request=MagicMock(), response=mock_429_response
        ))

        mock_success = MagicMock()
        mock_success.status_code = 200
        mock_success.json.return_value = {"result": "success"}
        mock_success.raise_for_status = MagicMock()

        mock_get.side_effect = [mock_429_response, mock_success]

        # Clear rate limit state
        patentsview_client._request_times = []

        # This test may take ~1 second due to Retry-After
        result = await patentsview_client._make_request("/test")

        # Should have retried after rate limit
        assert mock_get.call_count == 2


# ============================================================================
# Query Building Tests
# ============================================================================

@pytest.mark.unit
def test_build_query():
    """Test query building."""
    client = PatentsViewClient()

    query = {"patent_title": "test"}
    params = client._build_query(query, f=["patent_id"], s=[{"patent_date": "desc"}])

    assert "q" in params
    assert "f" in params
    assert "s" in params


@pytest.mark.unit
def test_build_query_minimal():
    """Test minimal query building."""
    client = PatentsViewClient()

    query = {"patent_id": "7861317"}
    params = client._build_query(query)

    assert "q" in params
    assert "f" not in params
    assert "s" not in params


# ============================================================================
# Cleanup Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_close():
    """Test client cleanup."""
    client = PatentsViewClient()

    with patch.object(client.client, 'aclose', new_callable=AsyncMock) as mock_close:
        await client.close()
        mock_close.assert_called_once()
