# USPTO Patent MCP Server

A [FastMCP server](https://github.com/modelcontextprotocol/python-sdk/tree/main/src/mcp/server/fastmcp) for accessing United States Patent and Trademark Office (USPTO) patent and patent application data through the [Patent Public Search](https://www.uspto.gov/patents/search/patent-public-search) API, the [Open Data Portal (ODP) API](https://data.uspto.gov/home), and [Google Patents Public Datasets](https://cloud.google.com/blog/topics/public-datasets/google-patents-public-datasets-connecting-public-paid-and-private-patent-data) via BigQuery. Using this server, Claude Desktop can pull data from the USPTO APIs or search through 90M+ patent publications from 17+ countries via Google's BigQuery:

![Screen Capture of Cladue Desktop using Patents MCP Server](screencap.gif)

For an introduction to MCP servers see [Introducing the Model Context Protcol](https://www.anthropic.com/news/model-context-protocol).

Special thanks to [Parker Hancock](https://github.com/parkerhancock), author of the amazing [Patent Client project](https://github.com/parkerhancock/patent_client), for [blazing the trail](https://github.com/parkerhancock/patent_client/issues/63) to understanding of the string of requests and responses needed to pull data through the Public Search API.

## Features

This server provides tools for:

1. **Patent Search** - Search for patents and patent applications across USPTO and Google Patents databases
2. **Full Text Documents** - Get complete text of patents including claims, description, etc.
3. **PDF Downloads** - Download patents as PDF files (Claude Desktop doesn't support this as a client currently)
4. **Metadata** - Access patent bibliographic information, assignments, and litigation data
5. **Google Patents Integration** - Access 90M+ patent publications from 17+ countries via BigQuery
6. **Advanced Search** - Search by inventor, assignee, CPC classification, and more

## API Sources

This server interacts with three patent data sources:

- **ppubs.uspto.gov** - For full text document access, PDF downloads, and advanced search
- **api.uspto.gov** - For metadata, continuity information, transactions, and assignments
- **Google Patents Public Datasets (BigQuery)** - For comprehensive patent search across 90M+ publications from 17+ countries

## Prerequisites

- **Python 3.10 or higher**
- Claude Desktop (for integration). Other models and MCP clients have not been tested.
- For Patent Public Search requests, no API Key is required, but [there are rate limits](https://github.com/parkerhancock/patent_client/issues/143#issuecomment-2078051755). This API is not meant for bulk downloads.
- For ODP API requests, a USPTO ODP API Key (see below).
- **For Google Patents**: A Google Cloud account with BigQuery API enabled (see Google Cloud Setup below).
- [UV](https://docs.astral.sh/uv/) for python version and dependency management.

If you're a python developer, but still unfamiliar with uv, you're in for a treat. It's faster and easier than having a separate python version manager (like pyenv) and setting up, activating, and maintaining virtual environments with venv and pip.

If you don't already have uv installed, `curl -LsSf https://astral.sh/uv/install.sh | sh` should do the trick.

## Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/riemannzeta/patent_mcp_server
   cd patent_mcp_server
   ```

2. Install dependencies with uv:

   ```bash
   uv sync
   ```

   If installed correctly, then:

    ```bash
    uv run patent-mcp-server
    ```

   Should write:

    ```bash
    INFO     Starting USPTO Patent MCP server with stdio transport
    ```
    
   to the console. With an API key installed in the environment and Claude Desktop configured, the patents MCP server is ready.

## API Key Setup

### USPTO API Key

To use the api.uspto.gov tools, you need to obtain an Open Data Portal (ODP) API key:

1. Visit [USPTO's Getting Started page](https://data.uspto.gov/apis/getting-started) and follow the instructions to request an API key if you don't already have one.

2. Create a `.env` file in the patent_mcp_server directory with your API key:
   ```bash
   USPTO_API_KEY=your_actual_key_here
   ```
   You don't need quotes around your key. The ppubs tools will run without this API key, but the API key is required for the api.uspto.gov tools.

### Google Cloud Setup (for Google Patents)

To use Google Patents Public Datasets, you need to set up Google Cloud credentials:

1. **Create a Google Cloud Project**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Note your Project ID

2. **Enable BigQuery API**:
   - In your project, go to "APIs & Services" > "Library"
   - Search for "BigQuery API" and enable it

3. **Create Service Account Credentials**:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "Service Account"
   - Give it a name (e.g., "patent-mcp-bigquery")
   - Grant it the "BigQuery User" role
   - Click "Done"
   - Click on the created service account
   - Go to "Keys" tab > "Add Key" > "Create new key"
   - Choose JSON format and download the key file

4. **Configure Environment Variables**:
   Add to your `.env` file:
   ```bash
   GOOGLE_CLOUD_PROJECT=your-project-id
   GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account-key.json
   ```

**Cost Information**: Google BigQuery provides 1TB of free queries per month. After that, queries cost $5 per TB. Patent queries are typically small and efficient. See [BigQuery pricing](https://cloud.google.com/bigquery/pricing) for details.

## Configuration

The server can be configured using environment variables in your `.env` file. All settings are optional with sensible defaults:

```bash
# API Keys
USPTO_API_KEY=your_key_here

# Google Cloud / BigQuery
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
BIGQUERY_DATASET=patents-public-data:patents
BIGQUERY_LOCATION=US
BIGQUERY_QUERY_TIMEOUT=60
BIGQUERY_MAX_RESULTS=1000

# Logging
LOG_LEVEL=INFO  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

# HTTP Settings
REQUEST_TIMEOUT=30.0  # Request timeout in seconds
MAX_RETRIES=3         # Maximum number of retry attempts for failed requests
RETRY_MIN_WAIT=2      # Minimum wait time between retries (seconds)
RETRY_MAX_WAIT=10     # Maximum wait time between retries (seconds)

# Session Management
SESSION_EXPIRY_MINUTES=30  # How long to cache ppubs sessions
ENABLE_CACHING=true        # Enable/disable session caching

# API Endpoints (usually don't need to change)
PPUBS_BASE_URL=https://ppubs.uspto.gov
API_BASE_URL=https://api.uspto.gov
```

## Claude Desktop Configuration

To integrate this MCP server with Claude Desktop:

1. Update your Claude Desktop configuration file (`claude_desktop_config.json`):
   ```json
    {
      "mcpServers": {
        "patents": {
          "command": "uv",
          "args": [
            "--directory",
            "/Users/username/patent_mcp_server",
            "run",
            "patent-mcp-server"
          ]
        }
      }
    }
   ```
   You can find `claude_desktop_config.json` on a mac by opening the Claude Desktop app, opening Settings (from the Claude menu or by Command + ' on the keyboard), clicking "Developer" in in the sidebar, and "Edit Config."

2. Replace `/Users/username/patent_mcp_server` with the actual path to your patent_mcp_server directory if that's not where it was cloned. (If you're on a mac, this may mean simply replacing `username` with your username.)

When integrated with Claude Desktop, the server will be automatically started when needed and doesn't need to be run separately. The server uses stdio transport for communication with Claude Desktop or other MCP clients running on the same host.

## Available Functions

The server provides the following functions to interact with USPTO data. Note that the Claude Desktop client does not fully support all of these tools. For example, Claude Desktop does not at present allow for download of PDFs.

### Public Patent Search (ppubs.uspto.gov)
- `ppubs_search_patents` - Search for granted patents in USPTO Public Search
- `ppubs_search_applications` - Search for published patent applications in USPTO Public Search
- `ppubs_get_full_document` - Get full patent document details by GUID from ppubs.uspto.gov 
- `ppubs_get_patent_by_number` - Get a granted patent's full text by number from ppubs.uspto.gov
- `ppubs_download_patent_pdf` - Download a granted patent as PDF from ppubs.uspto.gov (not currently supported by Claude Desktop)

### Open Data Portal API (api.uspto.gov)
- `get_app(app_num)` - Get basic patent application data
- `search_applications(...)` - Search for patent applications using query parameters
- `download_applications(...)` - Download patent applications using query parameters
- `get_app_metadata(app_num)` - Get application metadata
- `get_app_adjustment(app_num)` - Get patent term adjustment data
- `get_app_assignment(app_num)` - Get assignment data
- `get_app_attorney(app_num)` - Get attorney/agent information
- `get_app_continuity(app_num)` - Get continuity data
- `get_app_foreign_priority(app_num)` - Get foreign priority claims
- `get_app_transactions(app_num)` - Get transaction history
- `get_app_documents(app_num)` - Get document details
- `get_app_associated_documents(app_num)` - Get associated documents
- `get_status_codes(...)` - Search for status codes
- `search_datasets(...)` - Search bulk dataset products
- `get_dataset_product(...)` - Get a specific product by its identifier

### Google Patents Public Datasets (BigQuery)
- `google_search_patents(query, country, limit)` - Search patents by text in title/abstract across 90M+ publications
- `google_get_patent(publication_number)` - Get complete patent details by publication number
- `google_get_patent_claims(publication_number)` - Get all claims for a patent
- `google_get_patent_description(publication_number)` - Get full patent description/specification
- `google_search_by_inventor(inventor_name, country, limit)` - Find patents by inventor name
- `google_search_by_assignee(assignee_name, country, limit)` - Find patents by company/assignee
- `google_search_by_cpc(cpc_code, country, limit)` - Search patents by CPC classification code

**Supported Countries**: US, EP (European Patent Office), WO (WIPO/PCT), JP (Japan), CN (China), KR (South Korea), GB (Great Britain), DE (Germany), FR (France), CA (Canada), AU (Australia)

**Note**: Google Patents tools require Google Cloud credentials (see Google Cloud Setup above).

Refer to the function docstrings in the code for detailed parameter information.

## Recent Improvements (v0.2.2)

This release includes significant improvements to code quality, reliability, and maintainability:

### Architecture & Code Quality
- **Centralized Configuration** - All settings now managed through environment variables with sensible defaults
- **Constants Module** - Magic strings extracted to a dedicated constants module for consistency
- **Error Handling** - Standardized error responses across all endpoints using `ApiError` utility class
- **Code Deduplication** - Extracted common patent search logic to eliminate ~80 lines of duplicate code
- **Input Validation** - Automatic validation and sanitization of patent/application numbers using Pydantic

### Reliability & Performance
- **Retry Logic** - Exponential backoff retry mechanism for network errors using tenacity
- **Session Caching** - ppubs.uspto.gov sessions cached for 30 minutes (configurable) to reduce overhead
- **Resource Management** - Proper cleanup of HTTP clients with context managers and shutdown handlers
- **Type Hints** - Comprehensive type annotations throughout the codebase

### Developer Experience
- **pytest Framework** - Modern test framework with async support replacing custom test runner
- **Python 3.10+ Support** - Lowered requirement from 3.13 to 3.10 for broader compatibility
- **Better Logging** - Configurable log levels via environment variables
- **Development Tools** - Added pytest, pytest-asyncio, and pytest-cov to dev dependencies

## Testing

The `/test/` directory contains test suites for validating the MCP server functionality:

- **`test_tools_pytest.py`** - Modern pytest-based test suite for all MCP tools (recommended)
- **`test_tools.py`** - Legacy test runner (still functional)
- **`test_patents.py`** - Direct HTTP request tests for debugging

Test results in JSON and PDF format are stored in the `/test/test_results` subdirectory.

### Running Tests

```bash
# Run all tests with pytest (recommended)
uv run pytest test/test_tools_pytest.py -v

# Run excluding slow tests (like PDF downloads)
uv run pytest test/test_tools_pytest.py -v -m "not slow"

# Run with coverage report
uv run pytest test/test_tools_pytest.py --cov=patent_mcp_server

# Run legacy test suite
uv run test/test_tools.py
```

### Development

To install development dependencies:

```bash
uv sync --dev
```

## License

MIT
