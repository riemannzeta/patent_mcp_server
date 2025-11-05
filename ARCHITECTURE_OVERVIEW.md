# Patent MCP Server - Architecture Overview

## High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         Claude Desktop (MCP Client)                             │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        │ stdio transport
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      Patent MCP Server (FastMCP)                                │
│                        patents.py (main entry point)                            │
│                                                                                 │
│  ┌────────────────────────────────────────────────────────────────────────┐    │
│  │                      23 MCP Tools (async functions)                    │    │
│  │                                                                        │    │
│  │  Group A: ppubs.uspto.gov Tools (5)     Group B: api.uspto.gov Tools (18)  │
│  │  ├─ ppubs_search_patents                ├─ get_app                        │
│  │  ├─ ppubs_search_applications           ├─ search_applications (_get/_post)│
│  │  ├─ ppubs_get_full_document             ├─ download_applications(_get/_post)
│  │  ├─ ppubs_get_patent_by_number          ├─ get_app_metadata               │
│  │  └─ ppubs_download_patent_pdf           ├─ get_app_adjustment             │
│  │                                         ├─ get_app_assignment             │
│  │                                         ├─ get_app_attorney               │
│  │                                         ├─ get_app_continuity             │
│  │                                         ├─ get_app_foreign_priority       │
│  │                                         ├─ get_app_transactions           │
│  │                                         ├─ get_app_documents              │
│  │                                         ├─ get_app_associated_documents   │
│  │                                         ├─ get_status_codes (_get/_post)  │
│  │                                         ├─ search_datasets                │
│  │                                         └─ get_dataset_product            │
│  └────────────────────────────────────────────────────────────────────────┘    │
│                                    │                                            │
│  ┌────────────────────────────────┴──────────────────────────────────────┐    │
│  │              Input Validation & Error Handling Layer                  │    │
│  │                                                                        │    │
│  │  ├─ validation.py (Pydantic models)                                   │    │
│  │  │   ├─ PatentNumberInput (clean & validate)                        │    │
│  │  │   └─ ApplicationNumberInput (6+ digits)                          │    │
│  │  │                                                                    │    │
│  │  ├─ errors.py (ApiError utility class)                               │    │
│  │  │   ├─ create() - Standard error responses                         │    │
│  │  │   ├─ from_http_error()                                           │    │
│  │  │   ├─ not_found()                                                 │    │
│  │  │   └─ validation_error()                                          │    │
│  │  │                                                                    │    │
│  │  └─ is_error(response) - Check if dict is error                     │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                    │                                            │
│  ┌────────────────────────────────┴──────────────────────────────────────┐    │
│  │                   HTTP Client Layer (httpx)                           │    │
│  │                                                                        │    │
│  │  ┌──────────────────────┐         ┌──────────────────────┐           │    │
│  │  │  PpubsClient         │         │  ApiUsptoClient      │           │    │
│  │  │  (ppubs_uspto_gov.py)│         │  (api_uspto_gov.py)  │           │    │
│  │  │                      │         │                      │           │    │
│  │  │  • Session Mgmt      │         │  • API Key Auth      │           │    │
│  │  │    (30-min cache)    │         │  • Query Builder     │           │    │
│  │  │  • Retry Logic       │         │  • Retry Logic       │           │    │
│  │  │  • Rate Limiting     │         │  • Error Handling    │           │    │
│  │  │  • PDF Pipeline      │         │  • GET/POST Support  │           │    │
│  │  │  • HTTP/2 Support    │         │  • HTTP/2 Support    │           │    │
│  │  └──────────────────────┘         └──────────────────────┘           │    │
│  │                                                                        │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                    │                                            │
│  ┌────────────────────────────────┴──────────────────────────────────────┐    │
│  │                 Configuration & Utilities                             │    │
│  │                                                                        │    │
│  │  ├─ config.py                                                         │    │
│  │  │   ├─ USPTO_API_KEY (from .env)                                    │    │
│  │  │   ├─ LOG_LEVEL, REQUEST_TIMEOUT, MAX_RETRIES                      │    │
│  │  │   ├─ SESSION_EXPIRY_MINUTES, ENABLE_CACHING                       │    │
│  │  │   └─ get_log_level(), validate()                                  │    │
│  │  │                                                                    │    │
│  │  ├─ constants.py (magic string elimination)                          │    │
│  │  │   ├─ Sources (USPAT, US-PGPUB, USOCR)                             │    │
│  │  │   ├─ Fields (guid, type, error, message, etc.)                    │    │
│  │  │   ├─ Defaults (pagination, limits, timeouts)                      │    │
│  │  │   └─ Other enums (Operators, PrintStatus, HTTPMethods)            │    │
│  │  │                                                                    │    │
│  │  └─ logging.py (LoggingTransport)                                     │    │
│  │      ├─ Custom httpx async transport                                 │    │
│  │      ├─ Logs all requests/responses                                  │    │
│  │      └─ Pretty-prints JSON bodies                                    │    │
│  │                                                                        │    │
│  └────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                    ┌───────────────────┴───────────────────┐
                    ▼                                       ▼
    ┌──────────────────────────────┐   ┌──────────────────────────────┐
    │   ppubs.uspto.gov API        │   │   api.uspto.gov API          │
    │                              │   │                              │
    │ • POST /api/users/me/session │   │ • GET /api/v1/patent/apps... │
    │ • POST /api/searches/counts  │   │ • GET /api/v1/patent/apps... │
    │ • POST /api/searches/...     │   │ • POST /api/v1/patent/apps...│
    │ • GET /api/patents/highlight │   │ • GET /api/v1/datasets/...   │
    │ • POST /api/print/...        │   │ • POST /api/v1/patent/status │
    │                              │   │                              │
    │ (Full-text docs, PDFs)       │   │ (Metadata, transactions)     │
    └──────────────────────────────┘   └──────────────────────────────┘
