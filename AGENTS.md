# AGENTS.md

Guidance for AI agents (Claude, GPT-class, Cursor, Aider, etc.) contributing issues, PRs, or code review to `patent-mcp-server`.

This file complements [CONTRIBUTING.md](CONTRIBUTING.md), which applies to all contributors. Read both.

## Read CLAUDE.md first

[`CLAUDE.md`](CLAUDE.md) is the authoritative source for project conventions: release workflow, tool naming, error handling, the decommissioned-API pattern, and the rule that all unit tests must pass before any commit. **An agent that hasn't read CLAUDE.md will get patterns subtly wrong** — read it before making changes.

## When filing an issue

Use the bug-report or feature-request template (`.github/ISSUE_TEMPLATE/`). Both are YAML forms — fill in every required field.

The single highest-value thing you can include is the **constructed request** the client made, captured from `LOG_LEVEL=DEBUG`. Many "the tool returns wrong results" reports turn out to be either user-side query syntax or upstream USPTO API quirks; the logged URL and body settle it instantly.

If you don't have access to live logs (for example, the user reported the bug to you secondhand), say so explicitly in the report — write "constructed request not captured" rather than guessing or omitting. A report that admits a gap is more useful than one that papers over it.

Don't file an issue for a tool that returns `API_UNAVAILABLE` — those are intentional and documented. Check `check_api_status` first.

## When submitting a PR

In order:

1. **Confirm the bug exists.** Reproduce it locally — either via `uv run pytest -m integration` or by writing a one-off async script that hits the affected tool. A PR without reproduction is a guess.
2. **Identify the root cause.** Don't pattern-match a fix to surface symptoms. If a query parameter is being ignored, find *why* — wrong default, dropped param, upstream API requiring a different shape, etc.
3. **Write a unit test that fails before the fix and passes after.** This is the contract that prevents regression.
4. **Make the smallest fix that addresses the root cause.** Don't refactor adjacent code in the same PR unless it's necessary for the fix.
5. **Run the full test suite.** `uv run pytest` — must be 100% green.
6. **Bump the version** if the change is user-visible. Patch in both `pyproject.toml` and `config.py:USER_AGENT`.
7. **Update docstrings.** The `Args:` and `USE THIS TOOL WHEN:` sections in tool definitions are surfaced to other LLMs as the tool's interface — they matter as much as the code.

Branch name convention for agent-authored PRs: `claude/<slug>`, `aider/<slug>`, etc. — any prefix that identifies the agent is fine.

## Project layout cheat sheet

```
src/patent_mcp_server/
├── patents.py              # MCP tool definitions (the public surface)
├── config.py               # Env-var-driven config; bump USER_AGENT here on release
├── uspto/
│   ├── ppubs_uspto_gov.py  # Patent Public Search client (PPUBS)
│   └── api_uspto_gov.py    # Open Data Portal client (ODP)
├── util/{errors,response,validation,logging}.py
└── json/search_query.json  # PPUBS request template
test/unit/                  # Network-free, run by default
test/test_tools*.py         # Integration tests, network required, opt-in via -m integration
```

## Conventions in one screen

- **Tool naming**: `ppubs_*`, `odp_*`, `ptab_*`, `patentsview_*` (legacy).
- **Parameters**: `query` not `q`; `app_num`; `patent_number`; `offset` + `limit`.
- **Error returns**: `{"error": True, "message": ..., "error_code": ...}` — build via `ApiError.create()`.
- **Decommissioned APIs** return `error_code="API_UNAVAILABLE"` with a `workaround` field pointing at the active replacement.
- **Everything is async.** Tool functions are `async def`; clients use `async with`.
- **No new dependencies** without a clear reason. The existing four cover almost everything.

## What not to do

- Don't restructure the package layout to "modernize" it. Single `patents.py` for tool definitions is intentional — MCP servers benefit from one obvious entry point.
- Don't add abstractions ("BaseClient", "ToolRegistry", dependency injection) without an explicit ask. The codebase deliberately prefers shallow, readable code.
- Don't delete or rename a tool that's been published, even if it returns `API_UNAVAILABLE`. MCP clients may be pinned to the name.
- Don't skip tests to make a commit go through. If a test fails, fix the root cause.
- Don't commit the `.env` file or any secrets. Check `git status` before every commit.
