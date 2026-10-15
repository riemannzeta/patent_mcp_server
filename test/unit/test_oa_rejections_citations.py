"""Unit tests for get_office_action_rejections and get_office_action_citations.

Both tools send a Solr `criteria` string to the ODP rejection and citation
datasets (verified live 2026-10-15). These tests mock
office_action_client.search_records and check the criteria each tool
builds and the results it returns.
"""

import copy
from unittest.mock import AsyncMock, patch

import pytest

from patent_mcp_server.patents import (
    _oa_reference_clause,
    get_office_action_citations,
    get_office_action_rejections,
)
from patent_mcp_server.util.response import (
    group_rejection_rows, parse_claim_numbers, slim_oa_citation,
)
from test.fixtures.odp_oa_dataset_responses import (
    CITATION_RECORDS_RESPONSE,
    REJECTION_RECORDS_RESPONSE,
)
from test.fixtures.odp_office_action_responses import APPLICATION_LOOKUP_RESPONSE

SEARCH = "patent_mcp_server.patents.office_action_client.search_records"
MAKE_REQUEST = "patent_mcp_server.patents.api_client.make_request"

REJECTION_ROWS = REJECTION_RECORDS_RESPONSE["response"]["docs"]
CITATION_ROWS = CITATION_RECORDS_RESPONSE["response"]["docs"]


def _page(rows, total=None):
    rows = copy.deepcopy(rows)
    return {"total": len(rows) if total is None else total, "docs": rows}


def _criteria(mock, call=-1):
    return mock.call_args_list[call].args[1]


# ---------------------------------------------------------------------------
# Row helpers
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_parse_claim_numbers_sorts_numerically():
    assert parse_claim_numbers(["1,10,2,3"]) == [1, 2, 3, 10]
    assert parse_claim_numbers(["1,2", "2,5"]) == [1, 2, 5]
    assert parse_claim_numbers("3, 1a") == [3, "1a"]
    assert parse_claim_numbers(None) == []


@pytest.mark.unit
def test_group_rejection_rows_one_entry_per_action():
    actions = group_rejection_rows(copy.deepcopy(REJECTION_ROWS))
    assert len(actions) == 1
    action = actions[0]
    assert action["document_id"] == "MQQL87V0173X211"
    assert action["document_code"] == "CTNF"
    assert action["mail_date"] == "2026-06-24"
    assert action["art_unit"] == "1798"
    assert action["statutes"] == ["102", "103", "112"]
    assert "case_law" not in action
    assert action["claims"] == {"rejected": list(range(1, 11))}
    # The repeated first row does not add a group.
    assert len(action["claim_groups"]) == 11
    assert {"action": "rejected", "legal_section": "103", "claims": [9, 10]} in action["claim_groups"]


@pytest.mark.unit
def test_group_rejection_rows_case_law_and_double_patenting():
    row = dict(REJECTION_ROWS[0], aliceIndicator=True, mayoIndicator=True,
               hasRej101=1, hasRejDP=1, obsoleteDocumentIdentifier="OTHER")
    actions = group_rejection_rows([copy.deepcopy(REJECTION_ROWS[0]), row])
    assert [a["document_id"] for a in actions] == ["MQQL87V0173X211", "OTHER"]
    assert actions[1]["case_law"] == ["Alice", "Mayo"]
    assert actions[1]["statutes"] == ["101", "102", "103", "112", "DP"]


@pytest.mark.unit
def test_slim_oa_citation():
    slim = slim_oa_citation(copy.deepcopy(CITATION_ROWS[1]))
    assert slim["reference"] == "Battrell; C. Frederick US 20180292319 A1"
    assert slim["reference_number"] == "20180292319"
    assert slim["legal_section"] == "103"
    assert slim["document_id"] == "MQQL87V0173X211"
    assert slim["examiner_cited"] is True
    assert "createUserIdentifier" not in slim
    # A blank parsedReferenceIdentifier is dropped, not passed on as "".
    assert "reference_number" not in slim_oa_citation(copy.deepcopy(CITATION_ROWS[0]))


