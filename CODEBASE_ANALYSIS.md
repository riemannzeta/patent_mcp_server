# Patent MCP Server - Comprehensive Codebase Analysis

## Executive Summary

The **patent_mcp_server** is a Model Context Protocol (MCP) server that provides Claude Desktop and other MCP clients with tools to access USPTO (United States Patent and Trademark Office) patent data through two main APIs:
- **ppubs.uspto.gov** - Public Patent Search API for full-text documents and PDFs
- **api.uspto.gov** - Open Data Portal API for metadata and detailed patent information

The server implements **23 MCP tools** organized into two API client groups, with comprehensive error handling, retry logic, session caching, and input validation.

---

## 1. PROJECT STRUCTURE

### Directory Layout
```
patent_mcp_server/
├── src/
│   └── patent_mcp_server/
│       ├── patents.py              # Main MCP server - 23 tools defined
│       ├── config.py               # Configuration management (env vars)
│       ├── constants.py            # Constants and enums
│       ├── __main__.py             # Entry point
│       ├── __init__.py
│       ├── json/
│       │   └── search_query.json   # ppubs search query template
│       ├── uspto/
│       │   ├── ppubs_uspto_gov.py  # Client for ppubs.uspto.gov
│       │   ├── api_uspto_gov.py    # Client for api.uspto.gov
│       │   └── __init__.py
│       └── util/
│           ├── errors.py           # Error handling utilities
│           ├── validation.py       # Input validation with Pydantic
│           ├── logging.py          # Custom HTTP logging transport
│           └── __init__.py
├── test/
│   ├── test_tools_pytest.py        # Modern pytest-based tests (379 lines)
│   ├── test_tools.py               # Legacy test runner (703 lines)
│   ├── test_patents.py             # Direct HTTP request tests (236 lines)
│   ├── test_results/               # Test output directory
│   │   ├── *.json                  # API response samples
│   │   ├── US-9876543-B2.pdf       # Sample PDF download (1.8MB)
│   │   └── test_summary.json       # Test run summary
│   └── __init__.py
├── pyproject.toml                  # Project configuration
├── pytest.ini                      # Pytest configuration
├── setup.py                        # Setup script
├── README.md                       # Documentation
└── uv.lock                         # Dependency lock file
```

### Key Technologies
- **Framework**: FastMCP (MCP SDK for Python)
- **HTTP Client**: httpx with async/await
- **Validation**: Pydantic 2.0+
- **Resilience**: tenacity (retry decorator)
- **Testing**: pytest + pytest-asyncio
- **Python Version**: 3.10+ (originally 3.13, lowered for broader compatibility)

### Dependencies (from pyproject.toml)
```
h2>=4.2.0                    # HTTP/2 support
httpx>=0.28.1               # Async HTTP client
mcp[cli]>=1.3.0             # Model Context Protocol
python-dotenv>=1.0.1        # Environment variable loading
pydantic>=2.0.0             # Data validation
tenacity>=8.0.0             # Retry logic
```

---

## 2. MCP TOOLS IMPLEMENTED (23 Total)

### Group A: ppubs.uspto.gov Tools (5 tools)
These tools access the USPTO Public Patent Search API for full-text documents and PDFs.

| Tool Name | Purpose | Key Parameters | API Endpoint |
|-----------|---------|-----------------|--------------|
| `ppubs_search_patents` | Search granted patents | query, start, limit, sort, default_operator, expand_plurals, british_equivalents | POST `/api/searches/searchWithBeFamily` |
| `ppubs_search_applications` | Search published applications | query, start, limit, sort, default_operator, expand_plurals, british_equivalents | POST `/api/searches/searchWithBeFamily` |
| `ppubs_get_full_document` | Get full patent document by GUID | guid, source_type | GET `/api/patents/highlight/{guid}` |
| `ppubs_get_patent_by_number` | Get patent by number with full text | patent_number | POST `/api/searches/searchWithBeFamily` + GET `/api/patents/highlight` |
| `ppubs_download_patent_pdf` | Download patent as PDF | patent_number | POST `/api/print/imageviewer` + POST `/api/print/print-process` + GET `/api/internal/print/save/{pdf_name}` |

