"""Integration tests for trademark tools (real API calls).

Skipped by default; run with: uv run pytest -m integration -k trademark

Requirements:
  - Network access to uspto.gov hosts
  - TSDR_API_KEY or USPTO_API_KEY in .env for TSDR and assignment tests

These tests double as live-contract verification for the two backends that
could not be probed during development:
  - tmsearch.uspto.gov (undocumented internal API — see tmsearch_client.py)
  - trademark assignment search (ODP migration target vs legacy XML API)
If the tmsearch tests fail with 400/404, inspect the web app's network
calls and adjust SEARCH_PATH / TmSearchFields / build_search_body.
"""
import base64
import pytest

from patent_mcp_server import patents
from patent_mcp_server.config import config

# Long-registered, stable marks for lookups
KNOWN_SERIAL = "78787878"          # TSDR's own documentation example


requires_key = pytest.mark.skipif(
    not config.TSDR_API_KEY,
    reason="TSDR_API_KEY / USPTO_API_KEY not configured",
)


@pytest.mark.integration
@requires_key
async def test_tsdr_status_by_serial_live():
    """TSDR returns a status record for a known serial number."""
    result = await patents.tsdr_get_trademark_status(serial_number=KNOWN_SERIAL)

    assert result.get("error") is not True, result
    assert result["success"] is True
    assert result["source"] == "tsdr"
    # The record should carry a status block with a serial number
    record = result["results"]
    assert record, "empty TSDR record"


@pytest.mark.integration
@pytest.mark.slow
@requires_key
async def test_tsdr_document_bundle_live():
    """TSDR document bundle downloads and decodes to a PDF."""
    result = await patents.tsdr_download_trademark_documents(KNOWN_SERIAL)

    assert result.get("error") is not True, result
    assert result["content_type"].startswith("application/pdf")
    assert base64.b64decode(result["content"]).startswith(b"%PDF")


@pytest.mark.integration
async def test_tm_search_trademarks_live():
    """tmsearch returns hits for a famous live mark (validates the probed
    request body against the real internal API)."""
    result = await patents.tm_search_trademarks(
        mark_text="NIKE", status_filter="live", limit=5
    )

    assert result.get("error") is not True, result
    assert result["total"] > 0
    assert len(result["results"]) > 0


@pytest.mark.integration
@requires_key
async def test_tm_search_assignments_live():
    """Assignment search answers from one of the two backends."""
    result = await patents.tm_search_assignments(
        assignee_name="Nike", limit=5
    )

    assert result.get("error") is not True, result
    assert result["metadata"]["backend"] in ("odp", "legacy")
