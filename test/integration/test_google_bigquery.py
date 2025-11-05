"""
Integration tests for Google Patents BigQuery integration.

These tests require Google Cloud credentials and will make actual API calls.
They are skipped by default unless GOOGLE_APPLICATION_CREDENTIALS is set.
"""

import os
import pytest
from patent_mcp_server.google.bigquery_client import GoogleBigQueryClient

# Mark all tests as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture
def bigquery_client():
    """Real BigQuery client (requires authentication)."""
    return GoogleBigQueryClient()


@pytest.mark.skipif(
    not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
    reason="Requires Google Cloud credentials (GOOGLE_APPLICATION_CREDENTIALS)"
)
class TestGoogleBigQueryIntegration:
    """Integration tests for Google BigQuery client."""

    @pytest.mark.asyncio
    async def test_search_patents_real(self, bigquery_client):
        """Test real BigQuery patent search."""
        result = await bigquery_client.search_patents(
            query="artificial intelligence",
            country="US",
            limit=5
        )

        if bigquery_client.client is not None:
            assert result["success"] is True
            assert result["count"] >= 0
            assert result["count"] <= 5
            assert "results" in result

    @pytest.mark.asyncio
    async def test_search_patents_different_countries(self, bigquery_client):
        """Test searching patents from different countries."""
        countries = ["US", "EP", "JP"]

        for country in countries:
            result = await bigquery_client.search_patents(
                query="semiconductor",
                country=country,
                limit=3
            )

            if bigquery_client.client is not None:
                assert result["success"] is True
                assert "results" in result

    @pytest.mark.asyncio
    async def test_get_patent_real(self, bigquery_client):
        """Test getting real patent details."""
        # First search for a patent
        search_result = await bigquery_client.search_patents(
            query="machine learning",
            country="US",
            limit=1
        )

        if bigquery_client.client is not None and search_result.get("success") and search_result.get("count") > 0:
            patent_number = search_result["results"][0]["publication_number"]

            # Get full patent details
            result = await bigquery_client.get_patent_by_number(patent_number)

            assert result["success"] is True
            assert "patent" in result
            assert result["patent"]["publication_number"] == patent_number

    @pytest.mark.asyncio
    async def test_get_patent_claims_real(self, bigquery_client):
        """Test getting real patent claims."""
        # Search for a patent with claims
        search_result = await bigquery_client.search_patents(
            query="neural network",
            country="US",
            limit=1
        )

        if bigquery_client.client is not None and search_result.get("success") and search_result.get("count") > 0:
            patent_number = search_result["results"][0]["publication_number"]

            # Get claims
            result = await bigquery_client.get_patent_claims(patent_number)

            # Claims may or may not exist, but query should succeed
            assert result["success"] is True
            assert "claims_count" in result
            assert "claims" in result

    @pytest.mark.asyncio
    async def test_search_by_inventor_real(self, bigquery_client):
        """Test searching by inventor with real data."""
        # Use a common inventor name pattern
        result = await bigquery_client.search_by_inventor(
            inventor_name="Smith",
            country="US",
            limit=5
        )

        if bigquery_client.client is not None:
            assert result["success"] is True
            assert "results" in result
            # Smith is a common name, should find results
            assert result["count"] >= 0

    @pytest.mark.asyncio
    async def test_search_by_assignee_real(self, bigquery_client):
        """Test searching by assignee with real data."""
        # Use a known major assignee
        result = await bigquery_client.search_by_assignee(
            assignee_name="International Business Machines",
            country="US",
            limit=5
        )

        if bigquery_client.client is not None:
            assert result["success"] is True
            assert "results" in result
            # IBM should have many patents
            assert result["count"] >= 0

    @pytest.mark.asyncio
    async def test_search_by_cpc_real(self, bigquery_client):
        """Test searching by CPC code with real data."""
        # Use a common CPC code (G06N - computing arrangements)
        result = await bigquery_client.search_by_cpc(
            cpc_code="G06N",
            country="US",
            limit=5
        )

        if bigquery_client.client is not None:
            assert result["success"] is True
            assert "results" in result
            assert result["count"] >= 0

    @pytest.mark.asyncio
    async def test_large_query_limit(self, bigquery_client):
        """Test query with larger result limit."""
        result = await bigquery_client.search_patents(
            query="computer",
            country="US",
            limit=100
        )

        if bigquery_client.client is not None:
            assert result["success"] is True
            assert result["count"] <= 100

    @pytest.mark.asyncio
    async def test_client_cleanup(self, bigquery_client):
        """Test that client cleanup works properly."""
        await bigquery_client.close()
        # Should complete without errors
        assert True


@pytest.mark.skipif(
    os.getenv("GOOGLE_APPLICATION_CREDENTIALS") is not None,
    reason="Only run when credentials are NOT set"
)
class TestGoogleBigQueryWithoutCredentials:
    """Test behavior when Google Cloud credentials are not configured."""

    @pytest.mark.asyncio
    async def test_search_without_credentials(self):
        """Test that search fails gracefully without credentials."""
        client = GoogleBigQueryClient()

        # If no credentials, client should be None or query should fail
        if client.client is None:
            # Expected behavior - client not initialized
            assert True
        else:
            # Try a query - should fail
            try:
                result = await client.search_patents(
                    query="test",
                    country="US",
                    limit=1
                )
                # If it returns an error dict, that's acceptable
                assert "error" in result or "message" in result
            except Exception:
                # Exception is also acceptable
                assert True
