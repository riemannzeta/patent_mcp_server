"""Tool-layer tests: PTAB tools call PTABClient and envelope results."""
from unittest.mock import AsyncMock, patch
import pytest
from patent_mcp_server.patents import (
    ptab_search_proceedings, ptab_get_proceeding, ptab_get_documents,
    ptab_search_decisions, ptab_get_decision, ptab_search_appeals,
    ptab_get_appeal,
)

PROC = {"count": 1, "patentTrialProceedingDataBag": [{"trialNumber": "IPR2022-00001"}]}


@pytest.mark.unit
async def test_search_proceedings_returns_envelope():
    with patch("patent_mcp_server.patents.ptab_client.search_proceedings",
               new=AsyncMock(return_value=PROC)):
        r = await ptab_search_proceedings(query="estoppel", limit=5)
    assert r["success"] is True
    assert r["source"] == "ptab"
    assert r["results"][0]["trialNumber"] == "IPR2022-00001"


@pytest.mark.unit
async def test_all_seven_tools_no_longer_unavailable():
    bags = {
        "search_proceedings": PROC, "get_proceeding": PROC,
        "get_proceeding_documents": {"count": 0, "patentTrialDocumentDataBag": []},
        "search_decisions": {"count": 0, "patentTrialDocumentDataBag": []},
        "get_decision": {"count": 0, "patentTrialDocumentDataBag": []},
        "search_appeals": {"count": 0, "patentAppealDataBag": []},
        "get_appeal_decision": {"count": 0, "patentAppealDataBag": []},
    }
    with patch.multiple(
        "patent_mcp_server.patents.ptab_client",
        **{k: AsyncMock(return_value=v) for k, v in bags.items()},
    ):
        results = [
            await ptab_search_proceedings(query="x"),
            await ptab_get_proceeding(proceeding_number="IPR2022-00001"),
            await ptab_get_documents(proceeding_number="IPR2022-00001"),
            await ptab_search_decisions(query="x"),
            await ptab_get_decision(decision_id="IPR2022-00001"),
            await ptab_search_appeals(query="x"),
            await ptab_get_appeal(appeal_number="2026001737"),
        ]
    for r in results:
        assert r.get("error_code") != "API_UNAVAILABLE"
        assert r.get("success") is True


@pytest.mark.unit
async def test_check_api_status_reports_ptab_available():
    from patent_mcp_server.patents import check_api_status
    s = await check_api_status()
    ptab = s["sources"]["ptab"]
    odp = s["sources"]["odp"]
    # PTAB is an active, key-gated source like ODP. The "status" key is
    # reserved as the UNAVAILABLE marker, so active sources omit it; PTAB
    # must mirror the ODP active-source shape rather than carry status.
    assert "status" not in ptab
    assert "status" not in odp
    assert ptab["configured"] == odp["configured"]
    assert "api_key_set" in ptab
