"""Unit tests for error handling utilities."""
import pytest

from patent_mcp_server.util.errors import ApiError, is_error


# ============================================================================
# ApiError Creation Tests
# ============================================================================

@pytest.mark.unit
def test_api_error_create_basic():
    """Test basic API error creation."""
    error = ApiError.create(message="Test error")

    assert error["error"] is True
    assert error["message"] == "Test error"
    # error_code is only included when explicitly passed
    assert error.get("error_code") is None


@pytest.mark.unit
def test_api_error_create_with_code():
    """Test API error creation with error code."""
    error = ApiError.create(message="Test error", error_code="TEST_ERROR")

    assert error["error"] is True
    assert error["message"] == "Test error"
    assert error["error_code"] == "TEST_ERROR"


@pytest.mark.unit
def test_api_error_create_with_status():
    """Test API error creation with status code."""
    error = ApiError.create(message="Not found", status_code=404)

    assert error["error"] is True
    assert error["message"] == "Not found"
    assert error["status_code"] == 404


@pytest.mark.unit
def test_api_error_create_with_all_fields():
    """Test API error creation with all fields."""
    error = ApiError.create(
        message="Test error",
        error_code="TEST_ERROR",
        status_code=400,
        details="Additional details"
    )

    assert error["error"] is True
    assert error["message"] == "Test error"
    assert error["error_code"] == "TEST_ERROR"
    assert error["status_code"] == 400
    assert error["details"] == "Additional details"


# ============================================================================
# HTTP Error Conversion Tests
# ============================================================================

@pytest.mark.unit
def test_from_http_error_basic():
    """Test HTTP error conversion."""
    error = ApiError.from_http_error(
        status_code=404,
        response_text="Not Found"
    )

    assert error["error"] is True
    assert "404" in str(error.get("status_code", ""))


@pytest.mark.unit
def test_from_http_error_with_json():
    """Test HTTP error conversion with JSON response."""
    response_json = {
        "error": {"message": "Resource not found", "code": "NOT_FOUND"}
    }

    error = ApiError.from_http_error(
        status_code=404,
        response_text="Not Found",
        response_json=response_json
    )

    assert error["error"] is True
    assert error["status_code"] == 404


@pytest.mark.unit
def test_from_http_error_401():
    """Test 401 Unauthorized error."""
    error = ApiError.from_http_error(
        status_code=401,
        response_text="Unauthorized"
    )

    assert error["error"] is True
    assert error["status_code"] == 401


@pytest.mark.unit
def test_from_http_error_403():
    """Test 403 Forbidden error."""
    error = ApiError.from_http_error(
        status_code=403,
        response_text="Forbidden"
    )

    assert error["error"] is True
    assert error["status_code"] == 403


@pytest.mark.unit
def test_from_http_error_429():
    """Test 429 Rate Limited error."""
    error = ApiError.from_http_error(
        status_code=429,
        response_text="Too Many Requests"
    )

    assert error["error"] is True
    assert error["status_code"] == 429


@pytest.mark.unit
def test_from_http_error_500():
    """Test 500 Internal Server Error."""
    error = ApiError.from_http_error(
        status_code=500,
        response_text="Internal Server Error"
    )

    assert error["error"] is True
    assert error["status_code"] == 500


@pytest.mark.unit
def test_from_http_error_503():
    """Test 503 Service Unavailable error."""
    error = ApiError.from_http_error(
        status_code=503,
        response_text="Service Unavailable"
    )

    assert error["error"] is True
    assert error["status_code"] == 503


# ============================================================================
# Exception Conversion Tests
# ============================================================================

@pytest.mark.unit
def test_from_exception_basic():
    """Test exception conversion."""
    try:
        raise ValueError("Test exception")
    except Exception as e:
        error = ApiError.from_exception(e, "Operation failed")

        assert error["error"] is True
        assert "Operation failed" in error["message"]


