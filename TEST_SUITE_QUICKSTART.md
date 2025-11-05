# Patent MCP Server - Test Suite Quick Start Guide

## Overview

This guide provides step-by-step instructions to implement the proposed comprehensive test suite for the patent_mcp_server project.

## Prerequisites

### Required Packages
```bash
pip install pytest pytest-asyncio pytest-cov pytest-mock pytest-xdist respx
```

Or add to `pyproject.toml`:
```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "pytest-cov>=4.0",
    "pytest-mock>=3.11",
    "pytest-xdist>=3.3",
    "respx>=0.20",
]
```

Then install:
```bash
pip install -e ".[dev]"
```

## Phase 1: Foundation Setup (Day 1)

### Step 1: Create Directory Structure

```bash
cd /home/user/patent_mcp_server

# Create test directories
mkdir -p test/{unit,integration,mock,errors,performance,fixtures,utils,config}

# Create __init__.py files
touch test/unit/__init__.py
touch test/integration/__init__.py
touch test/mock/__init__.py
touch test/errors/__init__.py
touch test/performance/__init__.py
touch test/fixtures/__init__.py
touch test/utils/__init__.py
touch test/config/__init__.py
```

### Step 2: Update pytest.ini

```bash
cat > pytest.ini << 'EOF'
[pytest]
minversion = 7.0
testpaths = test
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Asyncio configuration
asyncio_mode = auto

# Markers for test categorization
markers =
    unit: Unit tests (fast, mocked)
    integration: Integration tests (real API calls)
    mock: Mocked tests (fast, offline)
    error: Error scenario tests
    performance: Performance tests
    slow: Slow tests (e.g., PDF downloads)
    ppubs: Tests for ppubs.uspto.gov
    api: Tests for api.uspto.gov

# Test output
addopts =
    -v
    --tb=short
    --strict-markers
    --disable-warnings
    -p no:warnings

# Coverage settings
[tool:pytest]
testpaths = test

[coverage:run]
source = src/patent_mcp_server
omit =
    */tests/*
    */test/*
    */__init__.py

[coverage:report]
precision = 2
show_missing = True
skip_covered = False
EOF
```

### Step 3: Create conftest.py

```python
cat > test/conftest.py << 'EOF'
"""Shared pytest fixtures for all tests."""
import pytest
from pathlib import Path
import json

# Test constants
PATENT_NUMBER = "9876543"
APP_NUMBER = "14412875"
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
EOF
```

### Step 4: Create Test Configuration

```python
cat > test/config/test_data.json << 'EOF'
{
  "patents": {
    "valid": ["9876543", "7123456", "8234567"],
    "invalid": ["", "abc", "123", "99999999999"],
    "not_found": ["1111111"]
  },
  "applications": {
    "valid": ["14412875", "15123456", "16234567"],
    "invalid": ["", "abc", "123/456"],
    "not_found": ["99999999"]
  },
  "search_queries": {
    "basic": "artificial intelligence",
    "advanced": "artificial intelligence AND (machine learning OR neural network)",
    "patent_number": "patentNumber:\"9876543\"",
    "date_range": "date_publ:[20200101 TO 20231231]"
  },
  "timeouts": {
    "fast": 5,
    "normal": 30,
    "slow": 120
  }
}
EOF
```

### Step 5: Create Test Utilities

```python
cat > test/utils/helpers.py << 'EOF'
"""Test helper utilities."""
import json
from pathlib import Path
from typing import Any, Dict

def load_test_data() -> Dict[str, Any]:
    """Load test data from config."""
    config_path = Path(__file__).parent.parent / "config" / "test_data.json"
    with open(config_path, 'r') as f:
        return json.load(f)

def validate_error_response(response: dict) -> bool:
    """Validate error response structure."""
    assert "error" in response
    assert response["error"] is True
    assert "message" in response
    return True

def validate_success_response(response: dict) -> bool:
    """Validate success response structure."""
    assert not response.get("error", False), f"Unexpected error: {response.get('message')}"
    return True

def validate_patent_response(response: dict) -> bool:
    """Validate patent search response structure."""
    validate_success_response(response)
    assert "numFound" in response or "total" in response
    return True
EOF
```

## Phase 2: Unit Tests (Days 2-4)

### Example: PpubsClient Unit Tests