#### Implementation Details:
- All ppubs tools require a **session** with case ID and access token
- Sessions are **cached for 30 minutes** (configurable via SESSION_EXPIRY_MINUTES)
- Automatic session refresh on 403 errors
- Rate limit handling (429 responses with retry delays)
- Use HTTP/2 for performance
- Custom logging transport for debugging

### Group B: api.uspto.gov Tools (18 tools)
These tools access the USPTO Open Data Portal API for metadata and detailed information.

#### Application Metadata (11 tools)
| Tool Name | Purpose | Key Parameters | API Endpoint |
|-----------|---------|-----------------|--------------|
| `get_app` | Get basic patent application data | app_num | GET `/api/v1/patent/applications/{app_num}` |
| `get_app_metadata` | Get application metadata | app_num | GET `/api/v1/patent/applications/{app_num}/meta-data` |
| `get_app_adjustment` | Get patent term adjustment | app_num | GET `/api/v1/patent/applications/{app_num}/adjustment` |
| `get_app_assignment` | Get assignment data | app_num | GET `/api/v1/patent/applications/{app_num}/assignment` |
| `get_app_attorney` | Get attorney/agent information | app_num | GET `/api/v1/patent/applications/{app_num}/attorney` |
| `get_app_continuity` | Get continuity data | app_num | GET `/api/v1/patent/applications/{app_num}/continuity` |
| `get_app_foreign_priority` | Get foreign priority claims | app_num | GET `/api/v1/patent/applications/{app_num}/foreign-priority` |
| `get_app_transactions` | Get transaction history | app_num | GET `/api/v1/patent/applications/{app_num}/transactions` |
| `get_app_documents` | Get document details | app_num | GET `/api/v1/patent/applications/{app_num}/documents` |
| `get_app_associated_documents` | Get associated documents metadata | app_num | GET `/api/v1/patent/applications/{app_num}/associated-documents` |

#### Search & Download (4 tools - 2 versions each: GET and POST)
| Tool Name | Purpose | Key Parameters | API Endpoint |
|-----------|---------|-----------------|--------------|
| `search_applications` | Search applications (GET) | q, sort, offset, limit, facets, fields, filters, range_filters | GET `/api/v1/patent/applications/search?{params}` |
| `search_applications_post` | Search applications (POST) | q, filters, range_filters, sort, fields, offset, limit, facets | POST `/api/v1/patent/applications/search` |
| `download_applications` | Download applications (GET) | q, sort, offset, limit, fields, filters, range_filters, format | GET `/api/v1/patent/applications/search/download?{params}` |
| `download_applications_post` | Download applications (POST) | q, filters, range_filters, sort, fields, offset, limit, format | POST `/api/v1/patent/applications/search/download` |

#### Status Codes & Datasets (3 tools)
| Tool Name | Purpose | Key Parameters | API Endpoint |
|-----------|---------|-----------------|--------------|
| `get_status_codes` | Search status codes (GET) | q, offset, limit | GET `/api/v1/patent/status-codes?{params}` |
| `get_status_codes_post` | Search status codes (POST) | q, offset, limit | POST `/api/v1/patent/status-codes` |
| `search_datasets` | Search bulk datasets | q, product_title, product_description, product_short_name, offset, limit, facets, include_files, latest, labels, categories, datasets, file_types | GET `/api/v1/datasets/products/search?{params}` |
| `get_dataset_product` | Get specific dataset product | product_id, file_data_from_date, file_data_to_date, offset, limit, include_files, latest | GET `/api/v1/datasets/products/{product_id}?{params}` |

#### Implementation Details:
- All api.uspto.gov tools require **USPTO_API_KEY** in environment (warning issued if missing)
- Automatic retry with exponential backoff for network errors (max 3 attempts by default)
- Support for both GET (query string) and POST (JSON body) request formats
- Proper HTTP error handling with descriptive error messages
- Query string builder for GET requests with URL encoding