```

---

## Request Flow Diagram

### Typical Request Flow for a Tool

```
1. Claude Desktop User Query
                  │
                  ▼
2. MCP Protocol Parses Tool Call
   (patents.py @mcp.tool() decorator)
                  │
                  ▼
3. Tool Function Invoked (async)
   ├─ Input validation (validation.py)
   ├─ Parameter cleaning & normalization
   └─ Error check before API call
                  │
                  ▼
4. Client Method Call
   ├─ PpubsClient.run_query() or similar
   └─ ApiUsptoClient.make_request() or similar
                  │
                  ▼
5. Retry Logic (tenacity decorator)
   ├─ Exponential backoff
   └─ Max 3 attempts (configurable)
                  │
                  ▼
6. HTTP Request
   ├─ LoggingTransport (logs request/response)
   ├─ httpx HTTP/2 async client
   └─ USPTO API endpoint
                  │
                  ▼
7. Handle Response
   ├─ Check status code
   ├─ Refresh session if 403 (ppubs only)
   ├─ Wait if rate limited 429
   └─ Parse JSON
                  │
                  ▼
8. Error Handling
   ├─ If error: ApiError.create() or variants
   └─ Return structured error dict
                  │
                  ▼
9. Return to Tool
   ├─ Success: Dict with data
   └─ Failure: Dict with error flag
                  │
                  ▼
10. Return to MCP Client
    └─ Claude Desktop displays results
