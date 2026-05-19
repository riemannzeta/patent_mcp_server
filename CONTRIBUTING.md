# Contributing

Thanks for taking the time to improve `patent-mcp-server`. This project is small, the surface area is well-defined, and clear contributions are easy to land. AI agents are explicit first-class contributors — see [AGENTS.md](AGENTS.md) for agent-specific guidance and the issue templates that follow.

## Quick start

```bash
git clone https://github.com/riemannzeta/patent_mcp_server.git
cd patent_mcp_server
uv sync --dev
cp .env.example .env  # then fill in USPTO_API_KEY
uv run pytest         # ~259 unit tests should pass
```

Integration tests (which hit the live USPTO APIs) are skipped by default; run them with `uv run pytest -m integration`. They require a valid `USPTO_API_KEY` and outbound network access to `api.uspto.gov` and `ppubs.uspto.gov`.

## Filing a good bug report

Most of the time spent on a bug report is reproducing it. Help us skip that step.

The `.github/ISSUE_TEMPLATE/bug_report.yml` template prompts for everything we need, but the gist:

- **Exact tool call** — the tool name and the arguments you passed, copy-pasted. Example: `ppubs_search_patents(query="machine learning", limit=25)`.
- **Expected vs actual** — one sentence each. "Expected the top results to mention machine learning; actually got the latest grants regardless of query."
- **Constructed request** — set `LOG_LEVEL=DEBUG` in your env, re-run, and paste the URL and (for POST) the request body the client logged. This is usually the difference between "we'll get to it" and "I see the bug, here's the fix."
- **Raw upstream response** — first ~50 lines of the raw API response when relevant. If you don't have it, that's fine, but it usually pins down whether the bug is in our code or upstream at USPTO.
- **Version** — output of `pip show patent-mcp-server` or the installed PyPI version.
- **Whether the affected tool is one of the [decommissioned APIs](README.md)** — if so, the tool is intentionally returning `API_UNAVAILABLE`; that's not a bug.

A weak report ("ppubs search returns wrong results") will get triaged but probably stall. A report with the four bullets above usually gets a fix in the same session.

## Filing a good PR

Before opening a PR:

1. **All tests pass** — `uv run pytest` must be green. No skipping tests to make a PR mergeable.
2. **New behavior has new tests** — unit tests live under `test/unit/` and mock the network. Integration tests live in `test/test_tools.py` / `test/test_tools_pytest.py` and run against the live USPTO APIs.
3. **Docstrings updated** — especially the `USE THIS TOOL WHEN:` and `Args:` sections, since these are surfaced to MCP clients and LLMs.
4. **Version bumped if user-visible** — patch bump in both `pyproject.toml` AND `src/patent_mcp_server/config.py` (`USER_AGENT`). See [`CLAUDE.md`](CLAUDE.md) for the full release workflow.
5. **Touched a decommissioned API?** Follow the seven-step pattern documented in [`CLAUDE.md`](CLAUDE.md) → "Handling Decommissioned APIs."

PR conventions:

- **Branch naming**: `fix/<issue-or-slug>`, `feature/<slug>`, `docs/<slug>`. AI-agent branches commonly use `claude/<slug>` — that's fine.
- **Commit messages**: short imperative subject (≤72 chars), optional body explaining *why* the change is needed. Match the style of recent commits on `main`.
- **Co-authored commits from AI agents are welcome** — add the standard `Co-Authored-By:` trailer.
- The PR template prompts for a one-line summary, the test plan, and a link to the issue.

## Project conventions

This summary is intentionally short — the source of truth is [`CLAUDE.md`](CLAUDE.md).

- **Tool naming**: `ppubs_*`, `odp_*`, `ptab_*`, `patentsview_*` — match the API source.
- **Parameter naming**: `query` (not `q`), `app_num`, `patent_number`, `offset`, `limit`.
- **Error shape**: every tool returns either `{"success": True, "results": ...}` or `{"error": True, "message": ..., "error_code": ...}`. Use `ApiError.create()` to build errors.
- **Async everywhere**: all clients are async, all tools are `async def`.
- **Don't introduce new dependencies without a clear reason.** `httpx`, `pydantic`, `tenacity`, `mcp[cli]` cover almost everything.

## Code of conduct

Be kind, assume good faith, keep discussions technical. Disagreements are normal; personal attacks are not.
