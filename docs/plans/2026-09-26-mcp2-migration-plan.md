---
title: Migrate to MCP Python SDK 2.x
type: chore
date: 2026-09-26
priority: medium
---

# Migrate to MCP Python SDK 2.x

## Overview

v1.2.1 pinned `mcp[cli]>=1.27,<2` because mcp 2.x renamed `mcp.server.fastmcp.FastMCP` to `mcp.server.mcpserver.MCPServer` and a fresh install crashed on import. The pin restores installs but leaves the server on a line that stopped receiving features on 2026-07-28. This plan moves the server to mcp 2.x.

A spike on 2026-09-26 (scratch copy of `src/`, mcp 2.2.0) showed the move is small: one import, one constructor, five transport settings, and the test client. With those changes the server imports with all 38 tools, keeps its annotations, resources and prompts, answers in-memory clients, and completes a live PPUBS call.

## Problem Statement

`mcp<2` buys time, not safety:

- The 1.x line's last release is 1.30.0 (2026-09-07); fixes will land on 2.x.
- mcp 2.x speaks protocol version `2026-07-28`. Clients will assume 2.x server behaviour (structured output, `_meta` envelopes, schema validation of results) sooner or later.
- Contributors who `pip install mcp` get 2.x and cannot import the server, which turns every first PR into a dependency puzzle.

## What Changes

Every SDK touchpoint in the codebase, from `grep` of `src/` and `test/` on 2026-09-26, and what the spike showed for each:

| Touchpoint | Where | mcp 1.x | mcp 2.x | Spike result |
|---|---|---|---|---|
| Server class | `patents.py:31,67` | `from mcp.server.fastmcp import FastMCP` | `from mcp.server.mcpserver import MCPServer` | Works. `name`, `instructions` unchanged |
| Transport settings | `patents.py:82-86` (constructor), `:2667-2671` (`mcp.settings.*` in `main()`) | Constructor kwargs `host`, `port`, `streamable_http_path`, `stateless_http`, `json_response`; overridden via `mcp.settings` | Constructor rejects them; `mcp.settings` no longer exists. Pass them to `run_streamable_http_async(host=, port=, streamable_http_path=, stateless_http=, json_response=)` | Works when `serve()` receives them as kwargs from `main()` |
| Run methods | `patents.py:2654-2656` | `run_stdio_async()`, `run_streamable_http_async()` | Same names; HTTP one takes the settings | Works |
| Tool annotations | `patents.py:93-98` (`ToolAnnotations(readOnlyHint=...)`) | camelCase fields | snake_case fields (`read_only_hint`); camelCase still accepted in the constructor, and `model_dump(by_alias=True)` emits camelCase on the wire | Works unchanged; switch to snake_case for clarity |
| Decorators | 38 `@tool()` / 25 `@legacy_tool()` / `@mcp.resource` / `@mcp.prompt` | `mcp.tool(annotations=...)` | Same signatures | Works |
| Tool return values | every tool returns `Dict[str, Any]` | Serialized as JSON text | Also populates `structured_content` from the dict and advertises an `outputSchema`; the server validates results against it | Works; `get_cpc_info` returned both text and structured content |
| Cleanup | `cleanup()` and `serve()` | Not a lifespan, because 1.x entered the lifespan once per request in stateless HTTP mode | 2.x enters the lifespan once, at session-manager startup, for all sessions and requests | Keep `serve()`'s `finally: await cleanup()`; it is transport-independent. A lifespan becomes an option, not a need |
| Test client | `test/unit/test_mcp_server.py:13,26,212,230` | `mcp.shared.memory.create_connected_server_and_client_session(mcp)` | Removed. `from mcp.client import Client; async with Client(mcp) as client:` connects in memory | Works, including two concurrent clients |
| Result fields in tests | `test_mcp_server.py:63,102,139-140,180,214` | `tool.inputSchema`, `result.isError`, `annotations.readOnlyHint` | `tool.input_schema`, `result.is_error`, `annotations.read_only_hint` (attribute access is snake_case only) | Needs the rename |
| Registry access in tests | `test_mcp_server.py:178-194` | `mcp._tool_manager.get_tool()` / `._tools` | Same private attributes exist | Works |
| Dependency extra | `pyproject.toml` | `mcp[cli]` | The `cli` extra pulls nothing in 2.x (`Provides-Extra: cli` is empty) | Change to `mcp>=2,<3` |
| Transitive pins | `pyproject.toml` (`python-multipart`, `h2`) | Pinned for CVEs in mcp 1.x's tree | `python-multipart` is still a 2.x runtime dependency; keep the pin. `h2` serves our own `httpx[http2]` clients, not mcp | Keep both |
| HTTP client library | nine `httpx` clients in `uspto/` | mcp 1.x also used `httpx` | mcp 2.x uses `httpx2`; both packages install side by side | Live PPUBS call succeeded with `httpx` 0.28 and `httpx2` present |
| Python floor | `requires-python = ">=3.10,<3.14"`, CI matrix 3.10-3.13 | | mcp 2.2.0 requires `>=3.10` | No change |

