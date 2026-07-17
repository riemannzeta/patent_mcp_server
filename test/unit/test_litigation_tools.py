"""Tool-layer tests: litigation_* tools call CourtListenerClient and envelope results.

These tools (and the four revived legacy aliases) are backed by CourtListener /
RECAP. The client is mocked, so no network access is needed.
"""

from unittest.mock import AsyncMock, patch

import pytest

from patent_mcp_server.constants import LitigationDefaults
from patent_mcp_server.patents import (
    litigation_search_cases,
    litigation_get_case,
    litigation_get_patent_cases,
    litigation_get_party_cases,
    litigation_list_documents,
    litigation_get_document,
    litigation_search_opinions,
    litigation_get_opinion,
    # revived legacy aliases
    search_litigation,
    get_litigation_case,
    get_patent_litigation,
    get_party_litigation,
)

# CourtListener paginated search/list envelope
SEARCH = {
    "count": 1,
    "next": "https://www.courtlistener.com/api/rest/v4/search/?cursor=abc",
    "previous": None,
    "results": [{"docket_id": 42, "caseName": "Acme v. Example"}],
}
# Single detail record
DOCKET = {"id": 42, "case_name": "Acme v. Example", "court": "txed"}
OPINION = {"id": 99, "plain_text": "It is so ordered.", "download_url": "http://x/y.pdf"}
RECAP_DOC = {
    "id": 7,
    "is_available": True,
    "plain_text": "Brief in support ...",
    "filepath_local": "/x/7.pdf",
}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_cases_returns_envelope():
    with patch("patent_mcp_server.patents.courtlistener_client.search_dockets",
               new=AsyncMock(return_value=SEARCH)):
        r = await litigation_search_cases(patent_number="8123456", court="cafc")
    assert r["success"] is True
    assert r["source"] == "courtlistener"
    assert r["total"] == 1
    assert r["results"][0]["docket_id"] == 42
    # cursor pagination surfaced in metadata
    assert "next" in r["metadata"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_case_single_record():
    with patch("patent_mcp_server.patents.courtlistener_client.get_docket",
               new=AsyncMock(return_value=DOCKET)):
        r = await litigation_get_case(docket_id="42")
    assert r["success"] is True
    assert r["source"] == "courtlistener"
    assert r["results"]["court"] == "txed"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_opinions_and_get_opinion():
    with patch("patent_mcp_server.patents.courtlistener_client.search_opinions",
               new=AsyncMock(return_value=SEARCH)):
        s = await litigation_search_opinions(query="claim construction", court="cafc")
    assert s["success"] is True
    assert s["source"] == "courtlistener"

    with patch("patent_mcp_server.patents.courtlistener_client.get_opinion",
               new=AsyncMock(return_value=OPINION)):
        r = await litigation_get_opinion(opinion_id="99")
    assert r["success"] is True
    assert r["results"]["plain_text"] == "It is so ordered."


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_documents_and_get_document():
    with patch("patent_mcp_server.patents.courtlistener_client.search_recap_documents",
               new=AsyncMock(return_value=SEARCH)):
        listed = await litigation_list_documents(docket_id="42", document_type="brief")
    assert listed["success"] is True

    with patch("patent_mcp_server.patents.courtlistener_client.get_recap_document",
               new=AsyncMock(return_value=RECAP_DOC)):
        doc = await litigation_get_document(recap_document_id="7")
    assert doc["success"] is True
    assert doc["results"]["filepath_local"] == "/x/7.pdf"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_opinion_text_is_capped():
    big = {"id": 1, "plain_text": "x" * (LitigationDefaults.MAX_TEXT_CHARS + 5000)}
    with patch("patent_mcp_server.patents.courtlistener_client.get_opinion",
               new=AsyncMock(return_value=big)):
        r = await litigation_get_opinion(opinion_id="1")
    assert len(r["results"]["plain_text"]) == LitigationDefaults.MAX_TEXT_CHARS
    assert r["results"]["_plain_text_truncated"] is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_document_absent_without_pacer_creds():
    """Document not in RECAP, no fetch requested -> note, not a crash."""
    absent = {"id": 7, "is_available": False, "plain_text": ""}
    with patch("patent_mcp_server.patents.courtlistener_client.get_recap_document",
               new=AsyncMock(return_value=absent)):
        r = await litigation_get_document(recap_document_id="7")
    assert r["success"] is True
    assert "_note" in r["results"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_document_pacer_fetch_not_configured():
    """allow_pacer_fetch=True but no creds -> clear PACER_NOT_CONFIGURED error."""
    absent = {"id": 7, "is_available": False, "plain_text": ""}
    with patch("patent_mcp_server.patents.courtlistener_client.get_recap_document",
               new=AsyncMock(return_value=absent)), \
         patch("patent_mcp_server.patents.courtlistener_client.fetch_from_pacer",
               new=AsyncMock(return_value={
                   "error": True, "error_code": "PACER_NOT_CONFIGURED",
                   "message": "PACER credentials are not configured."})):
        r = await litigation_get_document(recap_document_id="7", allow_pacer_fetch=True)
    assert r["error"] is True
    assert r["error_code"] == "PACER_NOT_CONFIGURED"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_client_errors_propagate():
    err = {"error": True, "message": "boom", "status_code": 500}
    with patch("patent_mcp_server.patents.courtlistener_client.search_dockets",
               new=AsyncMock(return_value=err)):
        r = await litigation_search_cases(query="x")
    assert r["error"] is True
    assert r.get("success") is not True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_legacy_litigation_tools_no_longer_unavailable():
    """The four revived tools return live envelopes, not API_UNAVAILABLE."""
    with patch.multiple(
        "patent_mcp_server.patents.courtlistener_client",
        search_dockets=AsyncMock(return_value=SEARCH),
        get_docket=AsyncMock(return_value=DOCKET),
    ):
        results = [
            await search_litigation(query="patent"),
            await get_litigation_case(case_id="42"),
            await get_patent_litigation(patent_number="8123456"),
            await get_party_litigation(party_name="Acme"),
        ]
    for r in results:
        assert r.get("error_code") != "API_UNAVAILABLE"
        assert r["success"] is True
        assert r["source"] == "courtlistener"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_api_status_reports_litigation_live():
    from patent_mcp_server.patents import check_api_status

    status = (await check_api_status())["sources"]
    assert "courtlistener" in status
    assert status["courtlistener"]["configured"] is True
    # litigation is no longer flagged UNAVAILABLE
    assert status["litigation"].get("status") != "UNAVAILABLE"
    assert "pacer" in status
