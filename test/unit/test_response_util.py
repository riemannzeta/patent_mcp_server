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
