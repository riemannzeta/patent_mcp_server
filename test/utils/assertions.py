"""Custom assertions for patent MCP server tests."""
from typing import Any, Dict, List, Optional


def assert_has_keys(data: dict, keys: List[str], message: Optional[str] = None) -> None:
    """Assert that dictionary has all specified keys.

    Args:
        data: Dictionary to check
        keys: List of required keys
        message: Optional custom error message

    Raises:
        AssertionError: If any key is missing
    """
    missing_keys = [k for k in keys if k not in data]
    if missing_keys:
        error_msg = message or f"Missing keys: {missing_keys}"
        raise AssertionError(error_msg)


def assert_has_structure(data: dict, structure: dict) -> None:
    """Assert that dictionary matches expected structure.

    Args:
        data: Dictionary to validate
        structure: Expected structure with key: type pairs

    Raises:
        AssertionError: If structure doesn't match

    Example:
        assert_has_structure(
            {"name": "test", "count": 5},
            {"name": str, "count": int}
        )
    """
    for key, expected_type in structure.items():
        assert key in data, f"Missing key: {key}"
        assert isinstance(data[key], expected_type), \
            f"Key '{key}' has type {type(data[key])}, expected {expected_type}"


def assert_patent_structure(patent: dict) -> None:
    """Assert that patent data has expected structure.

    Args:
        patent: Patent dictionary to validate

    Raises:
        AssertionError: If structure is invalid
    """
    required_keys = ["guid", "patentNumber", "type"]
    assert_has_keys(patent, required_keys, "Invalid patent structure")


def assert_application_structure(application: dict) -> None:
    """Assert that application data has expected structure.

    Args:
        application: Application dictionary to validate

    Raises:
        AssertionError: If structure is invalid
    """
    required_keys = ["applicationNumberText"]
    assert_has_keys(application, required_keys, "Invalid application structure")


def assert_search_response(response: dict, min_results: int = 0) -> None:
    """Assert that search response is valid.

    Args:
        response: Search response to validate
        min_results: Minimum number of expected results

    Raises:
        AssertionError: If response is invalid
    """
    assert not response.get("error", False), f"Error in response: {response.get('message')}"

    # Check for result count
    count_key = "numFound" if "numFound" in response else "total"
    assert count_key in response, "Response missing result count"

    if min_results > 0:
        assert response[count_key] >= min_results, \
            f"Expected at least {min_results} results, got {response[count_key]}"


def assert_error_response(response: dict, expected_code: Optional[str] = None) -> None:
    """Assert that response is an error response.

    Args:
        response: Response to validate
        expected_code: Optional expected error code

    Raises:
        AssertionError: If response is not an error or wrong error code
    """
    assert response.get("error") is True, "Response is not an error"
    assert "message" in response, "Error response missing message"

    if expected_code:
        assert response.get("error_code") == expected_code, \
            f"Expected error code {expected_code}, got {response.get('error_code')}"


def assert_valid_guid(guid: str) -> None:
    """Assert that string is a valid patent GUID.

    Args:
        guid: GUID string to validate

    Raises:
        AssertionError: If GUID is invalid

    Example:
        assert_valid_guid("US-9876543-B2")
    """
    assert isinstance(guid, str), "GUID must be a string"
    assert len(guid) > 0, "GUID cannot be empty"
    # Basic format check (e.g., "US-9876543-B2")
    parts = guid.split("-")
    assert len(parts) >= 2, f"Invalid GUID format: {guid}"


def assert_valid_patent_number(patent_number: str) -> None:
    """Assert that string is a valid patent number.

    Args:
        patent_number: Patent number to validate

    Raises:
        AssertionError: If patent number is invalid
    """
    assert isinstance(patent_number, str), "Patent number must be a string"
    assert len(patent_number) >= 4, "Patent number too short"
    assert patent_number.isdigit(), "Patent number must be numeric"


def assert_valid_app_number(app_number: str) -> None:
    """Assert that string is a valid application number.

    Args:
        app_number: Application number to validate

    Raises:
        AssertionError: If application number is invalid
    """
    assert isinstance(app_number, str), "Application number must be a string"
    assert len(app_number) >= 4, "Application number too short"
    # Remove common separators for validation
    clean_num = app_number.replace("/", "").replace(",", "")
    assert clean_num.isdigit(), "Application number must be numeric (after removing separators)"


def assert_session_structure(session: dict) -> None:
    """Assert that session data has expected structure.

    Args:
        session: Session dictionary to validate

    Raises:
        AssertionError: If structure is invalid
    """
    assert "userCase" in session, "Session missing 'userCase'"
    assert "caseId" in session["userCase"], "Session missing 'caseId'"


def assert_pdf_content(content: str) -> None:
    """Assert that content is valid base64-encoded PDF.

    Args:
        content: Base64-encoded PDF content

    Raises:
        AssertionError: If content is invalid
    """
    import base64

    assert isinstance(content, str), "PDF content must be a string"
    assert len(content) > 0, "PDF content cannot be empty"

    # Try to decode base64
    try:
        pdf_bytes = base64.b64decode(content)
    except Exception as e:
        raise AssertionError(f"Failed to decode base64 content: {e}")

    # Check PDF header
    assert pdf_bytes.startswith(b"%PDF"), "Content does not start with PDF header"


def assert_list_not_empty(data: list, message: Optional[str] = None) -> None:
    """Assert that list is not empty.

    Args:
        data: List to check
        message: Optional custom error message

    Raises:
        AssertionError: If list is empty
    """
    error_msg = message or "List is empty"
    assert len(data) > 0, error_msg


def assert_all_items_have_key(items: List[dict], key: str) -> None:
    """Assert that all items in list have specified key.

    Args:
        items: List of dictionaries
        key: Required key

    Raises:
        AssertionError: If any item is missing the key
    """
    for i, item in enumerate(items):
        assert key in item, f"Item {i} missing key '{key}'"
