"""Test helper utilities."""
import json
import asyncio
from pathlib import Path
from typing import Any, Dict, Callable, Optional
from datetime import datetime

def load_test_data() -> Dict[str, Any]:
    """Load test data from config."""
    config_path = Path(__file__).parent.parent / "config" / "test_data.json"
    with open(config_path, 'r') as f:
        return json.load(f)

def validate_error_response(response: dict) -> bool:
    """Validate error response structure.

    Args:
        response: Response dictionary to validate

    Returns:
        True if valid error response

    Raises:
        AssertionError: If response structure is invalid
    """
    assert "error" in response, "Response missing 'error' field"
    assert response["error"] is True, "Error flag should be True"
    assert "message" in response, "Error response missing 'message'"
    return True

def validate_success_response(response: dict) -> bool:
    """Validate success response structure.

    Args:
        response: Response dictionary to validate

    Returns:
        True if valid success response

    Raises:
        AssertionError: If response contains error
    """
    assert not response.get("error", False), f"Unexpected error: {response.get('message')}"
    return True

def validate_patent_response(response: dict) -> bool:
    """Validate patent search response structure.

    Args:
        response: Response dictionary to validate

    Returns:
        True if valid patent response

    Raises:
        AssertionError: If response structure is invalid
    """
    validate_success_response(response)
    assert "numFound" in response or "total" in response, "Response missing result count"
    return True

def validate_document_response(response: dict) -> bool:
    """Validate document retrieval response structure.

    Args:
        response: Response dictionary to validate

    Returns:
        True if valid document response

    Raises:
        AssertionError: If response structure is invalid
    """
    validate_success_response(response)
    assert "guid" in response or "patentNumber" in response, "Response missing document identifier"
    return True

def validate_pdf_response(response: dict) -> bool:
    """Validate PDF download response structure.

    Args:
        response: Response dictionary to validate

    Returns:
        True if valid PDF response

    Raises:
        AssertionError: If response structure is invalid
    """
    validate_success_response(response)
    assert "content" in response, "PDF response missing 'content'"
    assert "content_type" in response, "PDF response missing 'content_type'"
    assert response["content_type"] == "application/pdf", "Invalid content type"
    return True

async def wait_for_condition(
    condition: Callable[[], bool],
    timeout: float = 10.0,
    interval: float = 0.1
) -> bool:
    """Wait for a condition to become true.

    Args:
        condition: Callable that returns bool when condition is met
        timeout: Maximum time to wait in seconds
        interval: Time between checks in seconds

    Returns:
        True if condition met, False if timeout
    """
    start_time = datetime.now()
    while (datetime.now() - start_time).total_seconds() < timeout:
        if condition():
            return True
        await asyncio.sleep(interval)
    return False

def create_mock_patent(patent_number: str) -> dict:
    """Create a mock patent document for testing.

    Args:
        patent_number: Patent number to use

    Returns:
        Mock patent dictionary
    """
    return {
        "guid": f"US-{patent_number}-B2",
        "patentNumber": patent_number,
        "type": "USPAT",
        "title": f"Test Patent {patent_number}",
        "abstract": f"Abstract for patent {patent_number}...",
        "inventors": ["John Doe", "Jane Smith"],
        "assignee": "Test Corporation",
        "date_publ": "2018-01-02",
        "imageLocation": f"US/{patent_number[:2]}/{patent_number[2:5]}/{patent_number[5:]}",
        "pageCount": 10,
        "documentStructure": {
            "image_location": f"US/{patent_number[:2]}/{patent_number[2:5]}/{patent_number[5:]}",
            "page_count": 10
        }
    }

def create_mock_application(app_number: str) -> dict:
    """Create a mock application document for testing.

    Args:
        app_number: Application number to use

    Returns:
        Mock application dictionary
    """
    return {
        "applicationNumberText": app_number,
        "applicationType": "utility",
        "applicationMetaData": {
            "filingDate": "2014-01-01",
            "applicationStatus": "patented"
        },
        "inventorNameArrayText": ["John Doe", "Jane Smith"],
        "assigneeEntityName": "Test Corporation"
    }

def assert_valid_pdf(content: bytes) -> None:
    """Assert that content is a valid PDF.

    Args:
        content: PDF content bytes

    Raises:
        AssertionError: If content is not a valid PDF
    """
    assert content.startswith(b"%PDF"), "Content does not start with PDF header"
    assert b"%%EOF" in content, "Content missing PDF EOF marker"

def compare_responses(response1: dict, response2: dict, ignore_keys: Optional[list] = None) -> bool:
    """Compare two response dictionaries, optionally ignoring certain keys.

    Args:
        response1: First response
        response2: Second response
        ignore_keys: List of keys to ignore in comparison

    Returns:
        True if responses match (ignoring specified keys)
    """
    if ignore_keys is None:
        ignore_keys = []

    # Create copies without ignored keys
    r1 = {k: v for k, v in response1.items() if k not in ignore_keys}
    r2 = {k: v for k, v in response2.items() if k not in ignore_keys}

    return r1 == r2
