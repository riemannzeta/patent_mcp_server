"""Unit tests for odp_get_documents filters and odp_download_document."""

from unittest.mock import AsyncMock, patch

import pytest

from patent_mcp_server import patents
from patent_mcp_server.patents import odp_download_document, odp_get_documents
from test.fixtures.api_responses import MOCK_DOCUMENTS_RESPONSE


async def _listing(**kwargs):
    """Call odp_get_documents against the fixture; returns (mock, result)."""
    with patch.object(patents.api_client, "make_request", new_callable=AsyncMock,
                      return_value=MOCK_DOCUMENTS_RESPONSE) as make_request:
        result = await odp_get_documents("16123456", **kwargs)
    return make_request, result


@pytest.mark.unit
async def test_documents_listing_shape():
    make_request, result = await _listing()

    make_request.assert_awaited_once()
    assert make_request.call_args.args[0].endswith("/applications/16123456/documents")
    assert result["success"] is True
    assert result["total"] == 5 and result["count"] == 5
    first = result["results"][0]
    assert first["documentIdentifier"] == "KGC5TXULLDFLYX9"
    assert first["documentCode"] == "NOA"
    assert first["pageTotalQuantity"] == 2
    assert first["formats"] == ["PDF"]
    assert "downloadOptionBag" not in first
    ctnf = result["results"][2]
    assert ctnf["formats"] == ["PDF", "MS_WORD", "XML"]
    assert ctnf["pageTotalQuantity"] == 9


@pytest.mark.unit
async def test_documents_metadata_counts_codes():
    _, result = await _listing()
    meta = result["metadata"]
    assert meta["application_number"] == "16123456"
    assert meta["documents_in_wrapper"] == 5
    assert meta["code_counts"] == {"892": 1, "CTNF": 1, "NOA": 1, "REM": 1, "SPEC": 1}


@pytest.mark.unit
async def test_documents_filter_by_code_is_case_insensitive():
    _, result = await _listing(document_code="ctnf, noa")
    assert [d["documentCode"] for d in result["results"]] == ["NOA", "CTNF"]
    assert result["total"] == 2
    # Counts still describe the whole wrapper
    assert result["metadata"]["documents_in_wrapper"] == 5


@pytest.mark.unit
async def test_documents_filter_by_direction():
    _, result = await _listing(direction="incoming")
    assert [d["documentCode"] for d in result["results"]] == ["REM", "SPEC"]


@pytest.mark.unit
async def test_documents_offset_and_limit():
    _, result = await _listing(offset=1, limit=2)
    assert [d["documentCode"] for d in result["results"]] == ["REM", "CTNF"]
    assert result["total"] == 5
    assert result["count"] == 2
    assert result["offset"] == 1


@pytest.mark.unit
async def test_documents_passes_through_api_error():
    with patch.object(patents.api_client, "make_request", new_callable=AsyncMock,
                      return_value={"error": True, "message": "403", "status_code": 403}):
        result = await odp_get_documents("16123456")
    assert result["error"] is True


@pytest.mark.unit
async def test_documents_rejects_bad_app_number():
    with patch.object(patents.api_client, "make_request", new_callable=AsyncMock) as make_request:
        result = await odp_get_documents("12")
    assert result["error"] is True
    make_request.assert_not_awaited()


@pytest.mark.unit
async def test_download_document_builds_url_and_labels_result():
    payload = {"success": True, "content_type": "application/octet-stream",
               "size_bytes": 3, "content": "JVBE"}
    with patch.object(patents.api_client, "download_file", new_callable=AsyncMock,
                      return_value=payload) as download:
        result = await odp_download_document("16/123,456", " k87ak41frxeapx5 ")

    download.assert_awaited_once_with(
        "https://api.uspto.gov/api/v1/download/applications/16123456/K87AK41FRXEAPX5.pdf"
    )
    assert result["success"] is True
    assert result["filename"] == "16123456-K87AK41FRXEAPX5.pdf"
    assert result["document_id"] == "K87AK41FRXEAPX5"
    assert result["application_number"] == "16123456"


@pytest.mark.unit
async def test_download_document_rejects_bad_id():
    with patch.object(patents.api_client, "download_file", new_callable=AsyncMock) as download:
        result = await odp_download_document("16123456", "../etc/passwd")
    assert result["error"] is True
    download.assert_not_awaited()


@pytest.mark.unit
async def test_download_document_passes_through_error():
    with patch.object(patents.api_client, "download_file", new_callable=AsyncMock,
                      return_value={"error": True, "error_code": "RESPONSE_TOO_LARGE",
                                    "message": "big"}):
        result = await odp_download_document("16123456", "K87AK41FRXEAPX5")
    assert result["error_code"] == "RESPONSE_TOO_LARGE"
    assert "filename" not in result