---

## 3. API ENDPOINTS CALLED

### ppubs.uspto.gov Endpoints (Base URL: https://ppubs.uspto.gov)

#### Session Management
```
POST /api/users/me/session
  - Purpose: Create/establish a session
  - Request: JSON body with authentication
  - Response: {userCase: {caseId: "..."}, headers: {X-Access-Token: "..."}}
  - Used by: All ppubs tools (cached for 30 minutes)
```

#### Search Operations
```
POST /api/searches/counts
  - Purpose: Get count of search results
  - Request: Query object with search parameters
  - Response: Count of matching patents/applications
  - Used by: ppubs_search_patents, ppubs_search_applications

POST /api/searches/searchWithBeFamily
  - Purpose: Execute full-text search
  - Request: Search query with source databases, pagination, sorting
  - Response: Results with patents/docs array, numFound, snippets
  - Used by: ppubs_search_patents, ppubs_search_applications
```

#### Document Retrieval
```
GET /api/patents/highlight/{guid}?queryId={queryId}&source={source_type}&includeSections={boolean}&uniqueId={uniqueId}
  - Purpose: Get full patent document details
  - Request: Query parameters with document GUID and source type
  - Response: Full document text with sections, claims, description
  - Used by: ppubs_get_full_document, ppubs_get_patent_by_number
```

#### PDF Download
```
POST /api/print/imageviewer
  - Purpose: Request PDF generation
  - Request: {caseId, pageKeys, patentGuid, saveOrPrint, source}
  - Response: Print job ID string
  - Used by: ppubs_download_patent_pdf

POST /api/print/print-process
  - Purpose: Check PDF generation status
  - Request: [print_job_id]
  - Response: [{printStatus: "COMPLETED|PENDING|FAILED", pdfName: "..."}]
  - Used by: ppubs_download_patent_pdf (polling)

GET /api/internal/print/save/{pdf_name}
  - Purpose: Download the generated PDF
  - Request: None
  - Response: PDF file (binary)
  - Used by: ppubs_download_patent_pdf
```

### api.uspto.gov Endpoints (Base URL: https://api.uspto.gov)

#### Patent Application Endpoints
```
GET /api/v1/patent/applications/{app_num}
GET /api/v1/patent/applications/{app_num}/meta-data
GET /api/v1/patent/applications/{app_num}/adjustment
GET /api/v1/patent/applications/{app_num}/assignment
GET /api/v1/patent/applications/{app_num}/attorney
GET /api/v1/patent/applications/{app_num}/continuity
GET /api/v1/patent/applications/{app_num}/foreign-priority
GET /api/v1/patent/applications/{app_num}/transactions
GET /api/v1/patent/applications/{app_num}/documents
GET /api/v1/patent/applications/{app_num}/associated-documents
  - Purpose: Retrieve specific application data types
  - Parameters: app_num (required)
  - Headers: X-API-KEY (required), User-Agent
  - Response: JSON with application-specific data
```

#### Search Endpoints
```
GET /api/v1/patent/applications/search?q={q}&sort={sort}&offset={offset}&limit={limit}&facets={facets}&fields={fields}&filters={filters}&rangeFilters={range_filters}
POST /api/v1/patent/applications/search
  - Purpose: Search patent applications
  - Parameters: Query string (GET) or JSON body (POST)
  - Response: {results: [...], total: N}
  - Supports: Faceting, field selection, filtering, range filtering, pagination
```

#### Download Endpoints
```
GET /api/v1/patent/applications/search/download?{params}
POST /api/v1/patent/applications/search/download
  - Purpose: Download application data in bulk
  - Parameters: Same as search endpoints + format (json/csv)
  - Response: Download file content (json/csv format)
```

#### Status Code Endpoints
```
GET /api/v1/patent/status-codes?q={q}&offset={offset}&limit={limit}
POST /api/v1/patent/status-codes
  - Purpose: Search patent application status codes
  - Response: {results: [...], total: N}
```

