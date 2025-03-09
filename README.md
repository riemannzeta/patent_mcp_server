# USPTO Patent MCP Server

This repository contains a FastMCP server implementation for accessing USPTO (United States Patent and Trademark Office) patent application data through their [Open Data Portal (ODP) API](https://data.uspto.gov/home). Using this server, Claude Desktop can pull data from the USPTO using any of the available ODP API endpoints:

![Screen Capture of Cladue Desktop using Patents MCP Server](screencap.gif)

For an introduction to MCP servers see [Introducing the Model Context Protcol](https://www.anthropic.com/news/model-context-protocol).

## Overview

The USPTO Patent MCP Server provides a convenient interface for interacting with USPTO's patent application data. It implements various endpoints for searching and retrieving detailed information about patent applications, including:

- Basic application data
- Metadata
- Term adjustments
- Assignments
- Attorney/agent information
- Continuity data
- Foreign priority claims
- Transactions

## Prerequisites

- USPTO ODP API Key (see below)
- Claude Desktop (for integration)
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
uv run patents.py
```

Should run silently. With an API key installed in the environment and Claude Desktop configured, the patents MCP server is ready.

## API Key Setup

To use the USPTO APIs, you need to obtain an Open Data Portal (ODP) API key:

1. Visit [USPTO's Getting Started page](https://data.uspto.gov/apis/getting-started) and follow the instructions to request an API key if you don't already have one.

2. Create a `.env` file in the patent_mcp_server directory with the following content:
   ```
   PATENTS_MCP_SERVER_ODP_API_KEY=<your_key_here>
   ```
You don't need quotes or the < > brackets around your key.

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
           "patents.py"
         ]
       }
     }
   }
   ```

2. Replace `/Users/username/patent_mcp_server` with the actual path to your patent_mcp_server directory if that's not where it was cloned.
3. Replace `username` with your actual username

When integrated with Claude Desktop, the server will be automatically started when needed.

## Available Functions

The server provides the following functions to interact with USPTO data. Note that not all have been thoroughly tested!

- `get_app(app_num)` - Get basic patent application data
- `search_applications(...)` - Search for patent applications using various parameters
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
- `search_datasets(...)` - Search bulk datasets

Refer to the function docstrings in the code for detailed parameter information.

## License

MIT

