"""
Integration tests for ODP Office Action Search and Petition Decisions.

These call api.uspto.gov and need USPTO_API_KEY, so they are deselected
by default (pytest.ini). Records named here were verified live on
2026-10-14 (rejections and citations 2026-10-15); a failure means the
live contract moved.

Run with: uv run pytest -m integration test/test_odp_oa_petitions_integration.py
"""

import pytest

from patent_mcp_server.patents import (
    get_office_action_citations,
    get_office_action_rejections,
    odp_download_document,
    odp_get_documents,
    odp_search_office_actions,
    odp_search_petition_decisions,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

OA_APP_NUMBER = "18402543"          # CTNF 2026-06-24 and CTFR 2026-10-09
PETITION_PATENT_NUMBER = "8462371"  # 533 petition, dismissed 2026-10-05


def _ok(result):
    assert not result.get("error", False), f"Error: {result.get('message')}"


async def test_office_action_document_id_is_in_file_wrapper():
    """A search hit's document_id is the file-wrapper documentIdentifier."""
    result = await odp_search_office_actions(app_num=OA_APP_NUMBER, document_code="CTFR")
    _ok(result)
    assert result["total"] >= 1
    hit = result["results"][0]
    assert hit["document_code"] == "CTFR"
    assert len(hit["text_preview"]) <= 510

    wrapper = await odp_get_documents(app_num=OA_APP_NUMBER, document_code="CTFR")
    _ok(wrapper)
    ids = {d["documentIdentifier"] for d in wrapper["results"]}
    assert hit["document_id"] in ids


async def test_office_action_facet_count():
    """limit=1 still returns facets over the whole match set."""
    result = await odp_search_office_actions(
        rejection_type="101", art_unit="3689",
        date_from="2026-01-01", date_to="2026-06-30", limit=1,
    )
    _ok(result)
    assert result["count"] == 1
    codes = result["metadata"]["facets"]["documentCode"]
    assert sum(codes.values()) == result["total"] > 1
    assert result["metadata"]["facets"]["rejectionTypeBag"]["101"] == result["total"]


async def test_petition_decision_by_patent_number():
    result = await odp_search_petition_decisions(
        patent_number=PETITION_PATENT_NUMBER, petition_type="533",
    )
    _ok(result)
    assert result["total"] >= 1
    hit = result["results"][0]
    assert hit["petition_type_code"] == "533"
    assert hit["app_num"] == "12344137"
    assert hit["documents"][0]["documentIdentifier"]


async def test_office_action_full_text():
    """A search hit's full text comes from the document's XML archive."""
    hits = await odp_search_office_actions(app_num=OA_APP_NUMBER, document_code="CTFR")
    _ok(hits)
    hit = hits["results"][0]
    result = await odp_download_document(OA_APP_NUMBER, hit["document_id"], format="text")
    _ok(result)
    assert result["text"].startswith("DETAILED ACTION")
    assert result["total_chars"] > 5 * len(hit["text_preview"])
    assert "35 U.S.C. 102" in result["text"]


async def test_claims_text_keeps_amendment_markup():
    wrapper = await odp_get_documents(app_num=OA_APP_NUMBER, document_code="CLM")
    _ok(wrapper)
    clm = wrapper["results"][0]["documentIdentifier"]  # newest: the 2026 amendment
    result = await odp_download_document(OA_APP_NUMBER, clm, format="text")
    _ok(result)
    assert "~~" in result["text"] and "++" in result["text"]


async def test_document_without_xml():
    result = await odp_download_document("13806514", "J3DOI1O0RXEAPX1", format="text")
    assert result["error_code"] == "NO_TEXT_AVAILABLE"


async def test_rejections_group_one_action():
    """The CTNF of 2026-06-24 folds its rows into one action."""
    result = await get_office_action_rejections(
        application_number=OA_APP_NUMBER, mail_date="2026-06-24",
    )
    _ok(result)
    assert result["total"] >= 2
    assert len(result["results"]) == 1
    action = result["results"][0]
    assert action["document_code"] == "CTNF"
    assert {"102", "103", "112"} <= set(action["statutes"])
    assert 1 in action["claims"]["rejected"]

    wrapper = await odp_get_documents(app_num=OA_APP_NUMBER, document_code="CTNF")
    _ok(wrapper)
    assert action["document_id"] in {d["documentIdentifier"] for d in wrapper["results"]}


async def test_rejections_by_case_law_and_art_unit():
    result = await get_office_action_rejections(
        case_law="alice", art_unit="3689",
        date_from="2026-06-01", date_to="2026-06-30", limit=20,
    )
    _ok(result)
    assert result["total"] > 20
    assert result["metadata"]["next_offset"] == 20
    assert all("Alice" in a["case_law"] for a in result["results"])
    assert all(a["art_unit"] == "3689" for a in result["results"])


async def test_citations_by_mail_date():
    result = await get_office_action_citations(
        application_number=OA_APP_NUMBER, mail_date="2026-06-24",
    )
    _ok(result)
    sections = {r["reference"]: r.get("legal_section") for r in result["results"]}
    assert sections["ZHAO; BAO-GANG US 20130120945 A1"] == "102"
    assert any("20180292319" in ref for ref in sections)


async def test_citations_reverse_lookup():
    """The union of reference forms finds more than the parsed field alone."""
    result = await get_office_action_citations(cited_reference="US 2013/0120945 A1")
    _ok(result)
    apps = {r["app_num"] for r in result["results"]}
    assert OA_APP_NUMBER in apps
    assert len(apps) >= 3
