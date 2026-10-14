"""Unit tests for odp_search_office_actions and odp_search_petition_decisions.

Both tools POST a Lucene `q` to ODP record endpoints (verified live
2026-10-14). These tests mock api_client.make_request and check the
request body each tool builds and the slimmed results it returns.
"""

import copy
from unittest.mock import AsyncMock, patch

import pytest

from patent_mcp_server.patents import (
    odp_search_office_actions,
    odp_search_petition_decisions,
)
from patent_mcp_server.util.response import strip_highlights
from patent_mcp_server.util.validation import lucene_quote
from test.fixtures.odp_office_action_responses import (
    APPLICATION_LOOKUP_RESPONSE,
    OFFICE_ACTION_SEARCH_RESPONSE,
)
from test.fixtures.odp_petition_responses import PETITION_SEARCH_RESPONSE

MAKE_REQUEST = "patent_mcp_server.patents.api_client.make_request"
NOT_FOUND = {"error": True, "message": "Not Found", "status_code": 404}


def _mock(*responses):
    return AsyncMock(side_effect=[copy.deepcopy(r) for r in responses])


def _body(mock, call=-1):
    return mock.call_args_list[call].kwargs["data"]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_lucene_quote_escapes_quotes_and_backslashes():
    assert lucene_quote('say "hi"') == '"say \\"hi\\""'
    assert lucene_quote("a\\b") == '"a\\\\b"'


@pytest.mark.unit
def test_strip_highlights_marks_terms():
    text = (
        "based on <b><span style='background-color: yellow;'>unintentional"
        "</span></b> <b><span style='background-color: yellow;'>delay</span></b>"
    )
    assert strip_highlights(text) == "based on «unintentional» «delay»"
    assert strip_highlights(None) is None


# ---------------------------------------------------------------------------
# odp_search_office_actions
# ---------------------------------------------------------------------------

@pytest.mark.unit
async def test_office_actions_requires_a_filter():
    with patch(MAKE_REQUEST, new=AsyncMock()) as mock:
        result = await odp_search_office_actions()
    assert result["error_code"] == "MISSING_FILTER"
    mock.assert_not_called()


@pytest.mark.unit
async def test_office_actions_request_shape():
    mock = _mock(OFFICE_ACTION_SEARCH_RESPONSE)
    with patch(MAKE_REQUEST, new=mock):
        await odp_search_office_actions(
            query='officeActionText:"printed matter"',
            document_code="ctnf, CTFR",
            art_unit="1798",
            date_from="2026-01-01",
            sort="oldest",
            offset=10,
            limit=5,
        )

    assert mock.call_args.kwargs["method"] == "POST"
    assert mock.call_args.args[0].endswith("/api/v1/patent/office-action/search")
    body = _body(mock)
    assert body["q"] == (
        '(officeActionText:"printed matter") AND '
        'documentCode:("CTNF" OR "CTFR") AND '
        'groupArtUnitNumber:"1798" AND '
        "submissionDate:[2026-01-01 TO *]"
    )
    assert body["facets"] == ["documentCode", "rejectionTypeBag"]
    assert body["sort"] == [{"field": "submissionDate", "order": "asc"}]
    assert body["pagination"] == {"offset": 10, "limit": 5}


@pytest.mark.unit
async def test_office_actions_escape_quotes_in_values():
    mock = _mock(OFFICE_ACTION_SEARCH_RESPONSE)
    with patch(MAKE_REQUEST, new=mock):
        await odp_search_office_actions(art_unit='17" OR *:*')
    assert _body(mock)["q"] == 'groupArtUnitNumber:"17\\" OR *:*"'


@pytest.mark.unit
async def test_office_actions_rejection_types_are_anded():
    mock = _mock(OFFICE_ACTION_SEARCH_RESPONSE)
    with patch(MAKE_REQUEST, new=mock):
        await odp_search_office_actions(rejection_type="101, doublepatent")
    assert _body(mock)["q"] == (
        'rejectionTypeBag:"101" AND rejectionTypeBag:"DoublePatent"'
    )


@pytest.mark.unit
async def test_office_actions_reject_unknown_rejection_type():
    with patch(MAKE_REQUEST, new=AsyncMock()) as mock:
        result = await odp_search_office_actions(rejection_type="102,104")
    assert result["error_code"] == "VALIDATION_ERROR"
    assert "104" in result["message"]
    mock.assert_not_called()


