# CLAUDE.md - Development Guidelines for USPTO Patent MCP Server

This file provides guidance for Claude Code and other AI assistants working on this project.

## Project Overview

This is a Model Context Protocol (MCP) server that provides access to USPTO patent and trademark data through multiple APIs. The server is built with FastMCP and uses async/await patterns throughout. Published to PyPI as `patent-mcp-server`.

**Current state (v1.1.0):** 69 registered tools, 48 active, 21 unavailable due to API shutdowns:
- **Active:** PPUBS (5), ODP (12), PTAB (7), TSDR (4), Trademark search/assignments (3), Federal litigation (8 `litigation_*` + 4 revived legacy litigation tools), Utility (5)
- **Unavailable:** PatentsView (14, shut down March 2026), Office Actions (4, decommissioned early 2026), Enriched Citations (3, decommissioned early 2026)

**Federal litigation backend (`courtlistener_client.py`):** CourtListener / RECAP REST API v4 (Free Law Project) at `www.courtlistener.com/api/rest/v4`. Auth via `Authorization: Token <COURTLISTENER_API_KEY>`. Full-text `/search/?type=r|o|rd` works anonymously (lower rate limit); detail endpoints (`/dockets/{id}/`, `/opinions/{id}/`, `/recap-documents/{id}/`) return 401 without a token — the client maps that to `COURTLISTENER_AUTH_REQUIRED` with setup guidance. Pagination is cursor-based (`next`/`previous` surfaced in envelope metadata). Single-document text capped at `LitigationDefaults.MAX_TEXT_CHARS`. PACER fallback (`litigation_get_document(allow_pacer_fetch=True)`) posts to `/recap-fetch/` with `PACER_USERNAME`/`PACER_PASSWORD` (per-page fees); returns `PACER_NOT_CONFIGURED` when creds are absent. The 4 legacy tools (`search_litigation`, `get_litigation_case`, `get_patent_litigation`, `get_party_litigation`) are now live aliases over this client (closes issue #16). Verified live 2026-06-14.

**Trademark backend contracts (verified live 2026-06-10):**
- **tmsearch** (`tmsearch_client.py`): `POST tmsearch.uspto.gov/prod-stage-v1-0-0/tmsearch`, Elasticsearch-style body, non-standard response envelope (`hits.totalValue`, hit `source`/`id`). No key; behind AWS WAF (currently permissive — `TMSEARCH_WAF_TOKEN` supported as escape hatch). Class filters need zero-padded 3-digit terms ("025").
- **Assignments** (`tm_assignment_client.py`): `POST assignmentcenter.uspto.gov/ipas/search/api/v2/public/trademark/exportTradeMarkData` with `searchCriteria` list; no key. The legacy assignment-api.uspto.gov died with the Developer Hub on June 5, 2026.
- **TSDR** (`tsdr_client.py`): requires a TSDR-specific key from account.uspto.gov/profile/api-manager — the ODP key passes the gateway but 404s on the backend (`BACKEND RESPONSE STATUS: 404`); the client detects this and explains. Status uses `/info` + `Accept: application/json`; the document list at `/casedocs/{caseid}/info` is XML-ONLY (406 on JSON Accept) and is parsed via `_parse_document_list_xml`. Binary bundles are capped at `TrademarkDefaults.MAX_BINARY_BYTES` (full wrappers can exceed 10 MB) — filter by `document_type`/date. All endpoints verified live 2026-06-10 with a real TSDR key.

## Critical Rules

### Before Committing Changes

**IMPORTANT: Never commit and push changes without ensuring all tests pass.**

```bash
uv run pytest
# Expected: ~359 passed, ~54 deselected (integration tests skipped by default)
```

If tests fail, fix them before committing. Do not skip or delete failing tests unless the functionality has been intentionally removed.

### Playbooks

The release workflow and the decommissioned-API playbook live as skills in `.claude/skills/` (`release`, `decommission-api`) — invoke the matching skill when publishing a version or handling a USPTO API shutdown.

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

## Configuration

Environment variables are loaded from `.env` file — see `config.py` for all options and `.env.example` for the list.

## Reminders

1. **Always run tests before committing**
2. Keep docstrings up to date — especially "USE THIS TOOL WHEN" guidance
3. Don't introduce new dependencies without good reason
4. When updating README.md, keep version history and tool counts current
5. Update both `pyproject.toml` version AND `config.py` USER_AGENT on version bumps
