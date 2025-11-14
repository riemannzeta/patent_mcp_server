"""Shared pytest fixtures for all tests."""
import pytest
from pathlib import Path
import json
import base64

# Test constants
PATENT_NUMBER = "6000000"
APP_NUMBER = "16123456"
RESULTS_DIR = Path("test/test_results")

@pytest.fixture
def results_dir():
    """Provide the results directory path."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    return RESULTS_DIR

@pytest.fixture
def patent_number():
    """Provide a test patent number."""
    return PATENT_NUMBER

@pytest.fixture
def app_number():
    """Provide a test application number."""
    return APP_NUMBER

@pytest.fixture
async def save_result():
    """Helper to save test results to JSON."""
    async def _save(result: dict, filename: str, results_dir: Path):
        filepath = results_dir / filename
        with open(filepath, 'w') as f:
            json.dump(result, f, indent=2, default=str)
    return _save

@pytest.fixture
async def save_pdf():
    """Helper to save PDF results."""
    async def _save(result: dict, filename: str, results_dir: Path) -> bool:
        if result.get("success") and result.get("content"):
            filepath = results_dir / filename
            pdf_content = base64.b64decode(result["content"])
            with open(filepath, 'wb') as f:
                f.write(pdf_content)
            return True
        return False
    return _save

@pytest.fixture
def load_test_data():
    """Load test data from configuration."""
    def _load():
        config_path = Path(__file__).parent / "config" / "test_data.json"
        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)
        return {}
    return _load

@pytest.fixture
def validate_error_response():
    """Validator for error response structure."""
    def _validate(response: dict) -> bool:
        assert "error" in response, "Response missing 'error' field"
        assert response["error"] is True, "Error flag should be True"
        assert "message" in response, "Error response missing 'message'"
        return True
    return _validate

@pytest.fixture
def validate_success_response():
    """Validator for success response structure."""
    def _validate(response: dict) -> bool:
        assert not response.get("error", False), f"Unexpected error: {response.get('message')}"
        return True
    return _validate

@pytest.fixture
def validate_patent_response():
    """Validator for patent search response structure."""
    def _validate(response: dict) -> bool:
        assert not response.get("error", False), f"Unexpected error: {response.get('message')}"
        assert "numFound" in response or "total" in response, "Response missing result count"
        return True
    return _validate