@pytest.mark.unit
@pytest.mark.parametrize("kwargs", [
    {"date_from": "2026-1-1"},
    {"date_to": "2026-01-01] OR *:*"},
    {"sort": "relevance", "app_num": "18402543"},
    {"offset": -1, "app_num": "18402543"},
    {"app_num": "not-a-number"},
])
async def test_office_actions_validation_errors(kwargs):
    with patch(MAKE_REQUEST, new=AsyncMock()) as mock:
        result = await odp_search_office_actions(**kwargs)
    assert result["error_code"] == "VALIDATION_ERROR"
    mock.assert_not_called()


@pytest.mark.unit
async def test_office_actions_clamp_limit_to_100():
    mock = _mock(OFFICE_ACTION_SEARCH_RESPONSE)
    with patch(MAKE_REQUEST, new=mock):
        result = await odp_search_office_actions(app_num="18402543", limit=500)
    assert _body(mock)["pagination"]["limit"] == 100
    assert result["limit"] == 100
    assert result["metadata"]["limit_clamped_from"] == 500


@pytest.mark.unit
async def test_office_actions_slim_results_and_facets():
    mock = _mock(OFFICE_ACTION_SEARCH_RESPONSE)
    with patch(MAKE_REQUEST, new=mock):
        result = await odp_search_office_actions(app_num="18402543", limit=25)

    assert result["success"] is True
    assert result["total"] == 2
    assert result["has_more"] is False
    first = result["results"][0]
    assert first == {
        "record_id": "87f5a4cced36a7ab5ffef6d3f818b5db",
        "app_num": "18402543",
        "document_code": "CTFR",
        "description": "Final Rejections",
        "submission_date": "2026-10-09",
        "filing_date": "2024-01-02",
        "art_unit": "1798",
        "title": "HOUSING FOR A SENSOR AND SENSOR",
        "rejection_types": ["102", "103", "Other"],
        "document_id": "MUZJAZYBX54X145",
        "text_preview": first["text_preview"],
    }
    assert first["text_preview"].startswith("DETAILED ACTION")
    assert result["metadata"]["facets"] == {
        "documentCode": {"CTFR": 1, "CTNF": 1},
        "rejectionTypeBag": {"102": 2, "103": 2, "Other": 2, "112": 1},
    }
    assert "limit_clamped_from" not in result["metadata"]


@pytest.mark.unit
async def test_office_actions_404_is_an_empty_page():
    mock = _mock(NOT_FOUND)
    with patch(MAKE_REQUEST, new=mock):
        result = await odp_search_office_actions(app_num="99999999")
    assert result["success"] is True
    assert result["results"] == []
    assert result["total"] == 0


@pytest.mark.unit
async def test_office_actions_auth_error_carries_profile_hint():
    mock = _mock({"error": True, "message": "Unauthorized", "status_code": 401})
    with patch(MAKE_REQUEST, new=mock):
        result = await odp_search_office_actions(app_num="18402543")
    assert result["error"] is True
    assert "profile" in result["hint"]


@pytest.mark.unit
async def test_office_actions_resolve_patent_number():
    mock = _mock(APPLICATION_LOOKUP_RESPONSE, OFFICE_ACTION_SEARCH_RESPONSE)
    with patch(MAKE_REQUEST, new=mock):
        result = await odp_search_office_actions(patent_number="US 8,462,371 B2")

    lookup = _body(mock, 0)
    assert mock.call_args_list[0].args[0].endswith("/api/v1/patent/applications/search")
    assert lookup["q"] == 'applicationMetaData.patentNumber:"8462371"'
    assert _body(mock, 1)["q"] == 'applicationNumberText:"12344137"'
    assert result["success"] is True


@pytest.mark.unit
@pytest.mark.parametrize("lookup", [
    {"count": 0, "patentFileWrapperDataBag": []},
    NOT_FOUND,
])
async def test_office_actions_unknown_patent_number(lookup):
    mock = _mock(lookup)
    with patch(MAKE_REQUEST, new=mock):
        result = await odp_search_office_actions(patent_number="1234567")
    assert result["error_code"] == "NOT_FOUND"
    assert mock.call_count == 1