```python
cat > test/unit/test_ppubs_client.py << 'EOF'
"""Unit tests for PpubsClient."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from datetime import datetime, timedelta

from patent_mcp_server.uspto.ppubs_uspto_gov import PpubsClient

@pytest.fixture
async def ppubs_client():
    """Create a PpubsClient instance for testing."""
    client = PpubsClient()
    yield client
    await client.close()

@pytest.fixture
def mock_session_response():
    """Mock session response."""
    return {
        "userCase": {
            "caseId": "test-case-123",
            "userId": "test-user"
        }
    }

@pytest.mark.unit
@pytest.mark.asyncio
async def test_client_initialization():
    """Test client initialization."""
    client = PpubsClient()
    assert client.case_id is None
    assert client.access_token is None
    assert client.session_expires_at is None
    await client.close()

@pytest.mark.unit
@pytest.mark.asyncio
async def test_session_creation_success(ppubs_client, mock_session_response):
    """Test successful session creation."""
    # Mock the HTTP responses
    with patch.object(ppubs_client.client, 'get', new_callable=AsyncMock) as mock_get:
        with patch.object(ppubs_client.client, 'post', new_callable=AsyncMock) as mock_post:
            # Mock GET request
            mock_get.return_value = MagicMock(status_code=200)

            # Mock POST request
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_session_response
            mock_response.headers = {"X-Access-Token": "test-token-123"}
            mock_response.text = json.dumps(mock_session_response)
            mock_post.return_value = mock_response

            # Call get_session
            session = await ppubs_client.get_session()

            # Assertions
            assert session is not None
            assert ppubs_client.case_id == "test-case-123"
            assert ppubs_client.access_token == "test-token-123"
            assert ppubs_client.session_expires_at is not None

@pytest.mark.unit
@pytest.mark.asyncio
async def test_session_caching(ppubs_client, mock_session_response):
    """Test session caching."""
    # Set up cached session
    ppubs_client.session = mock_session_response
    ppubs_client.case_id = "test-case-123"
    ppubs_client.session_expires_at = datetime.now() + timedelta(minutes=30)

    # Should return cached session without making HTTP request
    session = await ppubs_client.get_session()

    assert session == mock_session_response
    assert ppubs_client.case_id == "test-case-123"

@pytest.mark.unit
@pytest.mark.asyncio
async def test_session_expiration_refresh(ppubs_client, mock_session_response):
    """Test session refresh after expiration."""
    # Set up expired session
    ppubs_client.session = mock_session_response
    ppubs_client.session_expires_at = datetime.now() - timedelta(minutes=1)

    # Mock the HTTP responses
    with patch.object(ppubs_client.client, 'get', new_callable=AsyncMock) as mock_get:
        with patch.object(ppubs_client.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_get.return_value = MagicMock(status_code=200)

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_session_response
            mock_response.headers = {"X-Access-Token": "new-token-456"}
            mock_response.text = json.dumps(mock_session_response)
            mock_post.return_value = mock_response

            # Should refresh session
            session = await ppubs_client.get_session()

            assert ppubs_client.access_token == "new-token-456"

@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limit_handling(ppubs_client):
    """Test rate limit (429) response handling."""
    with patch.object(ppubs_client.client, 'request', new_callable=AsyncMock) as mock_request:
        # First response: rate limited
        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {"x-rate-limit-retry-after-seconds": "2"}

        # Second response: success
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {"result": "success"}

        mock_request.side_effect = [rate_limit_response, success_response]

        # Should handle rate limit and retry
        response = await ppubs_client.make_request("GET", "http://test.com")

        assert response.status_code == 200
        assert mock_request.call_count == 2

@pytest.mark.unit
@pytest.mark.asyncio
async def test_network_error_retry(ppubs_client):
    """Test network error retry logic."""
    with patch.object(ppubs_client.client, 'request', new_callable=AsyncMock) as mock_request:
        # First attempt: network error
        # Second attempt: success
        mock_request.side_effect = [
            httpx.NetworkError("Connection failed"),
            MagicMock(status_code=200)
        ]

        # Should retry and succeed
        response = await ppubs_client.make_request("GET", "http://test.com")

        assert response.status_code == 200
        assert mock_request.call_count == 2
EOF
```

### Example: Validation Unit Tests