#### Dataset Endpoints
```
GET /api/v1/datasets/products/search?q={q}&productTitle={}&productDescription={}&offset={offset}&limit={limit}&facets={facets}&includeFiles={boolean}&latest={boolean}&labels={}&categories={}&datasets={}&fileTypes={}
  - Purpose: Search bulk dataset products
  - Response: {products: [...]} with file information

GET /api/v1/datasets/products/{product_id}?fileDataFromDate={}&fileDataToDate={}&offset={offset}&limit={limit}&includeFiles={boolean}&latest={boolean}
  - Purpose: Get specific dataset product details
  - Response: Product metadata with file information
```

---

## 4. TEST SUITE STRUCTURE

### Test Files Overview

#### 1. **test_tools_pytest.py** (379 lines) - RECOMMENDED
- Modern pytest-based test framework
- Async test support via pytest-asyncio
- Saves results to `test/test_results/`
- Supports test markers: `@pytest.mark.slow` for PDF downloads
- Run all tests: `pytest test/test_tools_pytest.py -v`
- Run excluding slow tests: `pytest test/test_tools_pytest.py -v -m "not slow"`
- Run with coverage: `pytest test/test_tools_pytest.py --cov=patent_mcp_server`

#### 2. **test_tools.py** (703 lines) - LEGACY
- Custom async test runner using raw asyncio
- Detailed logging with DEBUG level
- Tests all 23 tools
- Generates timing information per test
- Run: `uv run test/test_tools.py`

#### 3. **test_patents.py** (236 lines) - DIRECT HTTP TESTING
- Low-level HTTP request tests
- Useful for debugging API interaction
- Direct requests to USPTO endpoints

### Test Coverage (23 Tools Tested)

#### ppubs.uspto.gov Tests (5 tools)
```
✓ test_ppubs_search_patents
✓ test_ppubs_search_applications  
✓ test_ppubs_get_full_document
✓ test_ppubs_get_patent_by_number
✓ test_ppubs_download_patent_pdf (@pytest.mark.slow)
```

#### api.uspto.gov Tests (18 tools)
```
✓ test_get_app
✓ test_search_applications
✓ test_search_applications_post
✓ test_download_applications
✓ test_download_applications_post
✓ test_get_app_metadata
✓ test_get_app_adjustment
✓ test_get_app_assignment
✓ test_get_app_attorney
✓ test_get_app_continuity
✓ test_get_app_foreign_priority
✓ test_get_app_transactions
✓ test_get_app_documents
✓ test_get_app_associated_documents
✓ test_get_status_codes
✓ test_get_status_codes_post
✓ test_search_datasets
✓ test_get_dataset_product
```

### Test Fixtures & Helpers
```python
@pytest.fixture
def results_dir():
    """Provide the results directory path"""
    
async def save_result(result: dict, filename: str, results_dir: Path):
    """Helper to save test results to JSON"""
    
async def save_pdf(result: dict, filename: str, results_dir: Path) -> bool:
    """Helper to save PDF results"""
```

### Test Configuration (pytest.ini)
- Python files: `test_*.py` and `*_test.py`
- Test classes: `Test*`
- Test functions: `test_*`
- Asyncio mode: auto
- Markers: slow, integration, unit
- Test path: `test/`

### Test Results Artifacts
The `test/test_results/` directory contains:
- **JSON Files** (one per tool): API responses from last test run
- **PDF Files**: Sample downloaded patents (if PDF test ran)
- **test_summary.json**: Test execution summary with pass/fail status

### Test Constants
```python
PATENT_NUMBER = "9876543"      # Sample granted patent
APP_NUMBER = "14412875"         # Sample application
RESULTS_DIR = Path("test/test_results")
```

---

## 5. MAIN SOURCE FILES AND PURPOSES

### Core Files

#### **patents.py** (784 lines)
**Main MCP server implementation**
- Initializes FastMCP server
- Defines all 23 MCP tools using `@mcp.tool()` decorator
- Creates client instances (PpubsClient, ApiUsptoClient)
- Handles cleanup and shutdown
- Helper function: `_search_patent_by_number()` - shared patent search logic

