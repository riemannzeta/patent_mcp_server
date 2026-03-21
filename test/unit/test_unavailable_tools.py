"""Tests for tools that return API_UNAVAILABLE after developer.uspto.gov decommission."""

import pytest

from patent_mcp_server.patents import (
    get_office_action_text,
    search_office_actions,
    get_office_action_citations,
    get_office_action_rejections,
    get_enriched_citations,
    search_citations,
    get_citation_metrics,
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
class TestUnavailableToolErrorStructure:
    """Verify all 7 tools return a consistent error structure."""

    TOOLS_WITH_ARGS = [
        (get_office_action_text, {"application_number": "16123456"}),
        (search_office_actions, {}),
        (get_office_action_citations, {"application_number": "16123456"}),
        (get_office_action_rejections, {"application_number": "16123456"}),
        (get_enriched_citations, {"patent_number": "US11234567B2"}),
        (search_citations, {"citing_patent": "16123456"}),
        (get_citation_metrics, {"patent_number": "US11234567B2"}),
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
