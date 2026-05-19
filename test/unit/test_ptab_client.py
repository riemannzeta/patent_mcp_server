"""Unit tests for PTABClient (live ODP v3.0 contract).

These assert the NEW contract: full paths after host, a single `q=` built
from verified PTABFields clauses, single-record fetches routed through the
search endpoints (no `/{id}` routes exist on ODP), and appeals living under
`/api/v1/patent/appeals` (NOT under `/trials`).
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from patent_mcp_server.uspto.ptab_client import PTABClient
from patent_mcp_server.constants import PTABFields


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
async def test_client_initialization():
    """Client exposes host-only api_base (no /trials coupling)."""
    client = PTABClient()

    assert "User-Agent" in client.headers
    assert "X-API-KEY" in client.headers
    assert client.client is not None
    assert client.api_base == "https://api.uspto.gov"
    assert not hasattr(client, "base_url")

    await client.close()


@pytest.mark.unit
async def test_client_context_manager():
    """Test client context manager protocol."""
    async with PTABClient() as client:
        assert client is not None
        assert client.client is not None


# ============================================================================
# Core contract tests (from the plan, Step 1)
# ============================================================================

@pytest.mark.unit
async def test_search_proceedings_builds_q_and_correct_path(ptab_client):
    with patch.object(ptab_client, "_make_request", new_callable=AsyncMock) as m:
        m.return_value = {"count": 0, "patentTrialProceedingDataBag": []}
        await ptab_client.search_proceedings(
            query="estoppel", patent_number="8667559", offset=5, limit=3
        )
    path, kwargs = m.call_args.args[0], m.call_args.kwargs
    assert path == "/api/v1/patent/trials/proceedings/search"
    q = kwargs["params"]["q"]
    assert "estoppel" in q
    assert "patentOwnerData.patentNumber:8667559" in q
    assert kwargs["params"]["offset"] == 5
    assert kwargs["params"]["limit"] == 3


@pytest.mark.unit
async def test_get_proceeding_uses_search_not_id_route(ptab_client):
    with patch.object(ptab_client, "_make_request", new_callable=AsyncMock) as m:
        m.return_value = {"count": 1, "patentTrialProceedingDataBag": [{}]}
        await ptab_client.get_proceeding("IPR2022-00001")
    path, kwargs = m.call_args.args[0], m.call_args.kwargs
    assert path == "/api/v1/patent/trials/proceedings/search"
    assert kwargs["params"]["q"] == "trialNumber:IPR2022-00001"


@pytest.mark.unit
async def test_get_documents_uses_documents_search(ptab_client):
    with patch.object(ptab_client, "_make_request", new_callable=AsyncMock) as m:
        m.return_value = {"count": 0, "patentTrialDocumentDataBag": []}
        await ptab_client.get_proceeding_documents("IPR2022-00001")
    path, kwargs = m.call_args.args[0], m.call_args.kwargs
    assert path == "/api/v1/patent/trials/documents/search"
    assert kwargs["params"]["q"] == "trialNumber:IPR2022-00001"


@pytest.mark.unit
async def test_appeals_use_appeals_base_path(ptab_client):
    with patch.object(ptab_client, "_make_request", new_callable=AsyncMock) as m:
        m.return_value = {"count": 1, "patentAppealDataBag": [{}]}
        await ptab_client.get_appeal_decision("2026001737")
    path, kwargs = m.call_args.args[0], m.call_args.kwargs
    assert path == "/api/v1/patent/appeals/decisions/search"
    assert kwargs["params"]["q"] == "appealNumber:2026001737"


@pytest.mark.unit
async def test_search_decisions_path_and_q(ptab_client):
    with patch.object(ptab_client, "_make_request", new_callable=AsyncMock) as m:
        m.return_value = {"count": 0, "patentTrialDocumentDataBag": []}
        await ptab_client.search_decisions(query="anticipation")
    path, kwargs = m.call_args.args[0], m.call_args.kwargs
    assert path == "/api/v1/patent/trials/decisions/search"
    assert "anticipation" in kwargs["params"]["q"]


# ============================================================================
# Additional clause-mapping tests (Task 3 verified-field contract)
# ============================================================================

@pytest.mark.unit
async def test_search_proceedings_maps_verified_clauses(ptab_client):
    """trial_type/status/party_name map to nested verified field clauses."""
    with patch.object(ptab_client, "_make_request", new_callable=AsyncMock) as m:
        m.return_value = {"count": 0, "patentTrialProceedingDataBag": []}
        await ptab_client.search_proceedings(
            trial_type="IPR", status="Terminated", party_name="Apple"
        )
    q = m.call_args.kwargs["params"]["q"]
    assert "trialMetaData.trialTypeCode:IPR" in q
    assert "trialMetaData.trialStatusCategory:Terminated" in q
    assert "regularPetitionerData.realPartyInInterestName:Apple" in q
    assert PTABFields.TRIAL_TYPE == "trialMetaData.trialTypeCode"
    assert PTABFields.STATUS == "trialMetaData.trialStatusCategory"
    assert PTABFields.PETITIONER_NAME == "regularPetitionerData.realPartyInInterestName"


@pytest.mark.unit
async def test_search_proceedings_date_range_unquoted(ptab_client):
    """from+to produces an un-quoted bracket range; from-only uses > form."""
    with patch.object(ptab_client, "_make_request", new_callable=AsyncMock) as m:
        m.return_value = {"count": 0, "patentTrialProceedingDataBag": []}
        await ptab_client.search_proceedings(
            filing_date_from="2022-01-01", filing_date_to="2022-12-31"
        )
    q = m.call_args.kwargs["params"]["q"]
    assert "trialMetaData.petitionFilingDate:[2022-01-01 TO 2022-12-31]" in q
    assert '"' not in q  # range value must NOT be double-quoted

    with patch.object(ptab_client, "_make_request", new_callable=AsyncMock) as m:
        m.return_value = {"count": 0, "patentTrialProceedingDataBag": []}
        await ptab_client.search_proceedings(filing_date_from="2022-01-01")
    q = m.call_args.kwargs["params"]["q"]
    assert "trialMetaData.petitionFilingDate:>2022-01-01" in q

    with patch.object(ptab_client, "_make_request", new_callable=AsyncMock) as m:
        m.return_value = {"count": 0, "patentTrialProceedingDataBag": []}
        await ptab_client.search_proceedings(filing_date_to="2022-12-31")
    q = m.call_args.kwargs["params"]["q"]
    assert "trialMetaData.petitionFilingDate:[* TO 2022-12-31]" in q


@pytest.mark.unit
async def test_search_proceedings_party_name_with_space_quoted(ptab_client):
    """A clause value containing whitespace is double-quoted (non-range)."""
    with patch.object(ptab_client, "_make_request", new_callable=AsyncMock) as m:
        m.return_value = {"count": 0, "patentTrialProceedingDataBag": []}
        await ptab_client.search_proceedings(party_name="Apple Inc")
    q = m.call_args.kwargs["params"]["q"]
    assert 'regularPetitionerData.realPartyInInterestName:"Apple Inc"' in q


@pytest.mark.unit
async def test_get_proceeding_documents_document_type_free_text(ptab_client):
    """document_type has no verified field — folded into free text."""
    with patch.object(ptab_client, "_make_request", new_callable=AsyncMock) as m:
        m.return_value = {"count": 0, "patentTrialDocumentDataBag": []}
        await ptab_client.get_proceeding_documents(
            "IPR2022-00001", document_type="Petition", offset=2, limit=4
        )
    kwargs = m.call_args.kwargs
    q = kwargs["params"]["q"]
    assert "trialNumber:IPR2022-00001" in q
    assert "Petition" in q
    assert kwargs["params"]["offset"] == 2
    assert kwargs["params"]["limit"] == 4


@pytest.mark.unit
async def test_get_proceeding_documents_multiword_type_not_phrase_quoted(ptab_client):
    """Multi-word document_type is intentionally folded as loose free text.

    The document_type field name is unverified, so a multi-word value is NOT
    phrase-quoted — it ships as bare tokens (best-effort) until probed.
    """
    with patch.object(ptab_client, "_make_request", new_callable=AsyncMock) as m:
        m.return_value = {"count": 0, "patentTrialDocumentDataBag": []}
        await ptab_client.get_proceeding_documents(
            "IPR2022-00001", document_type="Final Written Decision"
        )
    q = m.call_args.kwargs["params"]["q"]
    assert "trialNumber:IPR2022-00001" in q
    assert "Final Written Decision" in q
    assert '"' not in q  # multi-word unverified term must NOT be phrase-quoted


@pytest.mark.unit
async def test_search_decisions_multiword_type_not_phrase_quoted(ptab_client):
    """Multi-word decision_type is intentionally folded as loose free text."""
    with patch.object(ptab_client, "_make_request", new_callable=AsyncMock) as m:
        m.return_value = {"count": 0, "patentTrialDocumentDataBag": []}
        await ptab_client.search_decisions(decision_type="Final Written Decision")
    q = m.call_args.kwargs["params"]["q"]
    assert "Final Written Decision" in q
    assert '"' not in q  # multi-word unverified term must NOT be phrase-quoted


@pytest.mark.unit
async def test_search_decisions_clauses_and_free_text(ptab_client):
    """proceeding_number/patent_number are clauses; decision_type free text."""
    with patch.object(ptab_client, "_make_request", new_callable=AsyncMock) as m:
        m.return_value = {"count": 0, "patentTrialDocumentDataBag": []}
        await ptab_client.search_decisions(
            query="anticipation",
            decision_type="Final Written Decision",
            proceeding_number="IPR2022-00001",
            patent_number="8667559",
        )
    q = m.call_args.kwargs["params"]["q"]
    assert "anticipation" in q
    assert "Final Written Decision" in q
    assert "trialNumber:IPR2022-00001" in q
    assert "patentOwnerData.patentNumber:8667559" in q


@pytest.mark.unit
async def test_search_decisions_date_range(ptab_client):
    with patch.object(ptab_client, "_make_request", new_callable=AsyncMock) as m:
        m.return_value = {"count": 0, "patentTrialDocumentDataBag": []}
        await ptab_client.search_decisions(
            decision_date_from="2022-01-01", decision_date_to="2022-12-31"
        )
    q = m.call_args.kwargs["params"]["q"]
    assert "decisionData.decisionIssueDate:[2022-01-01 TO 2022-12-31]" in q
    assert '"' not in q


@pytest.mark.unit
async def test_get_decision_routes_through_search_by_trial_number(ptab_client):
    with patch.object(ptab_client, "_make_request", new_callable=AsyncMock) as m:
        m.return_value = {"count": 0, "patentTrialDocumentDataBag": []}
        await ptab_client.get_decision("IPR2022-00001")
    path, kwargs = m.call_args.args[0], m.call_args.kwargs
    assert path == "/api/v1/patent/trials/decisions/search"
    assert kwargs["params"]["q"] == "trialNumber:IPR2022-00001"


@pytest.mark.unit
async def test_search_appeals_application_clause_and_patent_free_text(ptab_client):
    """appeals: application_number -> appellantData clause; patent_number -> free text."""
    with patch.object(ptab_client, "_make_request", new_callable=AsyncMock) as m:
        m.return_value = {"count": 0, "patentAppealDataBag": []}
        await ptab_client.search_appeals(
            query="rejection",
            application_number="90019597",
            appeal_number="2026001737",
            patent_number="8667559",
        )
    path, kwargs = m.call_args.args[0], m.call_args.kwargs
    assert path == "/api/v1/patent/appeals/decisions/search"
    q = kwargs["params"]["q"]
    assert "appellantData.applicationNumberText:90019597" in q
    assert "appealNumber:2026001737" in q
    assert "rejection" in q
    # patent_number folded into free text — NOT a patentOwnerData clause
    assert "patentOwnerData.patentNumber" not in q
    assert "8667559" in q


@pytest.mark.unit
async def test_search_appeals_date_range(ptab_client):
    with patch.object(ptab_client, "_make_request", new_callable=AsyncMock) as m:
        m.return_value = {"count": 0, "patentAppealDataBag": []}
        await ptab_client.search_appeals(
            decision_date_from="2022-01-01", decision_date_to="2022-12-31"
        )
    q = m.call_args.kwargs["params"]["q"]
    assert "decisionData.decisionIssueDate:[2022-01-01 TO 2022-12-31]" in q


@pytest.mark.unit
async def test_get_appeal_alias_resolves_to_get_appeal_decision(ptab_client):
    """Task 4 calls ptab_client.get_appeal; it must alias get_appeal_decision."""
    assert PTABClient.get_appeal is PTABClient.get_appeal_decision
    with patch.object(ptab_client, "_make_request", new_callable=AsyncMock) as m:
        m.return_value = {"count": 1, "patentAppealDataBag": [{}]}
        await ptab_client.get_appeal("2026001737")
    path, kwargs = m.call_args.args[0], m.call_args.kwargs
    assert path == "/api/v1/patent/appeals/decisions/search"
    assert kwargs["params"]["q"] == "appealNumber:2026001737"


# ============================================================================
# Interferences — not available on ODP (501)
# ============================================================================

@pytest.mark.unit
async def test_search_interferences_returns_501(ptab_client):
    result = await ptab_client.search_interferences(patent_number="7654321")
    assert result.get("error") is True
    assert result.get("status_code") == 501
    assert "interference" in result.get("message", "").lower()


@pytest.mark.unit
async def test_get_interference_returns_501(ptab_client):
    result = await ptab_client.get_interference("105,123")
    assert result.get("error") is True
    assert result.get("status_code") == 501
    assert "interference" in result.get("message", "").lower()


# ============================================================================
# _build_q helper
# ============================================================================

@pytest.mark.unit
def test_build_q_quotes_whitespace_values_only():
    q = PTABClient._build_q("free text", [("a", "b"), ("c", "d e"), ("x", None)])
    assert q == 'free text a:b c:"d e"'


@pytest.mark.unit
def test_build_q_empty():
    assert PTABClient._build_q(None, []) == ""


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.unit
async def test_http_error_handling(ptab_client):
    """Test handling of HTTP errors."""
    with patch.object(ptab_client.client, "get", new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_response.json.return_value = {"error": "Not found"}

        error = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )
        mock_get.side_effect = error

        result = await ptab_client._make_request("/api/v1/patent/trials/proceedings/search")

        assert result.get("error") is True


@pytest.mark.unit
async def test_make_request_builds_full_url_from_api_base(ptab_client):
    """_make_request joins api_base + full path (no /trials prefix)."""
    with patch.object(ptab_client.client, "get", new_callable=AsyncMock) as mock_get:
        mock_success = MagicMock()
        mock_success.status_code = 200
        mock_success.json.return_value = {"count": 0}
        mock_success.raise_for_status = MagicMock()
        mock_get.return_value = mock_success

        await ptab_client._make_request("/api/v1/patent/appeals/decisions/search")

        called_url = mock_get.call_args.args[0]
        assert called_url == "https://api.uspto.gov/api/v1/patent/appeals/decisions/search"


@pytest.mark.unit
async def test_network_error_retry(ptab_client):
    """Test network error retry logic is preserved."""
    with patch.object(ptab_client.client, "get", new_callable=AsyncMock) as mock_get:
        mock_success = MagicMock()
        mock_success.status_code = 200
        mock_success.json.return_value = {"result": "success"}
        mock_success.raise_for_status = MagicMock()

        mock_get.side_effect = [
            httpx.NetworkError("Connection failed"),
            mock_success,
        ]

        result = await ptab_client._make_request("/api/v1/patent/trials/proceedings/search")

        assert result == {"result": "success"}
        assert mock_get.call_count == 2


# ============================================================================
# Cleanup Tests
# ============================================================================

@pytest.mark.unit
async def test_close():
    """Test client cleanup."""
    client = PTABClient()

    with patch.object(client.client, "aclose", new_callable=AsyncMock) as mock_close:
        await client.close()
        mock_close.assert_called_once()
