"""Integration tests for trademark tools (real API calls).

Skipped by default; run with: uv run pytest -m integration -k trademark

Requirements:
  - Network access to uspto.gov hosts
  - TSDR_API_KEY in .env for the TSDR tests. NOTE: TSDR requires its own
    key from account.uspto.gov/profile/api-manager ("TSDR API" product);
    an ODP key passes the gateway but every request 404s.

tmsearch and Assignment Center contracts were verified live on 2026-06-10
and need no API key. If the tmsearch tests start failing with 403/202, AWS
WAF has been tightened — set TMSEARCH_WAF_TOKEN from a browser cookie.
"""
import base64
import os
import pytest

from patent_mcp_server import patents

# Long-registered, stable marks for lookups
KNOWN_SERIAL = "74612654"          # NIKE (word mark), registered 1996, live
KNOWN_WORDMARK = "NIKE"


# Keyed off the env var directly, NOT config.TSDR_API_KEY: the config falls
# back to USPTO_API_KEY, but an ODP key cannot reach the TSDR backend (every
# request 404s), so the fallback would make these tests fail, not run.
requires_tsdr_key = pytest.mark.skipif(
    not os.getenv("TSDR_API_KEY"),
    reason="TSDR_API_KEY not configured (TSDR-specific key required; "
           "the ODP key does not work for TSDR)",
)


@pytest.mark.integration
@requires_tsdr_key
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
@requires_tsdr_key
async def test_tsdr_list_documents_live():
    """TSDR lists prosecution document metadata (XML-only endpoint)."""
    result = await patents.tsdr_list_trademark_documents(KNOWN_SERIAL)

    assert result.get("error") is not True, result
    assert result["success"] is True
    assert result["total"] > 0
    assert result["results"][0].get("DocumentTypeCode"), result["results"][0]


@pytest.mark.integration
@pytest.mark.slow
@requires_tsdr_key
async def test_tsdr_document_bundle_live():
    """A filtered TSDR document bundle downloads and decodes to a PDF.

    Filtered by document type because NIKE's full wrapper is ~13 MB —
    over the MAX_BINARY_BYTES guard and a needless 4-req/min PDF spend.
    ACR (Notice-Acceptance-Renewal) is a single-page document.
    """
    result = await patents.tsdr_download_trademark_documents(
        KNOWN_SERIAL, document_type="ACR"
    )

    assert result.get("error") is not True, result
    assert result["content_type"].startswith("application/pdf")
    assert base64.b64decode(result["content"]).startswith(b"%PDF")


@pytest.mark.integration
async def test_tm_search_trademarks_live():
    """tmsearch returns hits for a famous live mark."""
    result = await patents.tm_search_trademarks(
        mark_text=KNOWN_WORDMARK, status_filter="live", limit=5
    )

    assert result.get("error") is not True, result
    assert result["total"] > 0
    assert len(result["results"]) > 0


@pytest.mark.integration
async def test_tm_search_trademarks_class_filter_live():
    """The international class filter narrows results (zero-padded term)."""
    result = await patents.tm_search_trademarks(
        owner_name="Nike", international_class="25", status_filter="live",
        limit=5,
    )

    assert result.get("error") is not True, result
    assert result["total"] > 0


@pytest.mark.integration
async def test_tm_get_trademark_live():
    """Single-record lookup by serial number hits the live index."""
    result = await patents.tm_get_trademark(KNOWN_SERIAL)

    assert result.get("error") is not True, result
    assert result["results"][0]["wordmark"] == KNOWN_WORDMARK


@pytest.mark.integration
async def test_tm_search_assignments_live():
    """Assignment Center answers without an API key."""
    result = await patents.tm_search_assignments(
        assignee_name="Nike, Inc.", limit=5
    )

    assert result.get("error") is not True, result
    assert result["metadata"]["backend"] == "assignment-center"
    assert len(result["results"]) > 0
