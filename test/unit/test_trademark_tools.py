"""Unit tests for the trademark MCP tools in patents.py."""
import base64
import pytest
from unittest.mock import AsyncMock, patch

from patent_mcp_server import patents

from test.fixtures.tsdr_responses import (
    MOCK_TSDR_STATUS_RESPONSE,
    MOCK_TSDR_PDF_CONTENT,
)


# ============================================================================
# TSDR Tools
# ============================================================================

@pytest.mark.unit
async def test_tsdr_get_trademark_status_by_serial():
    with patch.object(patents.tsdr_client, "get_case_status",
                      new_callable=AsyncMock) as m:
        m.return_value = MOCK_TSDR_STATUS_RESPONSE
        result = await patents.tsdr_get_trademark_status(serial_number="78787878")

    assert result["success"] is True
    assert result["source"] == "tsdr"
    assert result["results"]["status"]["markElement"] == "TESTMARK"
    m.assert_awaited_once_with(serial_number="78787878", registration_number=None)


@pytest.mark.unit
async def test_tsdr_get_trademark_status_cleans_serial():
    """Serial numbers with separators are cleaned before the API call."""
    with patch.object(patents.tsdr_client, "get_case_status",
                      new_callable=AsyncMock) as m:
        m.return_value = MOCK_TSDR_STATUS_RESPONSE
        await patents.tsdr_get_trademark_status(serial_number="78/787,878")

    m.assert_awaited_once_with(serial_number="78787878", registration_number=None)


@pytest.mark.unit
async def test_tsdr_get_trademark_status_invalid_serial():
    """A serial number that isn't 8 digits is rejected before any request."""
    result = await patents.tsdr_get_trademark_status(serial_number="123")

    assert result["error"] is True
    assert result["error_code"] == "VALIDATION_ERROR"


@pytest.mark.unit
async def test_tsdr_get_trademark_status_by_registration():
    with patch.object(patents.tsdr_client, "get_case_status",
                      new_callable=AsyncMock) as m:
        m.return_value = MOCK_TSDR_STATUS_RESPONSE
        result = await patents.tsdr_get_trademark_status(registration_number="3500027")

    assert result["success"] is True
    m.assert_awaited_once_with(serial_number=None, registration_number="3500027")


@pytest.mark.unit
async def test_tsdr_download_trademark_documents():
    """Binary responses pass through without envelope/truncation."""
    payload = {
        "success": True,
        "filename": "tm-78787878-documents.pdf",
        "content_type": "application/pdf",
        "content": MOCK_TSDR_PDF_CONTENT,
        "size_bytes": 60,
    }
    with patch.object(patents.tsdr_client, "download_case_documents",
                      new_callable=AsyncMock) as m:
        m.return_value = payload
        result = await patents.tsdr_download_trademark_documents("78787878")

    assert result == payload
    assert base64.b64decode(result["content"]).startswith(b"%PDF")


@pytest.mark.unit
async def test_tsdr_get_trademark_image_invalid_serial():
    result = await patents.tsdr_get_trademark_image("not-a-number")

    assert result["error"] is True
    assert result["error_code"] == "VALIDATION_ERROR"


# ============================================================================
# Trademark Search Tools
# ============================================================================

@pytest.mark.unit
async def test_tm_search_trademarks_requires_filter():
    result = await patents.tm_search_trademarks()

    assert result["error"] is True
    assert result["error_code"] == "MISSING_FILTER"


@pytest.mark.unit
async def test_tm_search_trademarks_normalizes_envelope():
    with patch.object(patents.tmsearch_client, "search",
                      new_callable=AsyncMock) as m:
        m.return_value = {
            "results": [{"id": "78787878", "wordmark": "TESTMARK"}],
            "total": 42,
        }
        result = await patents.tm_search_trademarks(mark_text="TESTMARK", limit=25)

    assert result["success"] is True
    assert result["source"] == "tmsearch"
    assert result["total"] == 42
    assert result["count"] == 1
    assert result["has_more"] is True


@pytest.mark.unit
async def test_tm_search_trademarks_propagates_error():
    with patch.object(patents.tmsearch_client, "search",
                      new_callable=AsyncMock) as m:
        m.return_value = {"error": True, "message": "down", "status_code": 503}
        result = await patents.tm_search_trademarks(mark_text="TESTMARK")

    assert result["error"] is True


@pytest.mark.unit
async def test_tm_get_trademark_not_found():
    with patch.object(patents.tmsearch_client, "get_by_serial",
                      new_callable=AsyncMock) as m:
        m.return_value = {"results": [], "total": 0}
        result = await patents.tm_get_trademark("78787878")

    assert result["error"] is True
    assert result["error_code"] == "NOT_FOUND"


@pytest.mark.unit
async def test_tm_get_trademark_found():
    with patch.object(patents.tmsearch_client, "get_by_serial",
                      new_callable=AsyncMock) as m:
        m.return_value = {
            "results": [{"id": "78787878", "wordmark": "TESTMARK"}],
            "total": 1,
        }
        result = await patents.tm_get_trademark("78787878")

    assert result["success"] is True
    assert result["results"][0]["wordmark"] == "TESTMARK"


@pytest.mark.unit
async def test_tm_search_assignments_requires_filter():
    result = await patents.tm_search_assignments()

    assert result["error"] is True
    assert result["error_code"] == "MISSING_FILTER"


@pytest.mark.unit
async def test_tm_search_assignments_reports_backend():
    with patch.object(patents.tm_assignment_client, "search_assignments",
                      new_callable=AsyncMock) as m:
        m.return_value = {
            "results": [{"reelNumber": "1234"}],
            "total": 1,
            "backend": "odp",
        }
        result = await patents.tm_search_assignments(registration_number="3500027")

    assert result["success"] is True
    assert result["source"] == "tm_assignments"
    assert result["metadata"]["backend"] == "odp"


# ============================================================================
# Reference Lookup Tools
# ============================================================================

@pytest.mark.unit
async def test_get_trademark_class_info_goods():
    result = await patents.get_trademark_class_info("9")

    assert result["class"] == "9"
    assert result["type"] == "goods"
    assert "software" in result["description"].lower()


@pytest.mark.unit
async def test_get_trademark_class_info_services():
    result = await patents.get_trademark_class_info("42")

    assert result["type"] == "services"


@pytest.mark.unit
async def test_get_trademark_class_info_accepts_leading_zero():
    result = await patents.get_trademark_class_info("09")

    assert result["class"] == "9"


@pytest.mark.unit
async def test_get_trademark_class_info_unknown():
    result = await patents.get_trademark_class_info("99")

    assert "error" in result


@pytest.mark.unit
async def test_get_trademark_status_code_known():
    result = await patents.get_trademark_status_code("700")

    assert result["code"] == "700"
    assert result["description"] == "Registered"
    assert result["stage"] == "registered"


@pytest.mark.unit
async def test_get_trademark_status_code_unknown():
    result = await patents.get_trademark_status_code("12345")

    assert "error" in result


# ============================================================================
# check_api_status Coverage
# ============================================================================

@pytest.mark.unit
async def test_check_api_status_includes_trademark_sources():
    result = await patents.check_api_status()

    sources = result["sources"]
    for key in ("tsdr", "tmsearch", "tm_assignments", "ttab"):
        assert key in sources

    assert sources["tmsearch"]["requires_auth"] is False
    assert sources["ttab"]["status"] == "NOT_AVAILABLE_AS_API"