@pytest.mark.unit
@pytest.mark.parametrize("given", [
    "US 2013/0120945 A1", "20130120945", "US20130120945A1", "2013-0120945",
])
def test_reference_clause_for_publication(given):
    assert _oa_reference_clause(given) == (
        '(parsedReferenceIdentifier:"20130120945" OR '
        'referenceIdentifier:20130120945 OR referenceIdentifier:"2013/0120945")'
    )


@pytest.mark.unit
@pytest.mark.parametrize("given", ["6,750,970", "US 6750970 B2", "6750970"])
def test_reference_clause_for_patent(given):
    assert _oa_reference_clause(given) == (
        '(parsedReferenceIdentifier:"6750970" OR '
        'referenceIdentifier:6750970 OR referenceIdentifier:"6,750,970")'
    )


@pytest.mark.unit
def test_reference_clause_for_design_patent_searches_text():
    assert _oa_reference_clause("D912345") == 'referenceIdentifier:"D912345"'


# ---------------------------------------------------------------------------
# get_office_action_rejections
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.asyncio
async def test_rejections_by_application():
    mock = AsyncMock(return_value=_page(REJECTION_ROWS, total=12))
    with patch(SEARCH, mock):
        result = await get_office_action_rejections(application_number="18/402,543")

    assert mock.call_args.args[0] == "oa_rejections"
    assert _criteria(mock) == 'patentApplicationNumber:"18402543"'
    assert mock.call_args.args[2:] == (0, 50)
    assert result["success"] is True
    assert result["total"] == 12
    assert result["count"] == 1
    assert result["has_more"] is False
    assert result["results"][0]["statutes"] == ["102", "103", "112"]
    assert result["metadata"]["rows_returned"] == 12


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rejections_filters_build_criteria():
    mock = AsyncMock(return_value=_page([]))
    with patch(SEARCH, mock):
        await get_office_action_rejections(
            statute="101, §103", case_law="Alice", document_code="ctnf,ctfr",
            art_unit="3689", date_from="2026-06-01", date_to="2026-06-30",
        )
    assert _criteria(mock) == (
        "submissionDate:[2026-06-01T00:00:00 TO 2026-06-30T23:59:59]"
        " AND hasRej101:1 AND hasRej103:1 AND aliceIndicator:true"
        ' AND legacyDocumentCodeIdentifier:("CTNF" OR "CTFR")'
        ' AND groupArtUnitNumber:"3689"'
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rejections_mail_date_is_one_day():
    mock = AsyncMock(return_value=_page([]))
    with patch(SEARCH, mock):
        await get_office_action_rejections(application_number="18402543", mail_date="2026-06-24")
    assert _criteria(mock) == (
        'patentApplicationNumber:"18402543" AND '
        "submissionDate:[2026-06-24T00:00:00 TO 2026-06-24T23:59:59]"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rejections_pages_by_rows():
    rows = copy.deepcopy(REJECTION_ROWS[:5])
    mock = AsyncMock(return_value={"total": 280, "docs": rows})
    with patch(SEARCH, mock):
        result = await get_office_action_rejections(case_law="alice", offset=20, limit=5000)
    assert mock.call_args.args[2:] == (20, 200)
    assert result["has_more"] is True
    assert result["metadata"]["next_offset"] == 25
    assert result["metadata"]["limit_clamped_from"] == 5000


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rejections_by_patent_number_resolves_application():
    lookup = AsyncMock(return_value=copy.deepcopy(APPLICATION_LOOKUP_RESPONSE))
    mock = AsyncMock(return_value=_page([]))
    app_num = APPLICATION_LOOKUP_RESPONSE["patentFileWrapperDataBag"][0]["applicationNumberText"]
    with patch(MAKE_REQUEST, lookup), patch(SEARCH, mock):
        await get_office_action_rejections(patent_number="US 9,999,999 B2")
    assert _criteria(mock) == f'patentApplicationNumber:"{app_num}"'


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("kwargs,field", [
    ({"statute": "105"}, "statute"),
    ({"case_law": "chakrabarty"}, "case_law"),
])
async def test_rejections_unknown_filter_values(kwargs, field):
    mock = AsyncMock()
    with patch(SEARCH, mock):
        result = await get_office_action_rejections(**kwargs)
    assert result["error_code"] == "VALIDATION_ERROR"
    assert result["details"]["field"] == field
    mock.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rejections_need_a_filter():
    mock = AsyncMock()
    with patch(SEARCH, mock):
        result = await get_office_action_rejections()
    assert result["error_code"] == "MISSING_FILTER"
    mock.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rejections_bad_date():
    with patch(SEARCH, AsyncMock()) as mock:
        result = await get_office_action_rejections(date_from="June 2026")
    assert result["error_code"] == "VALIDATION_ERROR"
    mock.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rejections_auth_error_gets_profile_hint():
    denied = {"error": True, "message": "Forbidden", "status_code": 403}
    with patch(SEARCH, AsyncMock(return_value=denied)):
        result = await get_office_action_rejections(application_number="18402543")
    assert result["error"] is True
    assert "data.uspto.gov" in result["hint"]


# ---------------------------------------------------------------------------
# get_office_action_citations
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.asyncio
async def test_citations_by_application():
    mock = AsyncMock(return_value=_page(CITATION_ROWS))
    with patch(SEARCH, mock):
        result = await get_office_action_citations(application_number="18402543")
    assert mock.call_args.args[0] == "oa_citations"
    assert _criteria(mock) == 'patentApplicationNumber:"18402543"'
    assert result["total"] == 2
    assert [r["legal_section"] for r in result["results"]] == ["102", "103"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_citations_mail_date_finds_actions_first():
    """Citation rows carry no date, so the rejection rows supply the ids."""
    mock = AsyncMock(side_effect=[_page(REJECTION_ROWS), _page(CITATION_ROWS)])
    with patch(SEARCH, mock):
        result = await get_office_action_citations(
            application_number="18402543", mail_date="2026-06-24",
        )
    assert mock.call_args_list[0].args[0] == "oa_rejections"
    assert "submissionDate:[2026-06-24T00:00:00 TO 2026-06-24T23:59:59]" in _criteria(mock, 0)
    assert mock.call_args_list[1].args[0] == "oa_citations"
    assert _criteria(mock, 1) == (
        'patentApplicationNumber:"18402543" AND '
        'obsoleteDocumentIdentifier:("MQQL87V0173X211")'
    )
    assert result["count"] == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_citations_mail_date_without_action():
    mock = AsyncMock(return_value=_page([]))
    with patch(SEARCH, mock):
        result = await get_office_action_citations(
            application_number="18402543", mail_date="2026-01-02",
        )
    assert mock.await_count == 1
    assert result["success"] is True
    assert result["results"] == []
    assert "2026-01-02" in result["metadata"]["note"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_citations_mail_date_needs_application():
    with patch(SEARCH, AsyncMock()) as mock:
        result = await get_office_action_citations(mail_date="2026-06-24")
    assert result["error_code"] == "VALIDATION_ERROR"
    mock.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_citations_reverse_lookup_filters():
    mock = AsyncMock(return_value=_page([]))
    with patch(SEARCH, mock):
        await get_office_action_citations(
            cited_reference="US 6,750,970 B2", legal_section="103",
            examiner_cited=True, tech_center="3600",
        )
    assert _criteria(mock) == (
        '(parsedReferenceIdentifier:"6750970" OR referenceIdentifier:6750970'
        ' OR referenceIdentifier:"6,750,970")'
        ' AND legalSectionCode:("103")'
        " AND examinerCitedReferenceIndicator:true"
        ' AND techCenter:"3600"'
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_citations_need_a_filter():
    with patch(SEARCH, AsyncMock()) as mock:
        result = await get_office_action_citations()
    assert result["error_code"] == "MISSING_FILTER"
    mock.assert_not_called()
