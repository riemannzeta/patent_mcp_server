# USPTO Patent MCP Server

A [FastMCP server](https://github.com/modelcontextprotocol/python-sdk/tree/main/src/mcp/server/fastmcp) for accessing United States Patent and Trademark Office (USPTO) patent and patent application data through the [Patent Public Search](https://www.uspto.gov/patents/search/patent-public-search) API and the [Open Data Portal (ODP) API](https://data.uspto.gov/home). Using this server, Claude Desktop can pull data from the USPTO using either the Public Search API (the backend for the Patent Center) or the ODP APIs:

![Screen Capture of Cladue Desktop using Patents MCP Server](screencap.gif)

For an introduction to MCP servers see [Introducing the Model Context Protcol](https://www.anthropic.com/news/model-context-protocol).

Special thanks to [Parker Hancock](https://github.com/parkerhancock), author of the amazing [Patent Client project](https://github.com/parkerhancock/patent_client), for [blazing the trail](https://github.com/parkerhancock/patent_client/issues/63) to understanding of the string of requests and responses needed to pull data through the Public Search API.

## Features

This server provides tools for:

1. **Patent Search** - Search for patents and patent applications
2. **Full Text Documents** - Get complete text of patents including claims, description, etc.
3. **PDF Downloads** - Download patents as PDF files. (But Claude Desktop doesn't support this as a client currently.)
4. **Metadata** - Access patent bibliographic information, assignments, and litigation data

## API Sources

This server interacts with two USPTO sources:

- **ppubs.uspto.gov** - For full text document access, PDF downloads, and advanced search
- **api.uspto.gov** - For metadata, continuity information, transactions, and assignments

## Prerequisites

- Claude Desktop (for integration). Other models and MCP clients have not been tested.
- For Patent Public Search requests, no API Key is required, but [there are rate limits](https://github.com/parkerhancock/patent_client/issues/143#issuecomment-2078051755). This API is not meant for bulk downloads.
- For ODP API requests, a USPTO ODP API Key (see below).
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

To use the api.uspto.gov tools, you need to obtain an Open Data Portal (ODP) API key:

1. Visit [USPTO's Getting Started page](https://data.uspto.gov/apis/getting-started) and follow the instructions to request an API key if you don't already have one.

2. Create a `.env` file in the patent_mcp_server directory with the following content:
   ```
   USPTO_API_KEY=<your_key_here>
   ```
You don't need quotes or the < > brackets around your key. The ppubs tools will run without this API key, but the API key is required for the api tools.

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

Refer to the function docstrings in the code for detailed parameter information.

## Testing

The `/test/` directory contains a couple of scripts for testing. `test_patents.py` includes a few tests of direct HTTP requests to the ppubs.uspto.gov and api.uspto.gov endpoints. `test_tools.py` includes a complete set of tests for each tool available to the MCP server. Test results in JSON and PDF format are stored in the `/test/test_results` subdirectory.

To execute a test, run `uv run test/test_tools.py` from the project root directory.

## License

MIT
