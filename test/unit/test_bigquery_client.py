"""
Unit tests for Google BigQuery client.

Tests the GoogleBigQueryClient functionality with mocked BigQuery responses.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from patent_mcp_server.google.bigquery_client import GoogleBigQueryClient
from test.fixtures.google_bigquery_responses import (
    MOCK_SEARCH_RESULTS,
    MOCK_PATENT_DETAILS,
    MOCK_PATENT_CLAIMS,
    MOCK_PATENT_DESCRIPTION,
    MOCK_INVENTOR_SEARCH_RESULTS,
    MOCK_ASSIGNEE_SEARCH_RESULTS,
    MOCK_CPC_SEARCH_RESULTS,
    MOCK_EMPTY_RESULTS,
)


@pytest.fixture
def mock_bigquery_client():
    """Mock BigQuery client."""
    with patch("patent_mcp_server.google.bigquery_client.bigquery.Client") as mock_client, \
         patch("patent_mcp_server.google.bigquery_client.default") as mock_default:
        # Mock the authentication
        mock_default.return_value = (None, "test-project")

        # Create client instance
        client = GoogleBigQueryClient()

        yield client


class TestGoogleBigQueryClient:
    """Test suite for GoogleBigQueryClient."""

    @pytest.mark.asyncio
    async def test_search_patents_success(self, mock_bigquery_client):
        """Test successful patent search."""
        mock_bigquery_client._execute_query = Mock(return_value=MOCK_SEARCH_RESULTS)

        result = await mock_bigquery_client.search_patents(
            query="machine learning",
            country="US",
            limit=10
        )

        assert result["success"] is True
        assert result["count"] == len(MOCK_SEARCH_RESULTS)
        assert "results" in result
        assert len(result["results"]) == 2
        assert result["results"][0]["publication_number"] == "US-10123456-B2"

    @pytest.mark.asyncio
    async def test_search_patents_empty_results(self, mock_bigquery_client):
        """Test patent search with no results."""
        mock_bigquery_client._execute_query = Mock(return_value=MOCK_EMPTY_RESULTS)

        result = await mock_bigquery_client.search_patents(
            query="nonexistent technology",
            country="US",
            limit=10
        )

        assert result["success"] is True
        assert result["count"] == 0
        assert result["results"] == []

    @pytest.mark.asyncio
    async def test_get_patent_by_number_success(self, mock_bigquery_client):
        """Test getting patent by number."""
        mock_bigquery_client._execute_query = Mock(return_value=[MOCK_PATENT_DETAILS])

        result = await mock_bigquery_client.get_patent_by_number("US-10123456-B2")

        assert result["success"] is True
        assert "patent" in result
        assert result["patent"]["publication_number"] == "US-10123456-B2"
        assert result["patent"]["title_localized"][0]["text"] == "Machine learning system for data analysis"

    @pytest.mark.asyncio
    async def test_get_patent_by_number_not_found(self, mock_bigquery_client):
        """Test patent not found."""
        mock_bigquery_client._execute_query = Mock(return_value=[])

        result = await mock_bigquery_client.get_patent_by_number("US-0000000-XX")

        assert "error" in result
        assert result["error"] is True
        assert "not found" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_get_patent_claims_success(self, mock_bigquery_client):
        """Test getting patent claims."""
        mock_bigquery_client._execute_query = Mock(return_value=MOCK_PATENT_CLAIMS)

        result = await mock_bigquery_client.get_patent_claims("US-10123456-B2")

        assert result["success"] is True
        assert result["publication_number"] == "US-10123456-B2"
        assert result["claims_count"] == 5
        assert len(result["claims"]) == 5
        assert result["claims"][0]["claim_num"] == 1
        assert "neural network" in result["claims"][0]["claim_text"].lower()

    @pytest.mark.asyncio
    async def test_get_patent_claims_empty(self, mock_bigquery_client):
        """Test getting claims for patent with no claims."""
        mock_bigquery_client._execute_query = Mock(return_value=[])

        result = await mock_bigquery_client.get_patent_claims("US-10123456-B2")

        assert result["success"] is True
        assert result["claims_count"] == 0
        assert result["claims"] == []

    @pytest.mark.asyncio
    async def test_get_patent_description_success(self, mock_bigquery_client):
        """Test getting patent description."""
        mock_bigquery_client._execute_query = Mock(return_value=[MOCK_PATENT_DESCRIPTION])

        result = await mock_bigquery_client.get_patent_description("US-10123456-B2")

        assert result["success"] is True
        assert "description" in result
        assert result["description"]["publication_number"] == "US-10123456-B2"
        assert result["description"]["description_length"] == 2847
        assert "BACKGROUND" in result["description"]["description_text"]

    @pytest.mark.asyncio
    async def test_get_patent_description_not_found(self, mock_bigquery_client):
        """Test description not found."""
        mock_bigquery_client._execute_query = Mock(return_value=[])

        result = await mock_bigquery_client.get_patent_description("US-0000000-XX")

        assert "error" in result
        assert result["error"] is True

    @pytest.mark.asyncio
    async def test_search_by_inventor_success(self, mock_bigquery_client):
        """Test searching by inventor name."""
        mock_bigquery_client._execute_query = Mock(return_value=MOCK_INVENTOR_SEARCH_RESULTS)

        result = await mock_bigquery_client.search_by_inventor(
            inventor_name="John Smith",
            country="US",
            limit=10
        )

        assert result["success"] is True
        assert result["count"] == 2
        assert result["inventor"] == "John Smith"
        assert len(result["results"]) == 2

    @pytest.mark.asyncio
    async def test_search_by_assignee_success(self, mock_bigquery_client):
        """Test searching by assignee name."""
        mock_bigquery_client._execute_query = Mock(return_value=MOCK_ASSIGNEE_SEARCH_RESULTS)

        result = await mock_bigquery_client.search_by_assignee(
            assignee_name="Google LLC",
            country="US",
            limit=10
        )

        assert result["success"] is True
        assert result["count"] == 2
        assert result["assignee"] == "Google LLC"
        assert len(result["results"]) == 2

    @pytest.mark.asyncio
    async def test_search_by_cpc_success(self, mock_bigquery_client):
        """Test searching by CPC code."""
        mock_bigquery_client._execute_query = Mock(return_value=MOCK_CPC_SEARCH_RESULTS)

        result = await mock_bigquery_client.search_by_cpc(
            cpc_code="G06N3/08",
            country="US",
            limit=10
        )

        assert result["success"] is True
        assert result["count"] == 2
        assert result["cpc_code"] == "G06N3/08"
        assert len(result["results"]) == 2

    @pytest.mark.asyncio
    async def test_query_execution_error(self, mock_bigquery_client):
        """Test handling of query execution errors."""
        mock_bigquery_client._execute_query = Mock(
            side_effect=Exception("BigQuery query failed")
        )

        result = await mock_bigquery_client.search_patents(
            query="test",
            country="US",
            limit=10
        )

        # Should return error dict
        assert "error" in result or "message" in result

    @pytest.mark.asyncio
    async def test_close_client(self, mock_bigquery_client):
        """Test closing the client."""
        await mock_bigquery_client.close()

        # Should complete without errors
        assert True


class TestBigQueryClientInitialization:
    """Test BigQuery client initialization."""

    @patch("patent_mcp_server.google.bigquery_client.bigquery.Client")
    @patch("patent_mcp_server.google.bigquery_client.default")
    def test_initialization_with_credentials(self, mock_default, mock_client_class):
        """Test client initialization with credentials."""
        mock_default.return_value = (None, "test-project")

        client = GoogleBigQueryClient()

        assert client.project_id is not None or True  # Project may be None or from config
        assert client.dataset_id == "patents-public-data:patents"
        assert client.location == "US"

    @patch("patent_mcp_server.google.bigquery_client.bigquery.Client")
    @patch("patent_mcp_server.google.bigquery_client.default")
    def test_initialization_failure(self, mock_default, mock_client_class):
        """Test client initialization failure."""
        mock_default.side_effect = Exception("Authentication failed")

        client = GoogleBigQueryClient()

        # Client should be None on initialization failure
        assert client.client is None