**Key Components:**
```python
# Server initialization
mcp = FastMCP("uspto_patent_tools")

# Clients
ppubs_client = PpubsClient()
api_client = ApiUsptoClient()

# Tool decorators
@mcp.tool()
async def tool_name(...) -> Dict[str, Any]:
    """Tool docstring"""
```

#### **config.py** (76 lines)
**Centralized configuration management**
- Loads from `.env` file via python-dotenv
- All settings have sensible defaults
- Configuration categories:
  - **API Keys**: USPTO_API_KEY
  - **API Endpoints**: PPUBS_BASE_URL, API_BASE_URL
  - **Logging**: LOG_LEVEL
  - **HTTP Settings**: USER_AGENT, REQUEST_TIMEOUT
  - **Rate Limiting**: MAX_RETRIES, RETRY_DELAY, RETRY_MIN_WAIT, RETRY_MAX_WAIT
  - **Session Management**: SESSION_EXPIRY_MINUTES
  - **Caching**: ENABLE_CACHING

**Key Methods:**
```python
config.get_log_level()  # Convert string to logging constant
config.validate()       # Validate and warn about missing settings
```

#### **constants.py** (72 lines)
**Centralized constants and enumerations**
- Eliminates magic strings throughout codebase
- Classes:
  - `Sources`: Patent data source types (USPAT, US-PGPUB, USOCR)
  - `Fields`: Common API response field names
  - `SortOrders`: Date sorting constants
  - `Operators`: Query operators (AND, OR)
  - `PrintStatus`: PDF print job status values
  - `HTTPMethods`: HTTP method constants
  - `Defaults`: Default values for operations

### API Client Files

#### **ppubs_uspto_gov.py** (465 lines)
**Client for USPTO Public Patent Search API**

**Class: PpubsClient**
- HTTP/2 async client with custom headers
- Custom LoggingTransport for debugging
- Session management with 30-minute caching

**Key Methods:**
```python
async def get_session() -> Optional[Dict[str, Any]]:
    """Establish or retrieve cached session"""
    
async def make_request() -> Union[httpx.Response, Dict]:
    """Make request with automatic retry and session refresh"""
    
async def run_query() -> Dict[str, Any]:
    """Execute search query against USPTO"""
    
async def get_document() -> Dict[str, Any]:
    """Retrieve full patent document by GUID"""
    
async def _request_save() -> Union[str, Dict]:
    """Request PDF generation"""
    
async def download_image() -> Dict[str, Any]:
    """Download patent as PDF with polling"""
```

**Features:**
- Automatic session refresh on 403
- Rate limit handling (429 responses)
- Exponential backoff retry (via tenacity)
- Polling for PDF generation
- Context manager support

#### **api_uspto_gov.py** (176 lines)
**Client for USPTO Open Data Portal API**

**Class: ApiUsptoClient**
- HTTP/2 async client with API key header
- Custom LoggingTransport for debugging
- Query string builder for GET requests

**Key Methods:**
```python
def build_query_string(params: Dict) -> str:
    """Build URL-encoded query string from parameters"""
    
async def make_request() -> Optional[Dict[str, Any]]:
    """Make GET or POST request with retry logic"""
```

**Features:**
- Automatic retry with exponential backoff
- Proper HTTP error handling
- GET and POST support
- JSON request body support
- Query string encoding

### Utility Files

#### **errors.py** (142 lines)
**Error handling utilities**

**Class: ApiError**
- Standardized error response creation
- Consistent error dictionary structure

**Methods:**
```python
@staticmethod
def create(message, status_code, error_code, details) -> Dict:
    """Create standardized error response"""
    
@staticmethod
def from_http_error(status_code, response_text, response_json) -> Dict:
    """Create error from HTTP response"""
    
@staticmethod
def from_exception(exception, context) -> Dict:
    """Create error from exception"""
    
@staticmethod
def not_found(resource_type, identifier) -> Dict:
    """Create 'not found' error"""
    
@staticmethod
def validation_error(message, field) -> Dict:
    """Create validation error"""
```

