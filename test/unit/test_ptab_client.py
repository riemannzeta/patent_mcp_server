"""Unit tests for PTABClient."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from patent_mcp_server.uspto.ptab_client import PTABClient
from patent_mcp_server.constants import HTTPMethods, PTABTrialTypes


@pytest.fixture
async def ptab_client():
    """Create a PTABClient instance for testing."""
    client = PTABClient()
    yield client
    await client.close()


# ============================================================================
# Initialization Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_client_initialization():
    """Test client initialization."""
    client = PTABClient()

    assert "User-Agent" in client.headers
    assert "X-API-KEY" in client.headers
    assert client.client is not None
    assert "/api/v1/patent/trials" in client.base_url

    await client.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_client_context_manager():
    """Test client context manager protocol."""
    async with PTABClient() as client:
        assert client is not None
        assert client.client is not None


# ============================================================================
# Proceeding Search Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_proceedings(ptab_client):
    """Test searching PTAB proceedings."""
    with patch.object(ptab_client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"results": [], "total": 0}

        result = await ptab_client.search_proceedings(
            query="test",
            trial_type=PTABTrialTypes.IPR,
            patent_number="7654321"
        )

        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert "/proceedings/search" in call_args[0][0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_proceedings_with_date_range(ptab_client):
    """Test searching with date range filters."""
    with patch.object(ptab_client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"results": [], "total": 0}

        await ptab_client.search_proceedings(
            filing_date_from="2023-01-01",
            filing_date_to="2023-12-31",
            status="Instituted"
        )

        mock_request.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_proceeding(ptab_client):
    """Test getting a specific proceeding."""
    with patch.object(ptab_client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"proceedingNumber": "IPR2023-00001"}

        result = await ptab_client.get_proceeding("IPR2023-00001")

        mock_request.assert_called_once()
        assert "/proceedings/IPR2023-00001" in mock_request.call_args[0][0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_proceeding_documents(ptab_client):
    """Test getting documents for a proceeding."""
    with patch.object(ptab_client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"documents": [], "total": 0}

        result = await ptab_client.get_proceeding_documents(
            "IPR2023-00001",
            document_type="petition"
        )

        mock_request.assert_called_once()
        assert "/proceedings/IPR2023-00001/documents" in mock_request.call_args[0][0]


# ============================================================================
# Decision Search Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_decisions(ptab_client):
    """Test searching PTAB decisions."""
    with patch.object(ptab_client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"results": [], "total": 0}

        result = await ptab_client.search_decisions(
            query="obviousness",
            decision_type="final"
        )

        mock_request.assert_called_once()
        assert "/decisions/search" in mock_request.call_args[0][0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_decision(ptab_client):
    """Test getting a specific decision."""
    with patch.object(ptab_client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"decisionId": "12345"}

        result = await ptab_client.get_decision("12345")

        mock_request.assert_called_once()
        assert "/decisions/12345" in mock_request.call_args[0][0]


# ============================================================================
# Appeal Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_appeals(ptab_client):
    """Test searching ex parte appeals."""
    with patch.object(ptab_client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"results": [], "total": 0}

        result = await ptab_client.search_appeals(
            application_number="12345678",
            decision_date_from="2023-01-01"
        )

        mock_request.assert_called_once()
        assert "/appeals/decisions/search" in mock_request.call_args[0][0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_appeal_decision(ptab_client):
    """Test getting a specific appeal decision."""
    with patch.object(ptab_client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"appealNumber": "2023-001234"}

        result = await ptab_client.get_appeal_decision("2023-001234")

        mock_request.assert_called_once()
        assert "/appeals/decisions/2023-001234" in mock_request.call_args[0][0]


# ============================================================================
# Interference Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_interferences(ptab_client):
    """Test searching historical interferences."""
    with patch.object(ptab_client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"results": [], "total": 0}

        result = await ptab_client.search_interferences(
            patent_number="7654321",
            party_name="Apple"
        )

        mock_request.assert_called_once()
        assert "/interferences/search" in mock_request.call_args[0][0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_interference(ptab_client):
    """Test getting a specific interference."""
    with patch.object(ptab_client, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"interferenceNumber": "105,123"}

        result = await ptab_client.get_interference("105,123")

        mock_request.assert_called_once()


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_http_error_handling(ptab_client):
    """Test handling of HTTP errors."""
    with patch.object(ptab_client.client, 'get', new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_response.json.return_value = {"error": "Not found"}

        error = httpx.HTTPStatusError("Not Found", request=MagicMock(), response=mock_response)
        mock_get.side_effect = error

        result = await ptab_client._make_request("/test")

        assert result.get("error") is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_network_error_retry(ptab_client):
    """Test network error retry logic."""
    with patch.object(ptab_client.client, 'get', new_callable=AsyncMock) as mock_get:
        mock_success = MagicMock()
        mock_success.status_code = 200
        mock_success.json.return_value = {"result": "success"}
        mock_success.raise_for_status = MagicMock()

        mock_get.side_effect = [
            httpx.NetworkError("Connection failed"),
            mock_success
        ]

        result = await ptab_client._make_request("/test")

        assert result == {"result": "success"}
        assert mock_get.call_count == 2


# ============================================================================
# Cleanup Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_close():
    """Test client cleanup."""
    client = PTABClient()

    with patch.object(client.client, 'aclose', new_callable=AsyncMock) as mock_close:
        await client.close()
        mock_close.assert_called_once()