Not used by this codebase, so not affected: `Context`, `get_context()`, SSE transport, OAuth, sampling, roots, resource subscriptions, the lowlevel `Server` decorators.

## Proposed Solution

Require `mcp>=2,<3` and drop 1.x support in the same release, rather than keeping a compatibility shim that imports whichever class exists.

### Why not support both

A shim costs one `try/except ImportError` around the import and a branch in `main()` for the transport settings, but it doubles the test matrix (the suite must run against both SDKs for the shim to mean anything) and keeps the `create_connected_server_and_client_session` fallback alive in the tests. The server has no consumers that install it as a library and pin their own `mcp`; users run it through `uvx` or `uv sync`, which resolve whatever `pyproject.toml` allows. A clean cut with a minor version bump (1.3.0) says the same thing more cheaply.

### Version

1.3.0. The public tool surface does not change, but the dependency floor moves by a major version and the HTTP transport settings move from constructor to `run()`, which anyone embedding `patents.mcp` would notice.

## Technical Considerations

### Transport settings

`main()` currently mutates `mcp.settings` after parsing flags, and `serve()` calls `run_streamable_http_async()` with no arguments. In 2.x the settings travel with the call:

```python
async def serve(transport: str, http: Optional[Dict[str, Any]] = None) -> None:
    try:
        if transport == "streamable-http":
            await mcp.run_streamable_http_async(**(http or {}))
        else:
            await mcp.run_stdio_async()
    finally:
        await cleanup()


def main():
    args = build_arg_parser().parse_args()
    http = dict(
        host=args.host,
        port=args.port,
        streamable_http_path=args.path,
        stateless_http=not args.stateful,
        json_response=args.json_response,
    )
    ...
    anyio.run(serve, args.transport, http)
```

The `MCP_*` environment variables and `--host/--port/--path/--stateful/--json-response` flags keep their meaning; only the plumbing moves. `test_http_transport_flags`, `test_env_var_sets_statelessness` and `test_stateless_is_the_default` in `test_mcp_server.py` test the parser, and should keep passing; add one test that `main()` hands the parsed values to `serve()`.

### Lifespan semantics

CLAUDE.md warns against a FastMCP lifespan because 1.x entered it once per request under stateless HTTP. 2.x enters it once when the session manager starts. That removes the hazard, but `serve()`'s `finally` already closes the clients on the right event loop for both transports, so there is nothing to gain from moving cleanup into a lifespan now. Update the CLAUDE.md note to say the constraint came from 1.x and that `serve()` remains the shutdown path by choice.

### Structured output

2.x derives an `outputSchema` from the `-> Dict[str, Any]` annotation and fills `structured_content` from the returned dict, next to the JSON text. Both forms travel in every `CallToolResult`. Measured through an in-memory `Client` against the spike server on 2026-09-26:

| Call | text | structured_content | wire total | wire / text |
|---|---|---|---|---|
| `get_cpc_info("G06")` | 125 | 127 | 479 | 3.8 |
| `ppubs_get_patent_by_number(sections=["biblio","claims"])` | 26,791 | 25,723 | 53,732 | 2.0 |
| `ppubs_search_patents(limit=5)` | 4,635 | 3,731 | 9,089 | 2.0 |
| `get_cpc_info` with `structured_output=False` | 125 | 0 | 316 | — |

The schema 2.x derives from `Dict[str, Any]` is `{"result": {"type": "object", "additionalProperties": true}}`, which tells a client nothing it cannot learn from the text. So the duplicate costs a 2x wire payload and buys no typing. **Decision: pass `structured_output=False` in the `tool()` and `legacy_tool()` helpers in Phase 1.** `check_and_truncate` budgets on the dict, and with structured output off the wire size matches that budget again. Revisit only if a tool grows a real Pydantic return model whose schema a client would use.

### Result validation

2.x validates handler results against the advertised schema. `Dict[str, Any]` produces an unconstrained object schema, so any dict passes. Tools that return non-dict values would fail; all 63 return dicts today (`test_every_tool_has_usable_schema` and the unavailable-tool tests cover the shapes).

### Annotations

Keep `READ_ONLY` and the `tool()` / `legacy_tool()` helpers. Write the fields in snake_case; the wire format stays camelCase through `by_alias`.

### Protocol version

