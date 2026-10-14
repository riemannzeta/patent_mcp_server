"""
Integration tests for ODP Office Action Search and Petition Decisions.

These call api.uspto.gov and need USPTO_API_KEY, so they are deselected
by default (pytest.ini). Records named here were verified live on
2026-10-14; a failure means the live contract moved.

Run with: uv run pytest -m integration test/test_odp_oa_petitions_integration.py
"""

import pytest

from patent_mcp_server.patents import (
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