# ---------------------------------------------------------------------------
# odp_search_petition_decisions
# ---------------------------------------------------------------------------

@pytest.mark.unit
async def test_petitions_requires_a_filter():
    with patch(MAKE_REQUEST, new=AsyncMock()) as mock:
        result = await odp_search_petition_decisions()
    assert result["error_code"] == "MISSING_FILTER"
    mock.assert_not_called()


@pytest.mark.unit
async def test_petitions_request_shape():
    mock = _mock(PETITION_SEARCH_RESPONSE)
    with patch(MAKE_REQUEST, new=mock):
        await odp_search_petition_decisions(
            petition_type="533",
            outcome="granted in part",
            deciding_office="Office of Petitions",
            technology_center="2600",
            date_from="2020-01-01",
            date_to="2026-12-31",
            final_only=True,
            patent_number="8462371",
        )

    assert mock.call_args.args[0].endswith("/api/v1/petition/decisions/search")
    body = _body(mock)
    assert body["q"] == (
        'patentNumber:"8462371" AND '
        'decisionPetitionTypeCode:"533" AND '
        'decidedPetitionTypeCode:"B" AND '
        'finalDecidingOfficeName:"Office of Petitions" AND '
        'technologyCenter:"2600" AND '
        "decisionDate:[2020-01-01 TO 2026-12-31] AND "
        "finalPetitionDecisionIndicator:true"
    )
    assert body["sort"] == [{"field": "decisionDate", "order": "desc"}]
    assert set(body["facets"]) == {
        "decidedPetitionTypeCodeDescriptionText",
        "finalDecidingOfficeName",
        "decisionPetitionTypeCode",
    }


@pytest.mark.unit
async def test_petitions_type_words_search_the_description():
    mock = _mock(PETITION_SEARCH_RESPONSE)
    with patch(MAKE_REQUEST, new=mock):
        await odp_search_petition_decisions(petition_type="revive")
    assert _body(mock)["q"] == 'decisionPetitionTypeCodeDescriptionText:"revive"'


@pytest.mark.unit
async def test_petitions_reject_unknown_outcome():
    with patch(MAKE_REQUEST, new=AsyncMock()) as mock:
        result = await odp_search_petition_decisions(outcome="approved")
    assert result["error_code"] == "VALIDATION_ERROR"
    mock.assert_not_called()


@pytest.mark.unit
async def test_petitions_slim_results():
    mock = _mock(PETITION_SEARCH_RESPONSE)
    with patch(MAKE_REQUEST, new=mock):
        result = await odp_search_petition_decisions(petition_type="533")

    assert result["total"] == 2817
    hit = result["results"][0]
    assert hit["record_id"] == "764ea781-7319-5ad7-a9b9-4e115544556e"
    assert hit["patent_number"] == "8462371"
    assert hit["outcome"] == "DISMISSED"
    assert hit["final_decision"] is False
    assert hit["deciding_office"] == "OFFICE OF PETITIONS"
    assert "<span" not in hit["text"]
    assert "«unintentional» «delay»" in hit["text"]
    assert "allSearchableFields" not in hit
    assert "full_text" not in hit
    doc = hit["documents"][0]
    assert doc["documentIdentifier"] == "MUWPOE8HX247X37"
    assert doc["formats"] == ["PDF", "MS_WORD"]
    assert "downloadOptionBag" not in doc
    assert result["metadata"]["facets"]["decidedPetitionTypeCodeDescriptionText"] == {
        "DISMISSED": 1713, "GRANTED": 1103, "DENIED": 1,
    }


@pytest.mark.unit
async def test_petitions_include_full_text():
    mock = _mock(PETITION_SEARCH_RESPONSE)
    with patch(MAKE_REQUEST, new=mock):
        result = await odp_search_petition_decisions(
            petition_type="533", include_full_text=True
        )
    assert result["results"][0]["full_text"].startswith("12344137")


@pytest.mark.unit
async def test_petitions_404_is_an_empty_page():
    mock = _mock(NOT_FOUND)
    with patch(MAKE_REQUEST, new=mock):
        result = await odp_search_petition_decisions(app_num="99999999")
    assert result["success"] is True
    assert result["results"] == []