mcp 2.x negotiates `2026-07-28` and keeps `HANDSHAKE_PROTOCOL_VERSIONS` for older clients. Verify with the two clients this project documents, Claude Desktop and Claude Code, before release; the smoke tests below cover it.

## Acceptance Criteria

### Functional

- `uvx --from dist/patent_mcp_server-1.3.0-py3-none-any.whl patent-mcp-server --help` runs on a machine without the repo; the resolved `mcp` is 2.x.
- Claude Code (`claude mcp add patents -- uvx patent-mcp-server`) lists 38 tools and completes `get_cpc_info`, `ppubs_search_patents`, and `odp_get_documents` calls.
- `patent-mcp-server --transport streamable-http --port 8000` serves `/mcp`; `claude mcp add --transport http` against it lists the tools; two concurrent requests to a stateless server succeed.
- `ENABLE_LEGACY_TOOLS=true` still registers 63 tools.
- Every tool still carries `readOnlyHint: true` on the wire (`list_tools` over a real client).

### Non-functional

- `uv run pytest` green on Python 3.10-3.13 (CI matrix).
- `uv run pytest -m ""` green live (unit plus integration), as on 2026-09-26.
- No 1.x import paths or `mcp.settings` references remain (`grep -rn "fastmcp\|mcp.settings" src test` is empty).
- `pip-audit` clean after the lock refresh; note that 2.x adds `httpx2`, `opentelemetry-api`, `pyjwt[crypto]`, `jsonschema`, `mcp-types` to the tree.

### Quality gates

- Unit tests cover: in-memory client round trip (`Client(mcp)`), annotations on every tool, legacy gating, transport kwargs from `main()` to `serve()`.
- README: install section, HTTP hosting section and version history updated; CLAUDE.md: the lifespan note and dependency line updated.

## Implementation Plan

### Phase 1: Dependency and server (one commit)

1. `pyproject.toml`: `"mcp>=2,<3"` (drop `[cli]`); keep `python-multipart` and `h2` pins with their comments. `uv lock`.
2. `patents.py`: import `MCPServer`; construct with `name` and `instructions` only; delete the `mcp.settings.*` block in `main()`; thread the five HTTP settings into `serve()` as above.
3. `patents.py`: `ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True)`, and `structured_output=False` in `tool()` so results travel once (see Structured output above).
4. Run `uv run pytest`; expect only `test_mcp_server.py` to fail (import of the removed helper).

### Phase 2: Tests (same PR, second commit)

1. `test/unit/test_mcp_server.py`: replace `create_connected_server_and_client_session(patents.mcp)` with `Client(patents.mcp)` from `mcp.client`; rename `inputSchema`, `isError`, `readOnlyHint`, `openWorldHint` to snake_case at the four sites.
2. Add `test_main_passes_transport_settings_to_serve` (patch `anyio.run`, assert the kwargs).
3. Add a test that `list_tools` over the in-memory client shows `readOnlyHint` in the wire form (`model_dump(by_alias=True)`), which pins the camelCase contract clients rely on.
4. `uv run pytest` green; then `uv run pytest -m ""` live.

### Phase 3: Docs and release

1. README: dependency note in Prerequisites; "Remote hosting over HTTP" unchanged for users; v1.3.0 history entry naming the SDK move and the `[cli]` extra removal.
2. CLAUDE.md: replace the lifespan paragraph's rationale; update the dependency line; note `Client(mcp)` as the test pattern.
3. Version 1.3.0 in `pyproject.toml`, `config.py`, `.env.example`, `uv.lock`.
4. Smoke tests from Acceptance Criteria (stdio via Claude Code; HTTP via `claude mcp add --transport http`; `uvx` from the built wheel on a clean cache).
5. `/release`.

Estimated size: about 40 changed lines in `src/`, 20 in tests, plus docs. The spike patch that produced the results above is the Phase 1 diff.

## Risks and Rollback

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| A client (Claude Desktop build in the field) rejects protocol `2026-07-28` | Low; 2.x keeps handshake versions for older clients | High: server unusable from that client | Smoke-test both clients before release; 1.2.1 stays on PyPI and `uvx patent-mcp-server==1.2.1` is the rollback |
| Structured output doubles wire size (measured 2.0x on documents and searches) | Certain if left on | Medium: context cost the v1.2.0 work just reduced | `structured_output=False` in `tool()` from Phase 1; a unit test asserts `structured_content is None` and no `outputSchema` on the wire |
| 2.x validates results and rejects a tool's return shape | Low; all tools return dicts | Medium | `test_every_tool_has_usable_schema` plus the unavailable-tool tests exercise every shape through the in-memory client |
| New transitive dependencies (`opentelemetry-api`, `httpx2`, `pyjwt[crypto]`) bring their own advisories | Medium over time | Low | Dependabot already watches the lock; `pip-audit` in the release checklist |
| `mcp._tool_manager` (private) changes under 2.x minors | Low | Low: two tests | Prefer `mcp.list_tools()` where a public call suffices |

