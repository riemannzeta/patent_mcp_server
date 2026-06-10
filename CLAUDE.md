# CLAUDE.md - Development Guidelines for USPTO Patent MCP Server

This file provides guidance for Claude Code and other AI assistants working on this project.

## Project Overview

This is a Model Context Protocol (MCP) server that provides access to USPTO patent and trademark data through multiple APIs. The server is built with FastMCP and uses async/await patterns throughout. Published to PyPI as `patent-mcp-server`.

**Current state (v1.0.0):** 60 registered tools, 35 active, 25 unavailable due to API shutdowns:
- **Active:** PPUBS (5), ODP (12), PTAB (7), TSDR (3), Trademark search/assignments (3), Utility (5)
- **Unavailable:** PatentsView (14, shut down March 2026), Office Actions (4, decommissioned early 2026), Enriched Citations (3, decommissioned early 2026), Litigation (4, not offered on ODP — issue #16)

**Unverified live contracts (verify when network access is available):** the trademark search client (`tmsearch_client.py`) targets the undocumented internal API behind tmsearch.uspto.gov with a best-effort request shape, and the trademark assignment client probes an ODP endpoint with legacy XML fallback. Run `uv run pytest -m integration -k trademark` with a real API key to verify; fix points are documented in each client's module docstring.

## Critical Rules

### Before Committing Changes

**IMPORTANT: Never commit and push changes without ensuring all tests pass.**

```bash
uv run pytest
# Expected: ~336 passed, ~51 deselected (integration tests skipped by default)
```

If tests fail, fix them before committing. Do not skip or delete failing tests unless the functionality has been intentionally removed.

### Release Workflow

When publishing a new version:

1. Run full test suite: `uv run pytest`
2. Bump version in `pyproject.toml` AND `config.py` (USER_AGENT string)
3. Commit and push to `origin/main`
4. Build: `rm -rf dist/ && uv run python -m build`
5. Publish: `uv run twine upload dist/*`

### Handling Decommissioned APIs

When a USPTO API is shut down, follow the established pattern (see PR #14 and the PatentsView shutdown commit):

1. **Keep all tool functions** — don't remove them. Return `API_UNAVAILABLE` with workaround guidance:
   ```python
   return {
       "error": True,
       "message": "Description of what happened and what to use instead...",
       "error_code": "API_UNAVAILABLE",
       "workaround": "Use alternative_tool(args) for this functionality.",
   }
   ```
2. **Update `check_api_status`** in `patents.py` — set `status: "UNAVAILABLE"` with a note
3. **Update `resources.py`** — update `DATA_SOURCES` entry and fix any cross-references pointing to the now-unavailable API
4. **Annotate client code** — add decommission notices to docstrings, keep code intact
5. **Annotate config** — add `# Legacy` comments, remove/downgrade API key warnings in `validate()`
6. **Add unavailability tests** in `test/unit/test_unavailable_tools.py` — both individual tests and entries in the parametrized `TestUnavailableToolErrorStructure`
7. **Skip integration tests** — add `@pytest.mark.skip(reason="...")` to affected integration tests
8. **Bump version** — minor version bump in `pyproject.toml` and `config.py` USER_AGENT

### Test Organization

- **Unit tests** (`test/unit/`): Run by default, mock external APIs
- **Integration tests** (`test/test_tools.py`, `test/test_tools_pytest.py`): Require network access, skipped by default
- **Unavailability tests** (`test/unit/test_unavailable_tools.py`): Verify decommissioned tools return correct error structure

```bash
# Unit tests only (default)
uv run pytest

# Integration tests (requires network + API keys)
uv run pytest -m integration
```

## Project Structure

```
src/patent_mcp_server/
├── patents.py              # Main server file with MCP tools, resources, and prompts
├── config.py               # Configuration management (environment variables)
├── constants.py            # Constants and enumerations
├── prompts.py              # Workflow prompt templates
├── resources.py            # Static resource data (CPC codes, status codes, data sources)
├── util/
│   ├── response.py         # Response normalization utilities
│   ├── errors.py           # Error handling utilities
│   ├── validation.py       # Input validation with Pydantic
│   └── logging.py          # Logging configuration
├── uspto/
│   ├── ppubs_uspto_gov.py  # Patent Public Search client
│   ├── api_uspto_gov.py    # Open Data Portal client
│   ├── ptab_client.py      # PTAB proceedings client
│   ├── tsdr_client.py      # TSDR trademark status/documents client
│   ├── tmsearch_client.py  # Trademark search client (internal API, like PPUBS)
│   ├── tm_assignment_client.py  # Trademark assignments (ODP + legacy fallback)
│   ├── office_action_client.py   # Legacy - decommissioned early 2026
│   ├── enriched_citation_client.py  # Legacy - decommissioned early 2026
│   └── litigation_client.py
└── patentsview/
    └── patentsview_client.py  # Legacy - shut down March 2026
```

## Code Conventions

### Function Naming

- **PPUBS tools**: `ppubs_*` (e.g., `ppubs_search_patents`)
- **ODP tools**: `odp_*` (e.g., `odp_get_application`)
- **PTAB tools**: `ptab_*` (e.g., `ptab_search_proceedings`)
- **TSDR tools**: `tsdr_*` (e.g., `tsdr_get_trademark_status`)
- **Trademark search/assignment tools**: `tm_*` (e.g., `tm_search_trademarks`)
- **PatentsView tools**: `patentsview_*` (legacy, all return API_UNAVAILABLE)

### Parameter Naming

- Use `query` not `q` for search queries
- Use `app_num` for application numbers
- Use `patent_number` for patent numbers
- Use `serial_number` and `registration_number` for trademarks (never `sn`/`rn`)
- Use `offset` and `limit` for pagination

### Error Handling

All tools should return a dictionary with consistent structure:
```python
# Success
{"success": True, "results": [...], "total": N, ...}

# Error
{"error": True, "message": "Error description", "error_code": "CODE"}

# Decommissioned API
{"error": True, "message": "...", "error_code": "API_UNAVAILABLE", "workaround": "..."}
```

Use `ApiError.create()` for error responses.

### Async Patterns

All API clients use async/await:
```python
async def tool_name(...) -> Dict[str, Any]:
    async with SomeClient() as client:
        return await client.method(...)
```

## Dependencies

Managed via `pyproject.toml`. Key dependencies:
- `mcp[cli]` - FastMCP server framework
- `httpx` - Async HTTP client
- `pydantic` - Data validation
- `tenacity` - Retry logic

Dev dependencies include `build` and `twine` for PyPI publishing.

```bash
uv add package-name        # Add dependency
uv sync --dev              # Install dev dependencies
```

## Configuration

Environment variables are loaded from `.env` file:
- `USPTO_API_KEY` - Required for ODP, PTAB, and Litigation tools
- `LOG_LEVEL` - Logging verbosity (default: INFO)

See `config.py` for all options.

## Reminders

1. **Always run tests before committing**
2. Keep docstrings up to date — especially "USE THIS TOOL WHEN" guidance
3. Use consistent error handling patterns
4. Follow async patterns
5. Don't introduce new dependencies without good reason
6. When updating README.md, keep version history and tool counts current
7. Update both `pyproject.toml` version AND `config.py` USER_AGENT on version bumps