```python
cat > test/unit/test_validation.py << 'EOF'
"""Unit tests for validation functions."""
import pytest
from patent_mcp_server.util.validation import validate_patent_number, validate_app_number

@pytest.mark.unit
def test_validate_patent_number_valid():
    """Test patent number validation with valid input."""
    assert validate_patent_number("9876543") == "9876543"
    assert validate_patent_number("7123456") == "7123456"
    assert validate_patent_number("US9876543") == "9876543"  # Strip prefix
    assert validate_patent_number("9,876,543") == "9876543"  # Strip commas

@pytest.mark.unit
def test_validate_patent_number_invalid():
    """Test patent number validation with invalid input."""
    with pytest.raises(ValueError, match="Patent number cannot be empty"):
        validate_patent_number("")

    with pytest.raises(ValueError, match="Patent number must be numeric"):
        validate_patent_number("abc")

    with pytest.raises(ValueError, match="Patent number too short"):
        validate_patent_number("123")

@pytest.mark.unit
def test_validate_app_number_valid():
    """Test application number validation with valid input."""
    assert validate_app_number("14412875") == "14412875"
    assert validate_app_number("15/123,456") == "15123456"  # Strip separators
    assert validate_app_number("14/412875") == "14412875"

@pytest.mark.unit
def test_validate_app_number_invalid():
    """Test application number validation with invalid input."""
    with pytest.raises(ValueError, match="Application number cannot be empty"):
        validate_app_number("")

    with pytest.raises(ValueError, match="Application number must be numeric"):
        validate_app_number("abc/def")
EOF
```

## Phase 3: Mock Tests (Days 5-7)

### Example: Mock Fixtures

```python
cat > test/fixtures/ppubs_responses.py << 'EOF'
"""Mock responses for ppubs.uspto.gov API."""
import base64

MOCK_SESSION_RESPONSE = {
    "userCase": {
        "caseId": "test-case-123456",
        "userId": "test-user",
        "queries": []
    },
    "settings": {}
}

MOCK_SEARCH_RESPONSE = {
    "numFound": 1,
    "start": 0,
    "patents": [
        {
            "guid": "US-9876543-B2",
            "patentNumber": "9876543",
            "type": "USPAT",
            "title": "Test Patent Title",
            "abstract": "Test patent abstract describing the invention...",
            "inventors": ["John Doe", "Jane Smith"],
            "assignee": "Test Corporation",
            "date_publ": "2018-01-02",
            "imageLocation": "US/09/876/543",
            "pageCount": 10,
            "documentStructure": {
                "image_location": "US/09/876/543",
                "page_count": 10
            }
        }
    ]
}

MOCK_DOCUMENT_RESPONSE = {
    "guid": "US-9876543-B2",
    "patentNumber": "9876543",
    "type": "USPAT",
    "title": "Test Patent Title",
    "abstract": "Test patent abstract...",
    "sections": {
        "abstract": "Detailed abstract text...",
        "claims": ["Claim 1: A method comprising...", "Claim 2: The method of claim 1..."],
        "description": "Detailed description of the invention...",
        "drawings": []
    }
}

# Mock PDF content (base64 encoded minimal PDF)
MOCK_PDF_CONTENT = base64.b64encode(
    b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
    b"2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n"
    b"3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\n"
    b"xref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n"
    b"0000000115 00000 n\ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n190\n%%EOF"
).decode('utf-8')

MOCK_PDF_JOB_RESPONSE = [
    {
        "printStatus": "COMPLETED",
        "pdfName": "test-patent-9876543.pdf"
    }
]
EOF
```

### Example: Mocked Tool Tests

