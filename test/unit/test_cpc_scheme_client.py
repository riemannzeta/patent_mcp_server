"""Unit tests for the CPC scheme client and the get_cpc_info tool on top of it."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx2
import pytest

from patent_mcp_server import patents
from patent_mcp_server.constants import CpcDefaults
from patent_mcp_server.uspto.cpc_scheme_client import (
    CpcSchemeClient,
    normalize_cpc_symbol,
    parse_scheme_page,
)
from test.fixtures.cpc_scheme_responses import MOCK_CPC_G06N_PAGE


def _page_response(status=200, text=MOCK_CPC_G06N_PAGE):
    response = MagicMock(spec=httpx2.Response)
    response.status_code = status
    response.text = text
    return response


@pytest.fixture
async def cpc_client():
    client = CpcSchemeClient()
    yield client
    await client.close()


# ============================================================================
# Symbol normalization
# ============================================================================

@pytest.mark.unit
@pytest.mark.parametrize("raw,symbol,display,group", [
    ("G06N3/08", "G06N3/08", "G06N 3/08", "3/08"),
    ("G06N 3/08", "G06N3/08", "G06N 3/08", "3/08"),
    ("g06n 3/08", "G06N3/08", "G06N 3/08", "3/08"),
    ("G06N 3/08 (2006.01)", "G06N3/08", "G06N 3/08", "3/08"),
    ("H04B7/0417 20130101", "H04B7/0417", "H04B 7/0417", "7/0417"),
    ("G06N0003/08", "G06N3/08", "G06N 3/08", "3/08"),
    ("G06N20/00", "G06N20/00", "G06N 20/00", "20/00"),
    ("G06N", "G06N", "G06N", None),
    ("G06", "G06", "G06", None),
    ("G", "G", "G", None),
])
def test_normalize_cpc_symbol(raw, symbol, display, group):
    parts = normalize_cpc_symbol(raw)
    assert parts["symbol"] == symbol
    assert parts["display"] == display
    assert parts["group"] == group
    assert parts["section"] == symbol[0]


@pytest.mark.unit
@pytest.mark.parametrize("raw", ["", "neural networks", "3/08", "G06N3", "G6N3/08", "GN3/08"])
def test_normalize_cpc_symbol_rejects_non_symbols(raw):
    assert normalize_cpc_symbol(raw) is None


# ============================================================================
# Page parsing
# ============================================================================

@pytest.mark.unit
def test_parse_scheme_page_entries_and_indents():
    entries = parse_scheme_page(MOCK_CPC_G06N_PAGE)
    by_symbol = {e["symbol"]: e for e in entries}

    assert [e["symbol"] for e in entries][:4] == ["G06N", "G06N3/00", "G06N3/002", "G06N3/02"]
    assert by_symbol["G06N"]["indent"] == -1
    assert by_symbol["G06N"]["title"] == "COMPUTING ARRANGEMENTS BASED ON SPECIFIC COMPUTATIONAL MODELS"
    assert by_symbol["G06N3/00"]["indent"] == 0
    assert by_symbol["G06N3/08"] == {
        "symbol": "G06N3/08", "title": "Learning methods", "indent": 2, "cpc_specific": False,
    }
    assert by_symbol["G06N3/084"]["title"] == "Backpropagation, e.g. using gradient descent"


@pytest.mark.unit
def test_parse_scheme_page_unwraps_cpc_specific_titles():
    by_symbol = {e["symbol"]: e for e in parse_scheme_page(MOCK_CPC_G06N_PAGE)}
    art = by_symbol["G06N3/0409"]
    assert art["cpc_specific"] is True
    assert art["title"] == "Adaptive resonance theory [ART] networks"
    assert by_symbol["G06N3/002"]["title"].startswith("Biomolecular computers")


@pytest.mark.unit
def test_parse_scheme_page_drops_revision_dates_and_notes():
    by_symbol = {e["symbol"]: e for e in parse_scheme_page(MOCK_CPC_G06N_PAGE)}
    assert "[2023-01]" not in by_symbol["G06N3/08"]["title"]
    assert "WARNING" not in by_symbol["G06N3/08"]["title"]


@pytest.mark.unit
def test_parse_scheme_page_empty_on_unexpected_markup():
    assert parse_scheme_page("<html><body>maintenance</body></html>") == []


# ============================================================================
# Lookup and hierarchy
# ============================================================================

@pytest.mark.unit
async def test_lookup_subgroup_hierarchy_and_children(cpc_client):
    with patch.object(cpc_client.client, "get", new_callable=AsyncMock,
                      return_value=_page_response()) as get:
        result = await cpc_client.lookup("G06N 3/08")

    get.assert_awaited_once_with(
        "https://www.uspto.gov/web/patents/classification/cpc/html/cpc-G06N.html"
    )
    assert result["code"] == "G06N 3/08"
    assert result["title"] == "Learning methods"
    assert result["level"] == "subgroup"
    assert [h["symbol"] for h in result["hierarchy"]] == ["G06N", "G06N 3/00", "G06N 3/02", "G06N 3/08"]
    assert [c["symbol"] for c in result["children"]] == ["G06N 3/082", "G06N 3/084", "G06N 3/0985"]
    assert result["child_count"] == 3
    assert result["source"].endswith("cpc-G06N.html")


@pytest.mark.unit
async def test_lookup_subclass_lists_main_groups(cpc_client):
    with patch.object(cpc_client.client, "get", new_callable=AsyncMock,
                      return_value=_page_response()):
        result = await cpc_client.lookup("G06N")

    assert result["level"] == "subclass"
    assert result["title"].startswith("COMPUTING ARRANGEMENTS")
    assert result["hierarchy"] == [{"symbol": "G06N", "title": result["title"]}]
    assert [c["symbol"] for c in result["children"]] == ["G06N 3/00", "G06N 20/00"]


@pytest.mark.unit
async def test_lookup_main_group(cpc_client):
    with patch.object(cpc_client.client, "get", new_callable=AsyncMock,
                      return_value=_page_response()):
        result = await cpc_client.lookup("G06N3/00")

    assert result["level"] == "main_group"
    assert [h["symbol"] for h in result["hierarchy"]] == ["G06N", "G06N 3/00"]
    assert [c["symbol"] for c in result["children"]] == ["G06N 3/002", "G06N 3/02"]


@pytest.mark.unit
async def test_lookup_unknown_group_names_the_main_groups(cpc_client):
    with patch.object(cpc_client.client, "get", new_callable=AsyncMock,
                      return_value=_page_response()):
        result = await cpc_client.lookup("G06N 99/99")

    assert result["error"] is True
    assert result["error_code"] == "NOT_FOUND"
    assert [g["symbol"] for g in result["details"]["main_groups"]] == ["G06N 3/00", "G06N 20/00"]


@pytest.mark.unit
async def test_lookup_rejects_codes_without_a_subclass(cpc_client):
    with patch.object(cpc_client.client, "get", new_callable=AsyncMock) as get:
        assert (await cpc_client.lookup("G06"))["error"] is True
        assert (await cpc_client.lookup("neural nets"))["error"] is True
    get.assert_not_awaited()


@pytest.mark.unit
async def test_lookup_unknown_subclass_is_not_found(cpc_client):
    with patch.object(cpc_client.client, "get", new_callable=AsyncMock,
                      return_value=_page_response(404, "nope")):
        result = await cpc_client.lookup("G06Z 1/00")
    assert result["error"] is True
    assert "G06Z" in result["message"]


@pytest.mark.unit
async def test_lookup_reports_parse_failure(cpc_client):
    with patch.object(cpc_client.client, "get", new_callable=AsyncMock,
                      return_value=_page_response(200, "<html>changed</html>")):
        result = await cpc_client.lookup("G06N 3/08")
    assert result["error_code"] == "PARSE_ERROR"


@pytest.mark.unit
async def test_lookup_network_error_is_an_error_dict(cpc_client):
    with patch.object(cpc_client.client, "get", new_callable=AsyncMock,
                      side_effect=httpx2.ConnectError("down")):
        result = await cpc_client.lookup("G06N 3/08")
    assert result["error"] is True


# ============================================================================
# Cache
# ============================================================================

@pytest.mark.unit
async def test_subclass_page_is_fetched_once_per_day(cpc_client):
    with patch.object(cpc_client.client, "get", new_callable=AsyncMock,
                      return_value=_page_response()) as get:
        await cpc_client.lookup("G06N 3/08")
        await cpc_client.lookup("G06N 20/00")
        await cpc_client.lookup("G06N")
    assert get.await_count == 1

    # Expire the entry and it is fetched again
    fetched_at, entries = cpc_client._cache["G06N"]
    cpc_client._cache["G06N"] = (fetched_at - CpcDefaults.CACHE_SECONDS - 1, entries)
    with patch.object(cpc_client.client, "get", new_callable=AsyncMock,
                      return_value=_page_response()) as get:
        await cpc_client.lookup("G06N 3/08")
    assert get.await_count == 1


@pytest.mark.unit
async def test_errors_are_not_cached(cpc_client):
    with patch.object(cpc_client.client, "get", new_callable=AsyncMock,
                      return_value=_page_response(503, "busy")) as get:
        assert (await cpc_client.lookup("G06N 3/08"))["error"] is True
        assert (await cpc_client.lookup("G06N 3/08"))["error"] is True
    assert get.await_count == 2
    assert "G06N" not in cpc_client._cache


# ============================================================================
# get_cpc_info tool
# ============================================================================

@pytest.fixture(autouse=True)
def _fresh_shared_cache():
    """The tool uses the module-level client; keep its cache out of these tests."""
    patents.cpc_scheme_client._cache.clear()
    yield
    patents.cpc_scheme_client._cache.clear()


@pytest.mark.unit
async def test_get_cpc_info_section_stays_static():
    with patch.object(patents.cpc_scheme_client, "lookup", new_callable=AsyncMock) as lookup:
        result = await patents.get_cpc_info("G")
    lookup.assert_not_awaited()
    assert result["title"] == "Physics"
    assert "subsections" in result


@pytest.mark.unit
async def test_get_cpc_info_class_stays_static():
    with patch.object(patents.cpc_scheme_client, "lookup", new_callable=AsyncMock) as lookup:
        result = await patents.get_cpc_info("G06")
    lookup.assert_not_awaited()
    assert result["code"] == "G06"
    assert result["section_title"] == "Physics"
    assert result["class_title"]
    assert "title" not in result


@pytest.mark.unit
async def test_get_cpc_info_group_merges_static_and_scheme():
    with patch.object(patents.cpc_scheme_client.client, "get", new_callable=AsyncMock,
                      return_value=_page_response()):
        result = await patents.get_cpc_info("G06N3/08")

    assert result["code"] == "G06N 3/08"
    assert result["title"] == "Learning methods"
    assert result["section"] == "G" and result["section_title"] == "Physics"
    assert result["class_title"]  # "Computing; Calculating; Counting" from the static table
    assert result["subclass_title"].startswith("COMPUTING ARRANGEMENTS")
    assert [h["symbol"] for h in result["hierarchy"]][-1] == "G06N 3/08"
    assert "error" not in result


@pytest.mark.unit
async def test_get_cpc_info_falls_back_to_static_when_scheme_unavailable():
    with patch.object(patents.cpc_scheme_client.client, "get", new_callable=AsyncMock,
                      side_effect=httpx2.ConnectError("down")):
        result = await patents.get_cpc_info("G06N3/08")

    assert result["code"] == "G06N 3/08"
    assert "title" not in result
    assert result["section_title"] == "Physics"
    assert result["scheme_error"]["error"] is True


@pytest.mark.unit
async def test_get_cpc_info_unknown_group_is_an_error_not_a_fallback():
    """A code the scheme lacks must not come back wearing the class title."""
    with patch.object(patents.cpc_scheme_client.client, "get", new_callable=AsyncMock,
                      return_value=_page_response()):
        result = await patents.get_cpc_info("G06N 99/99")

    assert result["error"] is True
    assert result["error_code"] == "NOT_FOUND"
    assert "title" not in result
    assert result["details"]["static"]["class_title"]
    assert [g["symbol"] for g in result["details"]["main_groups"]][:1] == ["G06N 3/00"]


@pytest.mark.unit
async def test_get_cpc_info_unknown_subclass_is_an_error():
    with patch.object(patents.cpc_scheme_client.client, "get", new_callable=AsyncMock,
                      return_value=_page_response(404, "nope")):
        result = await patents.get_cpc_info("G06Z 1/00")
    assert result["error"] is True
    assert "title" not in result
