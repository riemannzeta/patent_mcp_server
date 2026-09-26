"""Unit tests for response truncation utilities (issue #18)."""

import pytest

from patent_mcp_server.config import config
from patent_mcp_server.util.response import (
    LEAN_STRIP_FIELDS,
    ResponseEnvelope,
    check_and_truncate,
    truncate_response,
)


def _fat_record(size_chars: int = 12_000) -> dict:
    """Build a fake ODP file-wrapper record with a large eventDataBag."""
    payload = "x" * size_chars
    return {
        "applicationNumberText": "16123456",
        "applicationMetaData": {"filingDate": "2020-01-01"},
        "eventDataBag": [{"event": payload}],
        "foreignPriorityBag": [{"country": "JP", "filing": payload[:1000]}],
    }


@pytest.mark.unit
def test_truncate_no_op_under_budget():
    """Small responses pass through unchanged."""
    response = ResponseEnvelope.success(
        results=[{"id": 1}], source="odp", offset=0, limit=10
    )
    out = truncate_response(response, max_tokens=10_000)
    assert out is response
    assert "_truncated" not in out
    assert "_lean_mode" not in out


@pytest.mark.unit
def test_truncate_respects_envelope_limit():
    """When envelope.limit is smaller than max_results, slice to limit."""
    fat_records = [_fat_record(2_000) for _ in range(20)]
    response = ResponseEnvelope.success(
        results=fat_records, source="odp", total=18_000, offset=0, limit=3
    )
    # Force truncation by setting a tiny budget.
    out = truncate_response(response, max_tokens=500, max_results=20)
    assert out["_truncated"] is True
    assert out["_truncated_to"] == 3  # min(20, envelope.limit=3)
    assert out["_original_count"] == 20
    assert out["count"] == 3
    assert len(out["results"]) == 3


@pytest.mark.unit
def test_truncate_uses_max_results_when_no_envelope_limit():
    """When envelope.limit isn't a positive int, fall back to max_results."""
    response = {
        "success": True,
        "source": "odp",
        "results": [{"id": i} for i in range(50)],
        "count": 50,
    }  # No `limit` key.
    out = truncate_response(response, max_tokens=100, max_results=5)
    assert out["_truncated"] is True
    assert out["_truncated_to"] == 5
    assert len(out["results"]) == 5


@pytest.mark.unit
def test_truncate_strips_heavy_fields_when_slice_insufficient():
    """If post-slice payload still exceeds budget, strip nested heavy fields."""
    # 3 fat records — slicing alone (limit=3) won't shrink count, so stripping
    # is required to fit a small token budget.
    fat_records = [_fat_record(50_000) for _ in range(3)]
    response = ResponseEnvelope.success(
        results=fat_records, source="odp", total=3, offset=0, limit=3
    )
    out = truncate_response(response, max_tokens=500, max_results=20)

    assert len(out["results"]) == 3  # records preserved
    assert out["_lean_mode"] is True
    assert "eventDataBag" in out["_stripped_fields"]
    for record in out["results"]:
        assert record["eventDataBag"] == {"_stripped": True}
        # Non-heavy fields preserved.
        assert "applicationNumberText" in record


@pytest.mark.unit
def test_truncate_disabled_via_config(monkeypatch):
    """check_and_truncate respects TRUNCATE_LARGE_RESPONSES=False."""
    monkeypatch.setattr(config, "TRUNCATE_LARGE_RESPONSES", False)
    fat_records = [_fat_record(50_000) for _ in range(20)]
    response = ResponseEnvelope.success(
        results=fat_records, source="odp", total=20, offset=0, limit=3
    )
    out = check_and_truncate(response)
    assert out is response
    assert "_truncated" not in out
    assert "_lean_mode" not in out


@pytest.mark.unit
def test_lean_strip_fields_includes_event_data_bag():
    """Sanity check: the configured strip list covers the issue's offenders."""
    expected = {
        "eventDataBag",
        "foreignPriorityBag",
        "assignmentBag",
        "claims",
        "descriptionBag",
    }
    assert expected.issubset(set(LEAN_STRIP_FIELDS))


@pytest.mark.unit
def test_check_and_truncate_passes_through_when_under_budget(monkeypatch):
    """Small responses are returned unchanged through check_and_truncate."""
    monkeypatch.setattr(config, "TRUNCATE_LARGE_RESPONSES", True)
    response = ResponseEnvelope.success(
        results=[{"id": 1}], source="odp", offset=0, limit=10
    )
    out = check_and_truncate(response)
    assert out is response