## What Would Show This Plan Is Wrong

- The stdio smoke test fails against current Claude Desktop: then a shim supporting both SDK lines is worth its cost, and the plan should be reversed to "support both, default to 2.x".
- A client turns out to render `structured_content` and ignore the text: then `structured_output=False` would blank that client's view, and the setting should flip back on with a tighter budget in `check_and_truncate`. Check by calling one tool from Claude Code and Claude Desktop after Phase 1.
- `uv run pytest` on Python 3.10 fails on a 2.x dependency (`anyio>=4.9`, `pydantic>=2.12`, `starlette>=0.48`): then the Python floor moves and the CI matrix with it, which is a larger change than this plan assumes.

## Follow-up: move the USPTO clients from `httpx` to `httpx2` (v1.4.0)

mcp 2 depends on `httpx2`, the successor to `httpx` from the same author, now published under the pydantic organization. The nine USPTO clients in `uspto/` stay on `httpx` 0.28 through the mcp 2 migration: the two packages share only `anyio`, `idna` and `certifi`, resolve side by side (`httpx` 0.28.1 with `httpx2` 2.13.1 in the spike), and the live PPUBS call through `httpx` beside `httpx2` proved they do not interfere at runtime. Keeping them apart keeps the mcp 2 diff to one concern, which matters because that PR's one hard-to-test risk is client compatibility.

But `httpx` is not a place to stay. Its last release is 0.28.1 (December 2024) and `httpcore`'s is 1.0.9 (April 2025), while `httpx2` shipped three releases in the six weeks before this plan. The worst cases of staying, by impact:

1. **An advisory on `httpx`, `httpcore` or `h11` with no fix in the 0.28 tree.** `pip-audit` and Dependabot would stay red, and the only cure would be this migration done in a hurry against the PPUBS session code. Exploitability is low (the clients only make outbound requests to USPTO), but a standing advisory on a server that holds API keys and can be exposed over HTTP is not something to carry.
2. **A lockfile that will not resolve.** `httpx` pins `httpcore==1.*`. A future `mcp` or `httpx2` release that needs a shared package at a version `httpx` 0.28 cannot accept would block the mcp upgrade until this migration is done.
3. **Python 3.14.** When `requires-python` lifts its `<3.14` cap, `httpx` 0.28.1 has never been tested there.

### Cost

Small. The codebase uses nine `httpx` names (`AsyncClient`, `AsyncHTTPTransport`, `AsyncBaseTransport`, `Response`, `Cookies`, `TimeoutException`, `NetworkError`, `ConnectError`, `HTTPStatusError`), and `httpx2` 2.13.1 provides each with the same signature, including `http2=` with the `h2` extra, `build_request` and `send(stream=True)` for document downloads, and `handle_async_request` on the transport for `LoggingTransport`. The unit tests reference those exception classes 67 times, all through the module name. The change is `import httpx` → `import httpx2 as httpx` in eleven files, or a full rename, plus `httpx2[http2]` in place of `httpx` and `h2` in `pyproject.toml`; the existing PPUBS concurrency tests guard the delicate part.

### Plan

Do it as v1.4.0, directly after v1.3.0 ships, as its own PR:

1. `pyproject.toml`: replace `httpx>=0.28.1` and `h2>=4.2.0` with `httpx2[http2]>=2.13`; `uv lock`; confirm `httpx` and `httpcore` leave the lock entirely.
2. Rename the import in the nine clients, `util/logging.py`, and the unit tests. Prefer the full rename (`httpx2.`) over an alias so `grep httpx\.` finds nothing stale.
3. `uv run pytest`, then `uv run pytest -m ""` live: every client against its USPTO service, with the PPUBS session, PDF print job, TSDR XML document list, tmsearch WAF path, and the ODP document download redirect re-verified.
4. Bump to 1.4.0; README and CLAUDE.md dependency notes; `/release`.

### Tripwires

Any of these makes the migration immediate rather than scheduled:

- an advisory on `httpx`, `httpcore` or `h11` with no fix available in `httpx` 0.28's tree
- a `uv lock` conflict between `httpx` and anything mcp 2 pulls in
- a decision to support Python 3.14

## Sources

- Migration guide: <https://py.sdk.modelcontextprotocol.io/v2/migration/>
- Spike: `MCPServer.__init__`, `run_streamable_http_async`, `Client.__init__` signatures and behaviour from `mcp==2.2.0` via `inspect`, 2026-09-26.
- PyPI release dates: mcp 2.0.0 on 2026-07-28; 1.30.0 (last 1.x) and 2.2.0 on 2026-09-07.