**Function:**
```python
def is_error(response: Dict) -> bool:
    """Check if response is an error"""
```

#### **validation.py** (134 lines)
**Input validation using Pydantic**

**Pydantic Models:**
- `PatentNumberInput`: Validates and cleans patent numbers
- `ApplicationNumberInput`: Validates application numbers
- `SearchQueryInput`: Validates search queries
- `GuidInput`: Validates document GUIDs
- `PaginationInput`: Validates pagination parameters

**Validation Functions:**
```python
def validate_patent_number(patent_number: str) -> str:
    """Validate and return cleaned patent number"""
    
def validate_app_number(app_num: str) -> str:
    """Validate and return cleaned application number"""
```

**Validation Rules:**
- Patent numbers: Non-numeric chars removed
- App numbers: At least 6 digits
- Search queries: Non-empty, trimmed
- GUIDs: Non-empty, length validated
- Source types: USPAT, US-PGPUB, or USOCR

#### **logging.py** (44 lines)
**Custom HTTP transport for request/response logging**

**Class: LoggingTransport(httpx.AsyncBaseTransport)**
- Wraps httpx transport for detailed request/response logging
- Logs request method, URL, headers, body
- Logs response status and headers
- Pretty-prints JSON bodies
- DEBUG level logging only

### Entry Points

#### **__main__.py** (5 lines)
```python
from patent_mcp_server.patents import main
if __name__ == "__main__":
    main()
```

#### **patents.py - main() function**
```python
def main():
    """Initialize and run the server with stdio transport."""
    logger.info("Starting USPTO Patent MCP server with stdio transport")
    mcp.run(transport='stdio')
```

---

## 6. ARCHITECTURAL PATTERNS & BEST PRACTICES

### Design Patterns

#### 1. **Async/Await Pattern**
- All API calls are async (httpx.AsyncClient)
- All tools are coroutines with async def
- Session management is async
- Enables concurrent requests

#### 2. **Retry with Exponential Backoff**
- Uses tenacity library decorator
- Applied to: PpubsClient.make_request(), ApiUsptoClient.make_request()
- Configurable: MAX_RETRIES (default 3), RETRY_DELAY, RETRY_MIN_WAIT, RETRY_MAX_WAIT
- Retries on: httpx.TimeoutException, httpx.NetworkError

#### 3. **Session Caching**
- ppubs sessions cached for 30 minutes
- Reduces overhead of repeated session creation
- Automatic refresh on 403 Unauthorized

#### 4. **Error Handling**
- Standardized error response format
- Specific error types: NOT_FOUND, VALIDATION_ERROR, HTTP errors
- Error propagation from utilities to tools
- Caller receives structured error dict

#### 5. **Configuration Management**
- Centralized Config class
- Environment variables with defaults
- Validation on startup
- Logging of configuration state

#### 6. **Input Validation**
- Pydantic models for all inputs
- Patent/app number cleaning and validation
- Prevents invalid API calls
- Clear validation error messages

#### 7. **Context Manager Protocol**
- Both clients support async context managers
- Proper resource cleanup on exit
- Shutdown handler with atexit registration

#### 8. **MCP Tool Registration**
- @mcp.tool() decorator for each tool
- FastMCP auto-discovers and exposes tools
- Docstrings become tool documentation
- Type hints enable parameter validation

### Code Quality Features

#### Centralization
- Constants module eliminates magic strings
- Config module centralizes settings
- ApiError utility standardizes error handling
- Validation module consolidates input checks

#### Resilience
- Automatic retries for transient failures
- Session refresh on auth errors
- Rate limit handling
- Graceful error reporting

#### Observability
- Comprehensive logging at DEBUG level
- Custom transport logs all HTTP traffic
- Request/response body logging
- Structured error information

#### Testing
- Modern pytest framework
- Async test support
- 23 tools tested
- Results saved for inspection
- Test markers for slow tests

---

## 7. CONFIGURATION REFERENCE

