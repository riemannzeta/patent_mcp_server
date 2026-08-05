"""Unit tests for PpubsClient."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock, Mock
import httpx
from datetime import datetime, timedelta
import json
import asyncio

from patent_mcp_server.uspto.ppubs_uspto_gov import PpubsClient
from patent_mcp_server.constants import Sources, Fields, PrintStatus
from test.fixtures.ppubs_responses import (
    MOCK_SESSION_RESPONSE,
    MOCK_COUNTS_RESPONSE,
    MOCK_SEARCH_RESPONSE,
    MOCK_DOCUMENT_RESPONSE,
    MOCK_PDF_REQUEST_RESPONSE,
    MOCK_PDF_STATUS_COMPLETED,
    MOCK_PDF_CONTENT,
    MOCK_ERROR_SESSION_EXPIRED,
    MOCK_ERROR_RATE_LIMITED
)


@pytest.fixture
async def ppubs_client():
    """Create a PpubsClient instance for testing."""
    client = PpubsClient()
    yield client
    await client.close()


@pytest.fixture
def mock_session_data():
    """Mock session data."""
    return MOCK_SESSION_RESPONSE


# ============================================================================
# Initialization Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_client_initialization():
    """Test client initialization."""
    client = PpubsClient()

    # Check initial state
    assert client.case_id is None
    assert client.access_token is None
    assert client.session_expires_at is None
    assert client.session == {}
    assert client.client is not None

    await client.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_client_context_manager():
    """Test client context manager protocol."""
    async with PpubsClient() as client:
        assert client is not None
        assert client.client is not None

    # Client should be closed after context


# ============================================================================
# Session Management Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_session_creation_success(ppubs_client, mock_session_data):
    """Test successful session creation."""
    # Mock the HTTP responses
    with patch.object(ppubs_client.client, 'get', new_callable=AsyncMock) as mock_get:
        with patch.object(ppubs_client.client, 'post', new_callable=AsyncMock) as mock_post:
            # Mock GET request for initial page
            mock_get.return_value = MagicMock(status_code=200)

            # Mock POST request for session creation
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_session_data
            mock_response.headers = {"X-Access-Token": "test-token-123"}
            mock_response.text = json.dumps(mock_session_data)
            mock_post.return_value = mock_response

            # Call get_session
            session = await ppubs_client.get_session()

            # Assertions
            assert session is not None
            assert ppubs_client.case_id == "test-case-123456"
            assert ppubs_client.access_token == "test-token-123"
            assert ppubs_client.session_expires_at is not None
            assert isinstance(ppubs_client.session_expires_at, datetime)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_session_caching(ppubs_client, mock_session_data):
    """Test session caching functionality."""
    # Set up cached session
    ppubs_client.session = mock_session_data
    ppubs_client.case_id = "test-case-123456"
    ppubs_client.session_expires_at = datetime.now() + timedelta(minutes=30)

    # Should return cached session without making HTTP request
    with patch.object(ppubs_client.client, 'get', new_callable=AsyncMock) as mock_get:
        with patch.object(ppubs_client.client, 'post', new_callable=AsyncMock) as mock_post:
            session = await ppubs_client.get_session()

            # Should not have called HTTP methods
            mock_get.assert_not_called()
            mock_post.assert_not_called()

            assert session == mock_session_data
            assert ppubs_client.case_id == "test-case-123456"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_session_expiration_refresh(ppubs_client, mock_session_data):
    """Test session refresh after expiration."""
    # Set up expired session
    ppubs_client.session = mock_session_data
    ppubs_client.session_expires_at = datetime.now() - timedelta(minutes=1)

    # Mock the HTTP responses for refresh
    with patch.object(ppubs_client.client, 'get', new_callable=AsyncMock) as mock_get:
        with patch.object(ppubs_client.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_get.return_value = MagicMock(status_code=200)

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_session_data
            mock_response.headers = {"X-Access-Token": "new-token-456"}
            mock_response.text = json.dumps(mock_session_data)
            mock_post.return_value = mock_response

            # Should refresh session
            session = await ppubs_client.get_session()

            # Should have called HTTP methods to refresh
            mock_get.assert_called_once()
            mock_post.assert_called_once()

            assert ppubs_client.access_token == "new-token-456"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_session_creation_failure(ppubs_client):
    """Test handling of session creation failure."""
    # Mock failed session creation
    with patch.object(ppubs_client.client, 'get', new_callable=AsyncMock) as mock_get:
        with patch.object(ppubs_client.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_get.return_value = MagicMock(status_code=200)

            # Mock POST returns error
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_post.return_value = mock_response

            session = await ppubs_client.get_session()

            assert session is None


# ============================================================================
# HTTP Request Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_make_request_success(ppubs_client):
    """Test successful HTTP request."""
    with patch.object(ppubs_client.client, 'request', new_callable=AsyncMock) as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        mock_response.text = '{"result": "success"}'
        mock_request.return_value = mock_response

        response = await ppubs_client.make_request("GET", "http://test.com")

        assert response.status_code == 200
        mock_request.assert_called_once_with("GET", "http://test.com")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_make_request_session_expired_refresh(ppubs_client, mock_session_data):
    """Test automatic session refresh on 403 error."""
    with patch.object(ppubs_client.client, 'request', new_callable=AsyncMock) as mock_request:
        with patch.object(ppubs_client, '_refresh_session', new_callable=AsyncMock) as mock_refresh:
            # First response: 403 (session expired)
            expired_response = MagicMock()
            expired_response.status_code = 403

            # Second response: success after refresh
            success_response = MagicMock()
            success_response.status_code = 200
            success_response.json.return_value = {"result": "success"}
            success_response.text = '{"result": "success"}'

            mock_request.side_effect = [expired_response, success_response]
            mock_refresh.return_value = mock_session_data

            response = await ppubs_client.make_request("GET", "http://test.com")

            # Should have refreshed session, passing the token that was rejected
            # so a concurrent refresh isn't duplicated
            mock_refresh.assert_called_once_with(stale_token=None)

            # Should have retried request
            assert mock_request.call_count == 2
            assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.asyncio
async def test_make_request_rate_limit_handling(ppubs_client):
    """Test rate limit (429) response handling."""
    with patch.object(ppubs_client.client, 'request', new_callable=AsyncMock) as mock_request:
        # First response: rate limited
        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {"x-rate-limit-retry-after-seconds": "1"}

        # Second response: success
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {"result": "success"}
        success_response.text = '{"result": "success"}'

        mock_request.side_effect = [rate_limit_response, success_response]

        # Mock sleep to speed up test
        with patch('asyncio.sleep', new_callable=AsyncMock):
            response = await ppubs_client.make_request("GET", "http://test.com")

        assert response.status_code == 200
        assert mock_request.call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_make_request_network_error_retry(ppubs_client):
    """Test network error retry logic."""
    with patch.object(ppubs_client.client, 'request', new_callable=AsyncMock) as mock_request:
        # First attempt: network error
        # Second attempt: success
        mock_request.side_effect = [
            httpx.NetworkError("Connection failed"),
            MagicMock(status_code=200, text='{"result": "success"}')
        ]

        # Should retry and succeed
        response = await ppubs_client.make_request("GET", "http://test.com")

        assert response.status_code == 200
        assert mock_request.call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_make_request_timeout_error_retry(ppubs_client):
    """Test timeout error retry logic."""
    with patch.object(ppubs_client.client, 'request', new_callable=AsyncMock) as mock_request:
        # First attempt: timeout
        # Second attempt: success
        mock_request.side_effect = [
            httpx.TimeoutException("Request timeout"),
            MagicMock(status_code=200, text='{"result": "success"}')
        ]

        response = await ppubs_client.make_request("GET", "http://test.com")

        assert response.status_code == 200
        assert mock_request.call_count == 2


# ============================================================================
# Search Query Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_query_success(ppubs_client, mock_session_data):
    """Test successful search query execution."""
    # Set up session
    ppubs_client.case_id = "test-case-123456"
    ppubs_client.session_expires_at = datetime.now() + timedelta(minutes=30)

    with patch.object(ppubs_client, 'make_request', new_callable=AsyncMock) as mock_request:
        # Mock counts response
        counts_response = MagicMock()
        counts_response.status_code = 200
        counts_response.get.return_value = False  # No error

        # Mock search response
        search_response = MagicMock()
        search_response.status_code = 200
        search_response.json.return_value = MOCK_SEARCH_RESPONSE
        search_response.get.return_value = False  # No error

        mock_request.side_effect = [counts_response, search_response]

        result = await ppubs_client.run_query(
            query='patentNumber:"9876543"',
            sources=[Sources.GRANTED_PATENTS]
        )

        assert result is not None
        assert result.get("numFound") == 1
        assert len(result.get("docs", [])) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_query_creates_session_if_missing(ppubs_client, mock_session_data):
    """Test that run_query creates session if not exists."""
    assert ppubs_client.case_id is None

    async def mock_get_session_impl():
        """Mock get_session that sets case_id as a side effect."""
        ppubs_client.case_id = "test-case-123456"
        return mock_session_data

    with patch.object(ppubs_client, 'get_session', side_effect=mock_get_session_impl) as mock_get_session:
        with patch.object(ppubs_client, 'make_request', new_callable=AsyncMock) as mock_request:
            # Mock responses
            mock_request.side_effect = [
                MagicMock(status_code=200, get=lambda x, y: False),
                MagicMock(status_code=200, json=lambda: MOCK_SEARCH_RESPONSE, get=lambda x, y: False)
            ]

            await ppubs_client.run_query(query="test")

            # Should have created session
            mock_get_session.assert_called_once()


# ============================================================================
# Document Retrieval Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_document_success(ppubs_client, mock_session_data):
    """Test successful document retrieval."""
    ppubs_client.case_id = "test-case-123456"
    ppubs_client.session_expires_at = datetime.now() + timedelta(minutes=30)

    with patch.object(ppubs_client, 'make_request', new_callable=AsyncMock) as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = MOCK_DOCUMENT_RESPONSE
        mock_response.get.return_value = False

        mock_request.return_value = mock_response

        result = await ppubs_client.get_document("US-9876543-B2", "USPAT")

        assert result is not None
        assert result.get("guid") == "US-9876543-B2"
        assert "sections" in result


# ============================================================================
# PDF Download Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_save_success(ppubs_client):
    """Test PDF save request."""
    ppubs_client.case_id = "test-case-123456"

    with patch.object(ppubs_client.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = MOCK_PDF_REQUEST_RESPONSE
        mock_post.return_value = mock_response

        print_job_id = await ppubs_client._request_save(
            "US-9876543-B2",
            "US/09/876/543",
            10,
            "USPAT"
        )

        assert print_job_id == MOCK_PDF_REQUEST_RESPONSE
        mock_post.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_image_success(ppubs_client):
    """Test PDF download."""
    ppubs_client.case_id = "test-case-123456"

    with patch.object(ppubs_client, '_request_save', new_callable=AsyncMock) as mock_request_save:
        with patch.object(ppubs_client.client, 'post', new_callable=AsyncMock) as mock_post:
            with patch.object(ppubs_client.client, 'build_request') as mock_build:
                with patch.object(ppubs_client.client, 'send', new_callable=AsyncMock) as mock_send:
                    # Mock print job ID
                    mock_request_save.return_value = MOCK_PDF_REQUEST_RESPONSE

                    # Mock status check (completed immediately)
                    status_response = MagicMock()
                    status_response.status_code = 200
                    status_response.json.return_value = MOCK_PDF_STATUS_COMPLETED
                    mock_post.return_value = status_response

                    # Mock PDF download
                    import base64
                    pdf_bytes = base64.b64decode(MOCK_PDF_CONTENT)

                    pdf_response = MagicMock()
                    pdf_response.status_code = 200
                    pdf_response.aread = AsyncMock(return_value=pdf_bytes)
                    mock_send.return_value = pdf_response

                    mock_build.return_value = MagicMock()

                    result = await ppubs_client.download_image(
                        "US-9876543-B2",
                        "US/09/876/543",
                        10,
                        "USPAT"
                    )

                    assert result.get("success") is True
                    assert "content" in result
                    assert result["content_type"] == "application/pdf"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_image_uses_current_save_endpoint(ppubs_client):
    """Regression: USPTO moved the PDF download endpoint. The old
    /api/internal/print/save/{pdfName} path returns 404 ("No static
    resource"); the live endpoint is /api/print/save/{pdfName}
    (verified live 2026-08-05)."""
    ppubs_client.case_id = "test-case-123456"

    with patch.object(ppubs_client, '_request_save', new_callable=AsyncMock) as mock_request_save:
        with patch.object(ppubs_client.client, 'post', new_callable=AsyncMock) as mock_post:
            with patch.object(ppubs_client.client, 'build_request') as mock_build:
                with patch.object(ppubs_client.client, 'send', new_callable=AsyncMock) as mock_send:
                    mock_request_save.return_value = MOCK_PDF_REQUEST_RESPONSE

                    status_response = MagicMock()
                    status_response.status_code = 200
                    status_response.json.return_value = MOCK_PDF_STATUS_COMPLETED
                    mock_post.return_value = status_response

                    pdf_response = MagicMock()
                    pdf_response.status_code = 200
                    pdf_response.aread = AsyncMock(return_value=b"%PDF-fake")
                    mock_send.return_value = pdf_response
                    mock_build.return_value = MagicMock()

                    await ppubs_client.download_image(
                        "US-9876543-B2", "US/09/876/543", 10, "USPAT"
                    )

                    download_url = mock_build.call_args[0][1]
                    pdf_name = MOCK_PDF_STATUS_COMPLETED[0]["pdfName"]
                    assert download_url.endswith(f"/api/print/save/{pdf_name}")
                    assert "/api/internal/" not in download_url


# ============================================================================
# Resource Cleanup Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_close():
    """Test client cleanup."""
    client = PpubsClient()

    with patch.object(client.client, 'aclose', new_callable=AsyncMock) as mock_close:
        await client.close()
        mock_close.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_context_manager_cleanup():
    """Test context manager cleanup."""
    mock_close_called = False

    async with PpubsClient() as client:
        with patch.object(client.client, 'aclose', new_callable=AsyncMock) as mock_close:
            pass

    # Context manager should trigger cleanup


# ============================================================================
# Issue #21: query operator + template isolation
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_query_defaults_to_AND_operator(ppubs_client):
    """Default operator is AND so multi-word queries don't OR-fan-out
    into the latest-grants fallback (issue #21)."""
    ppubs_client.case_id = "case-1"
    ppubs_client.session_expires_at = datetime.now() + timedelta(minutes=30)

    posted_bodies = []

    async def capture_request(method, url, **kwargs):
        posted_bodies.append(kwargs.get("json"))
        resp = MagicMock(status_code=200)
        resp.json.return_value = MOCK_SEARCH_RESPONSE
        resp.get.return_value = False
        return resp

    with patch.object(ppubs_client, "make_request", side_effect=capture_request):
        await ppubs_client.run_query(query="machine learning")

    # First call posts the inner query (counts endpoint); second posts the wrapper.
    counts_body, search_body = posted_bodies
    assert counts_body["op"] == "AND"
    assert search_body["query"]["op"] == "AND"
    assert counts_body["q"] == "machine learning"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_query_does_not_mutate_template(ppubs_client):
    """Two sequential calls with different queries must not see each other's
    state — the template was previously shared via shallow copy (issue #21)."""
    ppubs_client.case_id = "case-1"
    ppubs_client.session_expires_at = datetime.now() + timedelta(minutes=30)

    template_q_before = ppubs_client.search_query["query"]["q"]

    async def fake_request(method, url, **kwargs):
        resp = MagicMock(status_code=200)
        resp.json.return_value = MOCK_SEARCH_RESPONSE
        resp.get.return_value = False
        return resp

    with patch.object(ppubs_client, "make_request", side_effect=fake_request):
        await ppubs_client.run_query(query="first query")
        await ppubs_client.run_query(query="second query")

    # Template must still hold its original q after both calls.
    assert ppubs_client.search_query["query"]["q"] == template_q_before


@pytest.mark.unit
async def test_ppubs_download_patent_pdf_tool_passes_full_signature():
    """Regression: the tool must call download_image with all four arguments
    (guid, image_location, page_count, document_type) — it previously passed
    only (guid, type), raising TypeError at runtime."""
    from patent_mcp_server import patents

    patent_doc = MOCK_SEARCH_RESPONSE["docs"][0]
    search_result = {"success": True, "patent": patent_doc}

    with patch("patent_mcp_server.patents._search_patent_by_number",
               new_callable=AsyncMock, return_value=search_result), \
         patch.object(patents.ppubs_client, "download_image",
                      new_callable=AsyncMock) as dl:
        dl.return_value = {"success": True, "filename": "x.pdf",
                           "content_type": "application/pdf", "content": ""}
        result = await patents.ppubs_download_patent_pdf("9876543")

    assert result["success"] is True
    dl.assert_awaited_once_with(
        patent_doc["guid"],
        patent_doc["imageLocation"],
        patent_doc["pageCount"],
        patent_doc["type"],
    )


# ============================================================================
# Session Concurrency Tests
# ============================================================================

def _session_post_mock(mock_session_data):
    """A POST mock that answers session-creation requests."""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = mock_session_data
    response.headers = {"X-Access-Token": "test-token-123"}
    response.text = json.dumps(mock_session_data)
    return response


@pytest.mark.unit
@pytest.mark.asyncio
async def test_concurrent_get_session_establishes_once(ppubs_client, mock_session_data):
    """Parallel callers share one session instead of each creating their own.

    Without the lock every concurrent tool call resets the cookie jar and
    races to swap the access token, so the requests that are already in
    flight end up signed with a half-replaced session.
    """
    async def slow_get(*args, **kwargs):
        # A real suspension point, so the other callers get a chance to run
        # mid-establishment. Without it the mocks never yield and the
        # coroutines run one after another, which would hide the race.
        await asyncio.sleep(0.01)
        return MagicMock(status_code=200)

    async def slow_post(*args, **kwargs):
        await asyncio.sleep(0.01)
        return _session_post_mock(mock_session_data)

    with patch.object(ppubs_client.client, 'get', side_effect=slow_get):
        with patch.object(ppubs_client.client, 'post', side_effect=slow_post) as mock_post:
            results = await asyncio.gather(*(ppubs_client.get_session() for _ in range(5)))

            # One establishment, and everyone got the same session back.
            assert mock_post.call_count == 1
            assert all(r == mock_session_data for r in results)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_refresh_skipped_when_another_caller_already_refreshed(
    ppubs_client, mock_session_data
):
    """A 403 does not discard a session that someone else just replaced."""
    ppubs_client.session = mock_session_data
    ppubs_client.access_token = "current-token"

    with patch.object(ppubs_client.client, 'post', new_callable=AsyncMock) as mock_post:
        # The caller's request was signed with a token that has since been
        # superseded, so there is nothing left to refresh.
        result = await ppubs_client._refresh_session(stale_token="already-replaced")

        mock_post.assert_not_called()
        assert result == mock_session_data
        assert ppubs_client.access_token == "current-token"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_refresh_proceeds_when_token_is_still_current(ppubs_client, mock_session_data):
    """A 403 on the newest token does establish a replacement session."""
    ppubs_client.access_token = "stale-token"

    with patch.object(ppubs_client.client, 'get', new_callable=AsyncMock) as mock_get:
        with patch.object(ppubs_client.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_get.return_value = MagicMock(status_code=200)
            mock_post.return_value = _session_post_mock(mock_session_data)

            await ppubs_client._refresh_session(stale_token="stale-token")

            assert ppubs_client.access_token == "test-token-123"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_token_is_sent_per_request(ppubs_client):
    """The session token rides on each request, not on the shared client.

    Keeping it off the client's default headers means a refresh cannot
    change the credentials of a request that has already been built.
    """
    ppubs_client.access_token = "test-token-123"

    with patch.object(ppubs_client.client, 'request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = MagicMock(status_code=200, text="{}")

        await ppubs_client.make_request("GET", "http://test.com")

        sent = mock_request.call_args.kwargs["headers"]
        assert sent["X-Access-Token"] == "test-token-123"
        assert "X-Access-Token" not in ppubs_client.client.headers


@pytest.mark.unit
@pytest.mark.asyncio
async def test_caller_supplied_token_is_preserved(ppubs_client):
    """An explicit token wins, so session creation can send its placeholder."""
    ppubs_client.access_token = "test-token-123"

    with patch.object(ppubs_client.client, 'request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = MagicMock(status_code=200, text="{}")

        await ppubs_client.make_request(
            "POST", "http://test.com", headers={"X-Access-Token": "null"}
        )

        assert mock_request.call_args.kwargs["headers"]["X-Access-Token"] == "null"