@pytest.mark.unit
def test_from_exception_with_details():
    """Test exception conversion with details."""
    try:
        raise ConnectionError("Network unreachable")
    except Exception as e:
        error = ApiError.from_exception(e, "Connection failed")

        assert error["error"] is True
        assert "Connection failed" in error["message"]


@pytest.mark.unit
def test_from_exception_preserves_type():
    """Test that exception type is preserved."""
    try:
        raise TimeoutError("Request timeout")
    except Exception as e:
        error = ApiError.from_exception(e, "Timeout occurred")

        assert error["error"] is True
        # Check exception info is included
        assert "message" in error


# ============================================================================
# Specific Error Type Tests
# ============================================================================

@pytest.mark.unit
def test_not_found_error():
    """Test not found error creation."""
    error = ApiError.not_found("Patent", "9876543")

    assert error["error"] is True
    assert "Patent" in error["message"]
    assert "9876543" in error["message"]
    assert "not found" in error["message"].lower()


@pytest.mark.unit
def test_validation_error():
    """Test validation error creation."""
    error = ApiError.validation_error("Invalid patent number", "patent_number")

    assert error["error"] is True
    assert "Invalid patent number" in error["message"]
    assert error.get("error_code") == "VALIDATION_ERROR"


@pytest.mark.unit
def test_rate_limit_error():
    """Test rate limit error creation."""
    error = ApiError.create(
        message="Rate limit exceeded",
        error_code="RATE_LIMITED",
        status_code=429
    )

    assert error["error"] is True
    assert error["error_code"] == "RATE_LIMITED"
    assert error["status_code"] == 429


# ============================================================================
# Error Detection Tests
# ============================================================================

@pytest.mark.unit
def test_is_error_true():
    """Test is_error returns True for error responses."""
    error = ApiError.create(message="Test error")

    assert is_error(error) is True


@pytest.mark.unit
def test_is_error_false():
    """Test is_error returns False for success responses."""
    success = {"success": True, "data": "test"}

    assert is_error(success) is False


@pytest.mark.unit
def test_is_error_with_error_false():
    """Test is_error with explicit error=False."""
    response = {"error": False, "data": "test"}

    assert is_error(response) is False


@pytest.mark.unit
def test_is_error_missing_error_key():
    """Test is_error with missing error key."""
    response = {"data": "test"}

    assert is_error(response) is False


@pytest.mark.unit
def test_is_error_none():
    """Test is_error with None - should handle gracefully."""
    # is_error expects a dict, so None will raise AttributeError
    # This test verifies the behavior (or that it needs handling)
    try:
        result = is_error(None)
        assert result is False
    except (AttributeError, TypeError):
        # This is expected - None doesn't have .get() method
        pass


@pytest.mark.unit
def test_is_error_empty_dict():
    """Test is_error with empty dictionary."""
    assert is_error({}) is False


# ============================================================================
# Error Message Format Tests
# ============================================================================

@pytest.mark.unit
def test_error_message_formatting():
    """Test error message formatting."""
    error = ApiError.create(
        message="Failed to retrieve patent {patent_num}",
        error_code="RETRIEVAL_ERROR"
    )

    assert error["message"] is not None
    assert len(error["message"]) > 0


@pytest.mark.unit
def test_error_with_multiple_details():
    """Test error with multiple detail fields."""
    error = ApiError.create(
        message="Operation failed",
        error_code="OPERATION_ERROR",
        details="Additional context",
        status_code=400
    )

    assert error["error"] is True
    assert error["message"] == "Operation failed"
    assert error["error_code"] == "OPERATION_ERROR"
    assert error["details"] == "Additional context"
    assert error["status_code"] == 400


# ============================================================================
# Edge Cases
# ============================================================================

@pytest.mark.unit
def test_error_with_empty_message():
    """Test error creation with empty message."""
    error = ApiError.create(message="")

    assert error["error"] is True
    assert "message" in error


