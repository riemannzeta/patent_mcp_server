"""Tests for tools that return API_UNAVAILABLE after API decommissions."""

import pytest

from patent_mcp_server.patents import (
    get_office_action_text,
    search_office_actions,
    get_office_action_citations,
    get_office_action_rejections,
    get_enriched_citations,
    search_citations,
    get_citation_metrics,
    patentsview_search_patents,
    patentsview_get_patent,
    patentsview_search_assignees,
    patentsview_get_assignee,
    patentsview_search_inventors,
    patentsview_get_inventor,
    patentsview_get_claims,
    patentsview_get_description,
    patentsview_search_by_cpc,
    patentsview_lookup_cpc,
    patentsview_search_attorneys,
    patentsview_get_attorney,
    patentsview_lookup_ipc,
    patentsview_search_by_ipc,
)


@pytest.mark.unit
class TestUnavailableOfficeActionTools:
    """All 4 office action tools should return API_UNAVAILABLE."""

    @pytest.mark.asyncio
    async def test_get_office_action_text(self):
        result = await get_office_action_text(application_number="16123456")
        assert result["error"] is True
        assert result["error_code"] == "API_UNAVAILABLE"
        assert "workaround" in result
        assert "message" in result

    @pytest.mark.asyncio
    async def test_search_office_actions(self):
        result = await search_office_actions(query="test")
        assert result["error"] is True
        assert result["error_code"] == "API_UNAVAILABLE"
        assert "workaround" in result

    @pytest.mark.asyncio
    async def test_get_office_action_citations(self):
        result = await get_office_action_citations(application_number="16123456")
        assert result["error"] is True
        assert result["error_code"] == "API_UNAVAILABLE"
        assert "workaround" in result

    @pytest.mark.asyncio
    async def test_get_office_action_rejections(self):
        result = await get_office_action_rejections(application_number="16123456")
        assert result["error"] is True
        assert result["error_code"] == "API_UNAVAILABLE"
        assert "workaround" in result


@pytest.mark.unit
class TestUnavailableEnrichedCitationTools:
    """All 3 enriched citation tools should return API_UNAVAILABLE."""

    @pytest.mark.asyncio
    async def test_get_enriched_citations(self):
        result = await get_enriched_citations(patent_number="US11234567B2")
        assert result["error"] is True
        assert result["error_code"] == "API_UNAVAILABLE"
        assert "workaround" in result

    @pytest.mark.asyncio
    async def test_search_citations(self):
        result = await search_citations(citing_patent="16123456")
        assert result["error"] is True
        assert result["error_code"] == "API_UNAVAILABLE"
        assert "workaround" in result

    @pytest.mark.asyncio
    async def test_get_citation_metrics(self):
        result = await get_citation_metrics(patent_number="US11234567B2")
        assert result["error"] is True
        assert result["error_code"] == "API_UNAVAILABLE"
        assert "workaround" in result