@pytest.mark.unit
def test_from_ptab_unwraps_proceeding_databag():
    raw = {
        "count": 2,
        "patentTrialProceedingDataBag": [
            {"trialNumber": "IPR2022-00001"},
            {"trialNumber": "IPR2022-00002"},
        ],
    }
    env = ResponseEnvelope.from_ptab(raw, offset=0, limit=25)
    assert env["success"] is True
    assert env["source"] == "ptab"
    assert env["total"] == 2
    assert len(env["results"]) == 2
    assert env["results"][0]["trialNumber"] == "IPR2022-00001"


@pytest.mark.unit
def test_from_ptab_unwraps_document_and_appeal_databags():
    for bag in ("patentTrialDocumentDataBag", "patentAppealDataBag"):
        raw = {"count": 1, bag: [{"x": 1}]}
        env = ResponseEnvelope.from_ptab(raw, 0, 25)
        assert env["success"] is True
        assert env["source"] == "ptab"
        assert env["results"] == [{"x": 1}]
        assert env["total"] == 1


# ============================================================================
# slim_document
# ============================================================================

from patent_mcp_server.constants import DocumentSections
from patent_mcp_server.util.response import slim_document


def _raw_document() -> dict:
    """A PPUBS document in miniature: text sections, biblio, empties, kwic."""
    return {
        "guid": "US-9876543-B2",
        "type": "USPAT",
        "inventionTitle": "Widget",
        "datePublished": "2018-01-23T00:00:00Z",
        "assigneeName": ["Acme"],
        "usRefGroup": ["US 7000000 B2"],
        "abstractHtml": "<p>abstract</p>",
        "claimsHtml": "1. A widget.",
        "descriptionHtml": "<p>long</p>",
        "briefHtml": "<p>brief</p>",
        "backgroundTextHtml": "",
        "applicantCity": None,
        "cpcAdditional": [],
        "continuityData": {},
        "applicationFilingDateKwicHits": [1],
        "applicationNumberHighlights": ["x"],
    }


@pytest.mark.unit
def test_slim_document_drops_empties_and_highlights():
    slim = slim_document(_raw_document())
    for gone in ("backgroundTextHtml", "applicantCity", "cpcAdditional",
                 "continuityData", "applicationFilingDateKwicHits",
                 "applicationNumberHighlights"):
        assert gone not in slim
    # Everything with content survives when no sections are named
    for kept in ("guid", "assigneeName", "usRefGroup", "abstractHtml",
                 "claimsHtml", "descriptionHtml", "briefHtml"):
        assert kept in slim
    assert "_sections" not in slim


@pytest.mark.unit
def test_slim_document_claims_only_keeps_identity():
    slim = slim_document(_raw_document(), ["claims"])
    assert slim["claimsHtml"] == "1. A widget."
    assert slim["guid"] == "US-9876543-B2"
    assert slim["inventionTitle"] == "Widget"
    for gone in ("abstractHtml", "descriptionHtml", "briefHtml",
                 "assigneeName", "usRefGroup"):
        assert gone not in slim
    assert slim["_sections"] == ["claims"]


@pytest.mark.unit
def test_slim_document_biblio_excludes_text_sections():
    slim = slim_document(_raw_document(), ["biblio"])
    assert slim["assigneeName"] == ["Acme"]
    assert slim["usRefGroup"] == ["US 7000000 B2"]
    for gone in ("abstractHtml", "claimsHtml", "descriptionHtml", "briefHtml"):
        assert gone not in slim


@pytest.mark.unit
def test_slim_document_description_covers_brief_and_background():
    raw = _raw_document()
    raw["backgroundTextHtml"] = "<p>bg</p>"
    slim = slim_document(raw, ["description"])
    assert set(slim) >= {"descriptionHtml", "briefHtml", "backgroundTextHtml"}
    assert "claimsHtml" not in slim


@pytest.mark.unit
def test_slim_document_does_not_mutate_input():
    raw = _raw_document()
    before = dict(raw)
    slim_document(raw, ["claims"])
    assert raw == before


@pytest.mark.unit
def test_slim_document_real_sample_fits_budget():
    """The checked-in US 9,876,543 document: claims + biblio fit in 8k tokens."""
    import json
    from pathlib import Path
    from patent_mcp_server.util.response import estimate_tokens

    sample = Path(__file__).resolve().parents[2] / "json" / "patent_9876543_data.json"
    if not sample.exists():
        pytest.skip("sample document not checked out")
    raw = json.loads(sample.read_text())

    full = slim_document(raw)
    assert len(full) < len(raw) // 2  # empties and kwic gone
    assert estimate_tokens(full) < estimate_tokens(raw)

    lean = slim_document(raw, ["biblio", "claims"])
    assert estimate_tokens(lean) <= config.MAX_RESPONSE_TOKENS
    assert "claimsHtml" in lean and "descriptionHtml" not in lean
    assert DocumentSections.ALL == ["biblio", "abstract", "claims", "description"]