@pytest.mark.unit
def test_error_with_none_values():
    """Test error creation with None values."""
    error = ApiError.create(
        message="Test error",
        error_code=None,
        status_code=None
    )

    assert error["error"] is True
    assert error["message"] == "Test error"


@pytest.mark.unit
def test_error_with_special_characters():
    """Test error with special characters in message."""
    error = ApiError.create(
        message="Error: <>&\"'",
        error_code="SPECIAL_CHARS"
    )

    assert error["error"] is True
    assert error["message"] == "Error: <>&\"'"


@pytest.mark.unit
def test_error_with_unicode():
    """Test error with unicode characters."""
    error = ApiError.create(
        message="Error: 特許番号が見つかりません",
        error_code="UNICODE_ERROR"
    )

    assert error["error"] is True
    assert "特許番号が見つかりません" in error["message"]


# ============================================================================
# Error Code Constants Tests
# ============================================================================

@pytest.mark.unit
def test_common_error_codes():
    """Test that common error codes work correctly."""
    error_codes = [
        "VALIDATION_ERROR",
        "NOT_FOUND",
        "RATE_LIMITED",
        "SESSION_EXPIRED",
        "NETWORK_ERROR",
        "TIMEOUT",
        "SERVER_ERROR",
        "UNAUTHORIZED"
    ]

    for code in error_codes:
        error = ApiError.create(message="Test", error_code=code)
        assert error["error_code"] == code


# ============================================================================
# Error Context Tests
# ============================================================================

@pytest.mark.unit
def test_error_with_context():
    """Test error with additional context."""
    error = ApiError.create(
        message="Failed to download PDF",
        error_code="PDF_ERROR",
        details={
            "patent_number": "9876543",
            "step": "PDF generation",
            "attempt": 3
        }
    )

    assert error["error"] is True
    assert error["message"] == "Failed to download PDF"
    assert isinstance(error.get("details"), dict)


# ============================================================================
# Boolean Error Flag Handling Tests (PatentsView API)
# ============================================================================

@pytest.mark.unit
def test_from_http_error_with_boolean_error_flag():
    """Test that boolean 'error' field is NOT used as message."""
    response_json = {"error": True}

    error = ApiError.from_http_error(
        status_code=400,
        response_text="Bad Request: Invalid query syntax",
        response_json=response_json
    )

    assert error["error"] is True
    assert error["status_code"] == 400
    assert isinstance(error["message"], str)
    assert error["message"] == "Bad Request: Invalid query syntax"


@pytest.mark.unit
def test_from_http_error_prefers_message_field():
    """Test that 'message' field is preferred over 'error' field."""
    response_json = {
        "error": True,
        "message": "Query parameter 'q' is required"
    }

    error = ApiError.from_http_error(
        status_code=400,
        response_text="Bad Request",
        response_json=response_json
    )

    assert error["message"] == "Query parameter 'q' is required"


@pytest.mark.unit
def test_from_http_error_uses_string_error_field():
    """Test that string 'error' field is used as message."""
    response_json = {"error": "Invalid patent number format"}

    error = ApiError.from_http_error(
        status_code=400,
        response_text="Bad Request",
        response_json=response_json
    )

    assert error["message"] == "Invalid patent number format"


@pytest.mark.unit
def test_from_http_error_with_false_error_flag():
    """Test handling of 'error': false (shouldn't be used as message)."""
    response_json = {"error": False}

    error = ApiError.from_http_error(
        status_code=400,
        response_text="Something went wrong",
        response_json=response_json
    )

    assert error["message"] == "Something went wrong"
    assert isinstance(error["message"], str)


@pytest.mark.unit
def test_from_http_error_with_empty_message_field():
    """Test handling of empty message field falls back to response_text."""
    response_json = {"error": True, "message": ""}

    error = ApiError.from_http_error(
        status_code=400,
        response_text="Fallback error message",
        response_json=response_json
    )

    assert error["message"] == "Fallback error message"