```python
cat > test/mock/test_ppubs_tools_mocked.py << 'EOF'
"""Mocked tests for ppubs.uspto.gov tools."""
import pytest
import respx
import httpx
from test.fixtures.ppubs_responses import (
    MOCK_SESSION_RESPONSE,
    MOCK_SEARCH_RESPONSE,
    MOCK_DOCUMENT_RESPONSE,
    MOCK_PDF_CONTENT
)

from patent_mcp_server.patents import (
    ppubs_search_patents,
    ppubs_get_patent_by_number,
    ppubs_download_patent_pdf
)

@pytest.mark.mock
@pytest.mark.asyncio
@respx.mock
async def test_ppubs_search_patents_mocked():
    """Test patent search with mocked response."""
    # Mock session creation
    respx.get("https://ppubs.uspto.gov/pubwebapp/").mock(return_value=httpx.Response(200))
    respx.post("https://ppubs.uspto.gov/api/users/me/session").mock(
        return_value=httpx.Response(
            200,
            json=MOCK_SESSION_RESPONSE,
            headers={"X-Access-Token": "test-token"}
        )
    )

    # Mock search counts
    respx.post("https://ppubs.uspto.gov/api/searches/counts").mock(
        return_value=httpx.Response(200, json={"numFound": 1})
    )

    # Mock search execution
    respx.post("https://ppubs.uspto.gov/api/searches/searchWithBeFamily").mock(
        return_value=httpx.Response(200, json=MOCK_SEARCH_RESPONSE)
    )

    # Execute test
    result = await ppubs_search_patents(query='patentNumber:"9876543"', limit=10)

    # Assertions
    assert not result.get("error", False)
    assert result.get("numFound") == 1
    assert len(result.get("patents", [])) == 1
    assert result["patents"][0]["patentNumber"] == "9876543"

@pytest.mark.mock
@pytest.mark.asyncio
@respx.mock
async def test_ppubs_search_error_handling():
    """Test error handling with mocked error response."""
    # Mock session
    respx.get("https://ppubs.uspto.gov/pubwebapp/").mock(return_value=httpx.Response(200))
    respx.post("https://ppubs.uspto.gov/api/users/me/session").mock(
        return_value=httpx.Response(
            200,
            json=MOCK_SESSION_RESPONSE,
            headers={"X-Access-Token": "test-token"}
        )
    )

    # Mock search counts with error
    respx.post("https://ppubs.uspto.gov/api/searches/counts").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )

    # Execute test
    result = await ppubs_search_patents(query="invalid query", limit=10)

    # Should return error
    assert result.get("error") is True
    assert "message" in result
EOF
```

## Running the Tests

### Run All Unit Tests
```bash
pytest -m unit -v
```

### Run All Mock Tests
```bash
pytest -m mock -v
```

### Run Fast Tests (Unit + Mock)
```bash
pytest -m "unit or mock" -v
```

### Run with Coverage
```bash
pytest -m "unit or mock" --cov=src/patent_mcp_server --cov-report=html --cov-report=term
```

### View Coverage Report
```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## Expected Results After Phase 1-3

### Test Execution
```bash
$ pytest -m "unit or mock" -v

======================================== test session starts ========================================
collected 50 items

test/unit/test_ppubs_client.py::test_client_initialization PASSED                           [  2%]
test/unit/test_ppubs_client.py::test_session_creation_success PASSED                        [  4%]
test/unit/test_ppubs_client.py::test_session_caching PASSED                                 [  6%]
test/unit/test_ppubs_client.py::test_session_expiration_refresh PASSED                      [  8%]
test/unit/test_ppubs_client.py::test_rate_limit_handling PASSED                             [ 10%]
test/unit/test_ppubs_client.py::test_network_error_retry PASSED                             [ 12%]
...
test/mock/test_ppubs_tools_mocked.py::test_ppubs_search_patents_mocked PASSED              [ 90%]
test/mock/test_ppubs_tools_mocked.py::test_ppubs_search_error_handling PASSED              [ 92%]
...

======================================== 50 passed in 2.35s =========================================
```

### Coverage Report
```
Name                                              Stmts   Miss  Cover
---------------------------------------------------------------------
src/patent_mcp_server/patents.py                    200     20    90%
src/patent_mcp_server/uspto/ppubs_uspto_gov.py      150     10    93%
src/patent_mcp_server/uspto/api_uspto_gov.py         80      5    94%
src/patent_mcp_server/util/validation.py             30      2    93%
src/patent_mcp_server/util/errors.py                 40      3    93%
---------------------------------------------------------------------
TOTAL                                                500     40    92%
```

## Troubleshooting

### Import Errors
```bash
# Make sure the package is installed in editable mode
pip install -e .
```

### Async Test Errors
```bash
# Make sure pytest-asyncio is installed
pip install pytest-asyncio

# Check pytest.ini has asyncio_mode = auto
```

### Mock Not Working
```bash
# Make sure respx is installed
pip install respx

# Use @respx.mock decorator
```

## Next Steps

After completing Phase 1-3:
1. Review test results and coverage
2. Proceed to Phase 4: Integration Tests
3. Proceed to Phase 5: Performance Tests
4. Set up CI/CD in Phase 6

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [respx Documentation](https://lundberg.github.io/respx/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)

---

**Ready to start?** Follow this guide step-by-step to build the comprehensive test suite!