```

---

## Data Model - Response Structures

### Success Response Example (ppubs_search_patents)
```json
{
  "numFound": 1,
  "patents": [
    {
      "guid": "US-9876543-B2",
      "type": "USPAT",
      "docNumber": "9876543",
      "title": "Patent Title",
      "date_publ": "2025-01-15",
      "abstract": "Patent abstract...",
      "snippets": "Highlighted snippets...",
      "imageLocation": "/path/to/images",
      "pageCount": 42
    }
  ]
}
```

### Success Response Example (get_app metadata)
```json
{
  "applicationNumber": "14412875",
  "status": "issued",
  "patentNumber": "9876543",
  "inventorCount": 3,
  "publicationDate": "2025-01-15",
  "filingDate": "2023-01-20",
  "meta": {
    "total": 1,
    "pageCount": 25,
    "pageSize": 10
  }
}
```

### Error Response (Standardized)
```json
{
  "error": true,
  "message": "Patent 999 not found",
  "status_code": 404,
  "error_code": "NOT_FOUND",
  "details": {
    "field": "patent_number"
  }
}
```

---

## Data Flow Between Components

```
Input Validation Chain:
  User Input 
    ↓
  Pydantic Models (validation.py)
    ├─ PatentNumberInput
    ├─ ApplicationNumberInput
    └─ etc.
    ↓
  validate_patent_number() / validate_app_number()
    ↓
  Cleaned & Validated Value or ValueError

Error Handling Chain:
  Any Error in Tool
    ↓
  ApiError.create() / .from_exception() / .not_found()
    ↓
  Standardized Error Dict {error: true, message: "...", ...}
    ↓
  is_error() check
    ↓
  Return to Caller

HTTP Request Chain:
  Tool calls Client Method
    ↓
  Client prepares request (headers, params, body)
    ↓
  LoggingTransport logs request
    ↓
  httpx sends request to USPTO API
    ↓
  USPTO returns response
    ↓
  LoggingTransport logs response
    ↓
  Client handles status codes
    ↓
  Client parses JSON or returns error
    ↓
  Tool processes and returns to MCP
    ↓
  Claude Desktop displays result
```

---

## Configuration & Dependency Graph

```
┌─────────────────────────────────────────────────────────────────────┐
│                   Environment Variables (.env)                      │
├─────────────────────────────────────────────────────────────────────┤
│  ├─ USPTO_API_KEY                                                   │
│  ├─ PPUBS_BASE_URL, API_BASE_URL                                    │
│  ├─ LOG_LEVEL, REQUEST_TIMEOUT, MAX_RETRIES                         │
│  ├─ RETRY_DELAY, RETRY_MIN_WAIT, RETRY_MAX_WAIT                     │
│  ├─ SESSION_EXPIRY_MINUTES, ENABLE_CACHING                          │
│  └─ USER_AGENT                                                       │
└──────────────┬──────────────────────────────────────────────────────┘
               │
               ▼
   ┌──────────────────────────┐
   │   config.py (Config)     │
   └──────────────┬───────────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
  ┌───────────────┐   ┌────────────────────┐
  │ patents.py    │   │ constants.py       │
  │ (creates      │   │ (Defaults, etc.)   │
  │  clients)     │   └────────────────────┘
  └───────┬───────┘
          │
    ┌─────┴─────┐
    ▼           ▼
┌─────────┐  ┌─────────────┐
│ Ppubs   │  │ ApiUspto    │
│ Client  │  │ Client      │
└────┬────┘  └─────┬───────┘
     │             │
     ├─────┬───────┤
     ▼     ▼       ▼
  errors.py, validation.py, logging.py

Dependencies:
  httpx (2.0+) - Async HTTP client
  mcp[cli] (1.3.0+) - Model Context Protocol
  pydantic (2.0+) - Data validation
  tenacity (8.0+) - Retry logic
  python-dotenv (1.0+) - Environment loading
  h2 (4.2+) - HTTP/2 support