@pytest.mark.unit
class TestUnavailablePatentsViewTools:
    """All 14 PatentsView tools should return API_UNAVAILABLE.

    The PatentsView API (search.patentsview.org) was shut down on March 20, 2026.
    """

    @pytest.mark.asyncio
    async def test_patentsview_search_patents(self):
        result = await patentsview_search_patents(query="neural network")
        assert result["error"] is True
        assert result["error_code"] == "API_UNAVAILABLE"
        assert "workaround" in result

    @pytest.mark.asyncio
    async def test_patentsview_get_patent(self):
        result = await patentsview_get_patent(patent_id="7861317")
        assert result["error"] is True
        assert result["error_code"] == "API_UNAVAILABLE"
        assert "workaround" in result

    @pytest.mark.asyncio
    async def test_patentsview_search_assignees(self):
        result = await patentsview_search_assignees(name="Apple")
        assert result["error"] is True
        assert result["error_code"] == "API_UNAVAILABLE"
        assert "workaround" in result

    @pytest.mark.asyncio
    async def test_patentsview_get_assignee(self):
        result = await patentsview_get_assignee(assignee_id="test-id")
        assert result["error"] is True
        assert result["error_code"] == "API_UNAVAILABLE"
        assert "workaround" in result

    @pytest.mark.asyncio
    async def test_patentsview_search_inventors(self):
        result = await patentsview_search_inventors(name="Smith")
        assert result["error"] is True
        assert result["error_code"] == "API_UNAVAILABLE"
        assert "workaround" in result

    @pytest.mark.asyncio
    async def test_patentsview_get_inventor(self):
        result = await patentsview_get_inventor(inventor_id="test-id")
        assert result["error"] is True
        assert result["error_code"] == "API_UNAVAILABLE"
        assert "workaround" in result

    @pytest.mark.asyncio
    async def test_patentsview_get_claims(self):
        result = await patentsview_get_claims(patent_id="7861317")
        assert result["error"] is True
        assert result["error_code"] == "API_UNAVAILABLE"
        assert "workaround" in result

    @pytest.mark.asyncio
    async def test_patentsview_get_description(self):
        result = await patentsview_get_description(patent_id="7861317")
        assert result["error"] is True
        assert result["error_code"] == "API_UNAVAILABLE"
        assert "workaround" in result

    @pytest.mark.asyncio
    async def test_patentsview_search_by_cpc(self):
        result = await patentsview_search_by_cpc(cpc_code="G06N3/08")
        assert result["error"] is True
        assert result["error_code"] == "API_UNAVAILABLE"
        assert "workaround" in result

    @pytest.mark.asyncio
    async def test_patentsview_lookup_cpc(self):
        result = await patentsview_lookup_cpc(cpc_code="G06")
        assert result["error"] is True
        assert result["error_code"] == "API_UNAVAILABLE"
        assert "workaround" in result

    @pytest.mark.asyncio
    async def test_patentsview_search_attorneys(self):
        result = await patentsview_search_attorneys(name="Smith")
        assert result["error"] is True
        assert result["error_code"] == "API_UNAVAILABLE"
        assert "workaround" in result

    @pytest.mark.asyncio
    async def test_patentsview_get_attorney(self):
        result = await patentsview_get_attorney(attorney_id="test-id")
        assert result["error"] is True
        assert result["error_code"] == "API_UNAVAILABLE"
        assert "workaround" in result

    @pytest.mark.asyncio
    async def test_patentsview_lookup_ipc(self):
        result = await patentsview_lookup_ipc(ipc_code="G06F")
        assert result["error"] is True
        assert result["error_code"] == "API_UNAVAILABLE"
        assert "workaround" in result

    @pytest.mark.asyncio
    async def test_patentsview_search_by_ipc(self):
        result = await patentsview_search_by_ipc(ipc_code="G06F")
        assert result["error"] is True
        assert result["error_code"] == "API_UNAVAILABLE"
        assert "workaround" in result


@pytest.mark.unit
class TestUnavailableToolErrorStructure:
    """Verify all 21 unavailable tools return a consistent error structure."""

    TOOLS_WITH_ARGS = [
        # Office Action tools (decommissioned early 2026)
        (get_office_action_text, {"application_number": "16123456"}),
        (search_office_actions, {}),
        (get_office_action_citations, {"application_number": "16123456"}),
        (get_office_action_rejections, {"application_number": "16123456"}),
        # Enriched Citation tools (decommissioned early 2026)
        (get_enriched_citations, {"patent_number": "US11234567B2"}),
        (search_citations, {"citing_patent": "16123456"}),
        (get_citation_metrics, {"patent_number": "US11234567B2"}),
        # PatentsView tools (shut down March 20, 2026)
        (patentsview_search_patents, {"query": "test"}),
        (patentsview_get_patent, {"patent_id": "7861317"}),
        (patentsview_search_assignees, {"name": "IBM"}),
        (patentsview_get_assignee, {"assignee_id": "test-id"}),
        (patentsview_search_inventors, {"name": "Smith"}),
        (patentsview_get_inventor, {"inventor_id": "test-id"}),
        (patentsview_get_claims, {"patent_id": "7861317"}),
        (patentsview_get_description, {"patent_id": "7861317"}),
        (patentsview_search_by_cpc, {"cpc_code": "G06N3/08"}),
        (patentsview_lookup_cpc, {"cpc_code": "G06"}),
        (patentsview_search_attorneys, {"name": "Smith"}),
        (patentsview_get_attorney, {"attorney_id": "test-id"}),
        (patentsview_lookup_ipc, {"ipc_code": "G06F"}),
        (patentsview_search_by_ipc, {"ipc_code": "G06F"}),
    ]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("tool_func,kwargs", TOOLS_WITH_ARGS)
    async def test_consistent_error_keys(self, tool_func, kwargs):
        result = await tool_func(**kwargs)
        assert set(result.keys()) == {"error", "message", "error_code", "workaround"}
        assert result["error"] is True
        assert result["error_code"] == "API_UNAVAILABLE"
        assert isinstance(result["message"], str)
        assert isinstance(result["workaround"], str)
        assert len(result["message"]) > 20  # Not a stub
