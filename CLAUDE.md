# CLAUDE.md - Development Guidelines for USPTO Patent MCP Server

This file provides guidance for Claude Code and other AI assistants working on this project.

## Project Overview

This is a Model Context Protocol (MCP) server that provides access to USPTO patent data through multiple APIs. The server is built with FastMCP and uses async/await patterns throughout.

## Critical Rules

### Before Committing Changes

**IMPORTANT: Never commit and push changes without ensuring all tests pass.**

Before any commit:
```bash
# Run the full test suite
uv run pytest

# Expected output: All tests should pass (integration tests are skipped by default)
# Example: "150 passed, 36 deselected"
```

If tests fail:
1. Fix the failing tests before committing
2. Do not skip or delete failing tests unless the functionality has been intentionally removed
3. Update tests when function signatures change

### Test Organization

- **Unit tests** (`test/unit/`): Run by default, mock external APIs
- **Integration tests** (`test/test_tools.py`, `test/test_tools_pytest.py`): Require network access, skipped by default

To run integration tests:
```bash
uv run pytest -m integration
```

## Project Structure

```
src/patent_mcp_server/
├── patents.py              # Main server file with MCP tools, resources, and prompts
├── config.py               # Configuration management (environment variables)
├── constants.py            # Constants and enumerations
├── prompts.py              # Workflow prompt templates
├── resources.py            # Static resource data (CPC codes, status codes)
├── util/
│   ├── response.py         # Response normalization utilities
│   ├── errors.py           # Error handling utilities
│   ├── validation.py       # Input validation with Pydantic
│   └── logging.py          # Logging configuration
├── uspto/
│   ├── ppubs_uspto_gov.py  # Patent Public Search client
│   ├── api_uspto_gov.py    # Open Data Portal client
│   ├── ptab_client.py      # PTAB proceedings client
│   ├── office_action_client.py
│   ├── enriched_citation_client.py
│   └── litigation_client.py
└── patentsview/
    └── patentsview_client.py
```

## Code Conventions

### Function Naming

- **PPUBS tools**: `ppubs_*` (e.g., `ppubs_search_patents`)
- **ODP tools**: `odp_*` (e.g., `odp_get_application`)
- **PTAB tools**: `ptab_*` (e.g., `ptab_search_proceedings`)
- **PatentsView tools**: `patentsview_*` (e.g., `patentsview_search_patents`)

### Parameter Naming

- Use `query` not `q` for search queries
- Use `app_num` for application numbers
- Use `patent_number` for patent numbers
- Use `offset` and `limit` for pagination

### Error Handling

All tools should return a dictionary with consistent structure:
```python
# Success
{"success": True, "results": [...], "total": N, ...}

# Error
{"error": True, "message": "Error description", "error_code": "CODE"}
```

Use `ApiError.create()` for error responses.

### Async Patterns

All API clients use async/await:
```python
async def tool_name(...) -> Dict[str, Any]:
    async with SomeClient() as client:
        return await client.method(...)
```

## Testing Guidelines

### Writing Unit Tests

- Mock external HTTP calls using `unittest.mock`
- Use `@pytest.mark.unit` marker
- Test files go in `test/unit/`

### Writing Integration Tests

- Use `@pytest.mark.integration` marker
- These tests hit real APIs and require network access
- Place in `test/test_tools.py` or `test/test_tools_pytest.py`

### Test Fixtures

Common fixtures are in `test/fixtures/`:
- `ppubs_responses.py` - Mock PPUBS API responses
- Similar fixtures exist for other APIs

## Dependencies

Managed via `pyproject.toml`. Key dependencies:
- `mcp[cli]` - FastMCP server framework
- `httpx` - Async HTTP client
- `pydantic` - Data validation
- `tenacity` - Retry logic

To add a dependency:
```bash
uv add package-name
```

## Configuration

Environment variables are loaded from `.env` file:
- `USPTO_API_KEY` - Required for most tools
- `PATENTSVIEW_API_KEY` - Optional, for PatentsView tools
- `LOG_LEVEL` - Logging verbosity

See `config.py` for all options.

## Common Tasks

### Adding a New Tool

1. Add the function to `patents.py` with `@mcp.tool()` decorator
2. Follow naming conventions (`prefix_action`)
3. Add comprehensive docstring with "USE THIS TOOL WHEN" guidance
4. Add unit tests in `test/unit/`
5. Run tests before committing

### Updating an Existing Tool

1. Update the function signature
2. Update docstring if behavior changed
3. Update tests to match new signature
4. Run all tests before committing

### Running the Server Locally

```bash
# Start the server
uv run patent-mcp-server

# Run in development mode with debug logging
LOG_LEVEL=DEBUG uv run patent-mcp-server
```

## Version History

- **v0.5.0** - USPTO-only focus, renamed ODP tools with `odp_` prefix
- **v0.3.0** - Added PTAB, PatentsView, Office Actions, Citations, Litigation APIs
- **v0.2.2** - Centralized config, error handling, validation

## Reminders

1. **Always run tests before committing**
2. Keep docstrings up to date
3. Use consistent error handling
4. Follow async patterns
5. Don't introduce new dependencies without good reason