```

---

## Code Organization Summary

```
patent_mcp_server/
├── src/patent_mcp_server/         [Source Code]
│   ├── patents.py                 [23 Tools + Main Entry]
│   ├── config.py                  [Configuration]
│   ├── constants.py               [Constants & Enums]
│   ├── __main__.py                [Module Entry Point]
│   ├── json/
│   │   └── search_query.json      [ppubs Search Template]
│   ├── uspto/                     [API Clients]
│   │   ├── ppubs_uspto_gov.py     [ppubs.uspto.gov Client]
│   │   └── api_uspto_gov.py       [api.uspto.gov Client]
│   └── util/                      [Utilities]
│       ├── errors.py              [Error Handling]
│       ├── validation.py          [Input Validation]
│       └── logging.py             [Custom Logging]
│
├── test/                          [Tests]
│   ├── test_tools_pytest.py       [Modern pytest suite (RECOMMENDED)]
│   ├── test_tools.py              [Legacy test runner]
│   ├── test_patents.py            [Direct HTTP tests]
│   └── test_results/              [Test outputs & artifacts]
│
├── pyproject.toml                 [Project Config]
├── pytest.ini                     [Pytest Config]
└── README.md                      [Documentation]

Key Metrics:
  • 13 Python source files
  • ~2,000 lines of code
  • 23 MCP tools
  • 30+ API endpoints
  • 3 comprehensive test suites
```

---

## Tool Categories & Their Purposes

### ppubs.uspto.gov Tools (Full-Text Search & PDFs)
```
Search & Discovery:
  • ppubs_search_patents
  • ppubs_search_applications

Document Access:
  • ppubs_get_full_document (by GUID)
  • ppubs_get_patent_by_number (by Number)

PDF Downloads:
  • ppubs_download_patent_pdf (multi-step process)
    ├─ Search for patent
    ├─ Request PDF generation
    ├─ Poll for completion
    └─ Download PDF
```

### api.uspto.gov Tools (Metadata & Detail)
```
Single Application Lookups (11 tools):
  • get_app
  • get_app_metadata
  • get_app_adjustment
  • get_app_assignment
  • get_app_attorney
  • get_app_continuity
  • get_app_foreign_priority
  • get_app_transactions
  • get_app_documents
  • get_app_associated_documents

Search & Download (4 tools in GET and POST variants):
  • search_applications (GET/POST variants)
  • download_applications (GET/POST variants)

Reference Data (3 tools):
  • get_status_codes (GET/POST variants)
  • search_datasets
  • get_dataset_product
```

---

## Performance & Resilience Features

```
Resilience:
  ├─ Automatic Retry
  │   ├─ Exponential backoff (2-10 seconds)
  │   ├─ Max 3 attempts (configurable)
  │   └─ Retries on: Timeout, Network Error
  │
  ├─ Session Caching (ppubs)
  │   ├─ 30-minute expiry (configurable)
  │   ├─ Automatic refresh on 403
  │   └─ Single session per client instance
  │
  ├─ Rate Limit Handling
  │   ├─ Detects 429 responses
  │   └─ Respects Retry-After header
  │
  └─ Error Handling
      ├─ Structured error responses
      ├─ Validation before API calls
      └─ Graceful fallback for missing data

Performance:
  ├─ HTTP/2 (async client with h2 support)
  ├─ Async/await concurrency
  ├─ Connection pooling (httpx)
  ├─ Session reuse (30-minute cache)
  └─ Minimal latency on cache hits

Observability:
  ├─ Configurable log levels (DEBUG, INFO, WARNING, ERROR)
  ├─ HTTP request/response logging
  ├─ JSON body pretty-printing
  └─ Timing information in test runs
```

---

## Integration Points Summary

### With Claude Desktop
- **Transport**: stdio (standard input/output)
- **Protocol**: MCP (Model Context Protocol)
- **Tool Discovery**: @mcp.tool() decorators
- **Documentation**: Docstrings become tool descriptions
- **Authentication**: Via environment variables

### With USPTO APIs
- **ppubs.uspto.gov**:
  - Session-based authentication
  - Case ID for search operations
  - Multi-step PDF download process
  
- **api.uspto.gov**:
  - API Key authentication (X-API-KEY header)
  - RESTful endpoint structure
  - JSON request/response format

### With External Libraries
- **httpx**: Async HTTP client for API calls
- **pydantic**: Input validation and data models
- **tenacity**: Retry logic with exponential backoff
- **mcp[cli]**: Model Context Protocol framework
- **python-dotenv**: Environment configuration