### Environment Variables
```bash
# API Keys
USPTO_API_KEY=your_key_here    # Required for api.uspto.gov tools

# API Endpoints (usually don't change)
PPUBS_BASE_URL=https://ppubs.uspto.gov
API_BASE_URL=https://api.uspto.gov

# Logging
LOG_LEVEL=INFO                 # DEBUG, INFO, WARNING, ERROR, CRITICAL

# HTTP Settings
USER_AGENT=patent-mcp-server/0.2.3
REQUEST_TIMEOUT=30.0           # Seconds

# Rate Limiting & Retry
MAX_RETRIES=3                  # Max retry attempts
RETRY_DELAY=1.0                # Multiplier for exponential backoff
RETRY_MIN_WAIT=2               # Min seconds between retries
RETRY_MAX_WAIT=10              # Max seconds between retries

# Session Management
SESSION_EXPIRY_MINUTES=30      # ppubs session cache duration

# Caching
ENABLE_CACHING=true            # Enable session caching
```

### Default Values (from constants.py)
```python
SEARCH_START = 0               # Default pagination start
SEARCH_LIMIT = 100             # Default search results limit
SEARCH_LIMIT_MAX = 500         # Maximum allowed
API_LIMIT = 25                 # Default API results limit
DATASET_LIMIT = 10             # Default dataset results
```

---

## 8. DEPLOYMENT & INTEGRATION

### Installation
```bash
git clone https://github.com/riemannzeta/patent_mcp_server
cd patent_mcp_server
uv sync                        # Install dependencies
```

### Running the Server
```bash
uv run patent-mcp-server       # Direct run
python -m patent_mcp_server    # Via module
```

### Claude Desktop Integration
Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "patents": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/patent_mcp_server",
        "run",
        "patent-mcp-server"
      ]
    }
  }
}
```

### Running Tests
```bash
# Modern test suite (recommended)
pytest test/test_tools_pytest.py -v

# Exclude slow tests (PDF downloads)
pytest test/test_tools_pytest.py -v -m "not slow"

# With coverage report
pytest test/test_tools_pytest.py --cov=patent_mcp_server

# Legacy test suite
uv run test/test_tools.py
```

---

## 9. PROJECT STATISTICS

### Code Metrics
- **Total Tools**: 23 MCP tools
- **API Endpoints Called**: 15+ (ppubs) + 15+ (api.uspto.gov)
- **Source Files**: 13 Python files
- **Test Files**: 3 test suites
- **Total Lines**: ~2,000 lines of code
- **Documentation**: README.md (220+ lines)

### Test Coverage
- **Test Files**: 379 lines (pytest) + 703 lines (legacy) + 236 lines (direct)
- **Tests Defined**: 23 tools × 1 test each = 23 core tests
- **Test Results**: JSON responses saved for all 23 tests
- **Sample Data**: 1.8MB PDF, 300KB+ JSON responses

---

## 10. KEY INTEGRATION POINTS WITH USPTO APIS

### ppubs.uspto.gov Integration
1. **Session Establishment**: Create case ID and access token
2. **Search Query**: Execute full-text search with database filtering
3. **Result Retrieval**: Get patents/applications from search results
4. **Document Access**: Retrieve full document by GUID
5. **PDF Pipeline**: Request → Poll → Download

### api.uspto.gov Integration
1. **API Authentication**: X-API-KEY header
2. **Application Lookup**: Direct app number access
3. **Data Retrieval**: 11 different metadata endpoints
4. **Search Interface**: Query/POST search with filtering
5. **Bulk Download**: CSV/JSON data export

---

## Summary

The **patent_mcp_server** is a well-architected MCP server that:

✓ Implements **23 comprehensive tools** for patent data access
✓ Calls **30+ USPTO API endpoints** with proper error handling
✓ Features **robust retry logic** and session caching
✓ Includes **input validation** via Pydantic
✓ Has **extensive test coverage** with multiple test frameworks
✓ Follows **modern Python async patterns**
✓ Provides **detailed logging** for debugging
✓ Maintains **clean code organization** with utilities and constants
✓ Supports **easy integration** with Claude Desktop
✓ Is **production-ready** with proper error handling and resilience

