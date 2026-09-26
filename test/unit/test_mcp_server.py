"""Unit tests for the MCP protocol layer.

The rest of the suite calls the tool functions directly, which skips
everything MCPServer does: schema generation, resource and prompt
registration, and serialization of results. These tests drive the server
through a real client over an in-memory transport, so a change that
breaks registration or a tool signature fails here rather than in a user's
client.
"""
import json

import pytest
from mcp.client import Client

from patent_mcp_server import patents


def connect():
    """Open a client session against the real server object.

    ``Client(server)`` connects in memory (mcp 2 replaced
    create_connected_server_and_client_session with it). Used inline as
    ``async with connect() as session``. Deliberately not a pytest
    fixture: the session holds a running server task for as long as it is
    open, and handing that across a fixture yield deadlocks when the
    fixture and the test resolve to different event loops.
    """
    return Client(patents.mcp)


# ============================================================================
# Registration
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_server_exposes_tools():
    """The full tool set is registered and reachable over the protocol."""
    async with connect() as session:
        result = await session.list_tools()
        names = {tool.name for tool in result.tools}

        # Spot-check one tool per active API family
        assert "ppubs_search_patents" in names
        assert "odp_get_application" in names
        assert "ptab_search_proceedings" in names
        assert "tsdr_get_trademark_status" in names
        assert "tm_search_trademarks" in names
        assert "check_api_status" in names


@pytest.mark.unit
@pytest.mark.asyncio
async def test_every_tool_has_usable_schema():
    """Each tool carries a description and an object input schema.

    MCPServer builds these from the function signature and docstring, so this
    catches an unannotated argument or a missing docstring.
    """
    async with connect() as session:
        result = await session.list_tools()

        for tool in result.tools:
            assert tool.description, f"{tool.name} has no description"
            assert tool.input_schema["type"] == "object", f"{tool.name} schema is not an object"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_server_exposes_prompts():
    """Workflow prompts are registered."""
    async with connect() as session:
        result = await session.list_prompts()
        assert len(result.prompts) > 0
        for prompt in result.prompts:
            assert prompt.name


@pytest.mark.unit
@pytest.mark.asyncio
async def test_server_exposes_resources():
    """Static reference resources are registered."""
    async with connect() as session:
        result = await session.list_resources()
        uris = {str(resource.uri) for resource in result.resources}
        assert "patents://sources" in uris


# ============================================================================
# Round trips
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_call_tool_returns_json():
    """A tool call travels through the protocol and returns usable JSON.

    get_cpc_info is served from local reference data, so this needs no
    network access.
    """
    async with connect() as session:
        result = await session.call_tool("get_cpc_info", {"cpc_code": "G06"})

        assert not result.is_error
        payload = json.loads(result.content[0].text)
        assert payload["code"] == "G06"
        assert payload["section"] == "G"
        # structured_output is off in tool(): the dict travels once, as text
        assert result.structured_content is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_read_resource():
    """Resources can be read over the protocol."""
    async with connect() as session:
        result = await session.read_resource("patents://sources")
        assert result.contents[0].text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_prompt():
    """Prompts render over the protocol."""
    async with connect() as session:
        prompts = await session.list_prompts()
        result = await session.get_prompt(prompts.prompts[0].name, {})
        assert result.messages


@pytest.mark.unit
@pytest.mark.asyncio
async def test_every_tool_is_marked_read_only():
    """Every registered tool carries read-only annotations.

    Clients that honor them can skip a per-call confirmation; a tool
    registered with a bare @mcp.tool() would lose that.
    """
    async with connect() as session:
        result = await session.list_tools()
        for tool in result.tools:
            assert tool.annotations is not None, f"{tool.name} has no annotations"
            assert tool.annotations.read_only_hint is True, f"{tool.name} not read-only"
            assert tool.annotations.open_world_hint is True, f"{tool.name} not open-world"
            # No output schema: structured_output is off (see tool() in patents.py)
            assert tool.output_schema is None, f"{tool.name} advertises an outputSchema"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_annotations_use_camel_case_on_the_wire():
    """Clients read readOnlyHint, not read_only_hint, from the JSON."""
    async with connect() as session:
        result = await session.list_tools()
        wire = result.tools[0].annotations.model_dump(by_alias=True, exclude_none=True)
        assert wire["readOnlyHint"] is True
        assert "read_only_hint" not in wire


@pytest.mark.unit
@pytest.mark.asyncio
async def test_legacy_tools_hidden_by_default():
    """Tools for shut-down APIs are not registered unless opted in.

    Their schemas cost every client ~6k tokens per session, and the
    functions still exist for direct callers (test_unavailable_tools.py).
    """
    if patents.config.ENABLE_LEGACY_TOOLS:
        pytest.skip("ENABLE_LEGACY_TOOLS is set in this environment")
    async with connect() as session:
        result = await session.list_tools()
        names = {tool.name for tool in result.tools}

    for name in ("patentsview_search_patents", "get_office_action_text",
                 "get_enriched_citations", "search_litigation"):
        assert name not in names, f"{name} registered without ENABLE_LEGACY_TOOLS"
        assert callable(getattr(patents, name)), f"{name} function removed"

    payload = await patents.patentsview_search_patents(query="test")
    assert payload["error_code"] == "API_UNAVAILABLE"
    assert payload["workaround"]


@pytest.mark.unit
def test_legacy_tool_registers_when_enabled(monkeypatch):
    """With ENABLE_LEGACY_TOOLS set, legacy_tool registers like tool."""
    monkeypatch.setattr(patents.config, "ENABLE_LEGACY_TOOLS", True)

    @patents.legacy_tool()
    async def legacy_probe_tool() -> dict:
        """Probe."""
        return {}

    try:
        registered = patents.mcp._tool_manager.get_tool("legacy_probe_tool")
        assert registered is not None
        assert registered.annotations.read_only_hint is True
    finally:
        patents.mcp._tool_manager._tools.pop("legacy_probe_tool", None)


@pytest.mark.unit
def test_legacy_tool_returns_function_when_disabled(monkeypatch):
    """With the default off, legacy_tool leaves the function untouched."""
    monkeypatch.setattr(patents.config, "ENABLE_LEGACY_TOOLS", False)

    async def probe() -> dict:
        return {}

    assert patents.legacy_tool()(probe) is probe
    assert patents.mcp._tool_manager.get_tool("probe") is None


# ============================================================================
# Statelessness
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_server_survives_repeated_sessions():
    """Consecutive sessions each work against the same server object.

    Anything torn down at the end of a session would leave later sessions
    broken. Under mcp 1 stateless HTTP entered the lifespan once per request,
    which made this a hard rule; client shutdown still lives in serve()
    rather than a lifespan, and this test keeps it that way.
    """
    for _ in range(3):
        async with connect() as client:
            result = await client.call_tool("get_cpc_info", {"cpc_code": "G06"})
            assert not result.is_error

    # The shared HTTP clients must still be open for real work to continue.
    assert not patents.ppubs_client.client.is_closed
    assert not patents.api_client.client.is_closed


@pytest.mark.unit
@pytest.mark.asyncio
async def test_concurrent_sessions_are_independent():
    """Two sessions can run at once without sharing protocol state."""
    import anyio

    results = {}

    async def run(label):
        async with connect() as client:
            result = await client.call_tool("get_cpc_info", {"cpc_code": "G06"})
            results[label] = json.loads(result.content[0].text)["code"]

    async with anyio.create_task_group() as tg:
        tg.start_soon(run, "a")
        tg.start_soon(run, "b")

    assert results == {"a": "G06", "b": "G06"}


# ============================================================================
# Transport configuration
# ============================================================================

@pytest.mark.unit
def test_default_transport_is_stdio():
    """Existing local installs keep working without new flags."""
    args = patents.build_arg_parser().parse_args([])
    assert args.transport == "stdio"


@pytest.mark.unit
def test_http_transport_flags():
    """HTTP options are wired through to the parser."""
    args = patents.build_arg_parser().parse_args(
        ["--transport", "streamable-http", "--host", "0.0.0.0", "--port", "9001"]
    )
    assert args.transport == "streamable-http"
    assert args.host == "0.0.0.0"
    assert args.port == 9001


@pytest.mark.unit
def test_env_var_sets_statelessness(monkeypatch):
    """MCP_STATELESS is honoured, and the command line can still override it.

    build_arg_parser() reads the config when it is called, so the flag
    default tracks the environment rather than being fixed at import.
    """
    monkeypatch.setattr(patents.config, "MCP_STATELESS", False)
    assert patents.build_arg_parser().parse_args([]).stateful is True
    assert patents.build_arg_parser().parse_args(["--no-stateful"]).stateful is False

    monkeypatch.setattr(patents.config, "MCP_STATELESS", True)
    assert patents.build_arg_parser().parse_args([]).stateful is False
    assert patents.build_arg_parser().parse_args(["--stateful"]).stateful is True


@pytest.mark.unit
def test_stateless_is_the_default():
    """HTTP serving is stateless unless --stateful is passed."""
    assert patents.build_arg_parser().parse_args([]).stateful is False
    assert patents.build_arg_parser().parse_args(["--stateful"]).stateful is True


@pytest.mark.unit
def test_http_settings_follow_the_flags():
    """Parsed flags become the keyword arguments run_streamable_http_async takes."""
    args = patents.build_arg_parser().parse_args(
        ["--transport", "streamable-http", "--host", "0.0.0.0", "--port", "9001",
         "--path", "/patents", "--stateful", "--json-response"]
    )
    assert patents.http_settings(args) == {
        "host": "0.0.0.0",
        "port": 9001,
        "streamable_http_path": "/patents",
        "stateless_http": False,
        "json_response": True,
    }


@pytest.mark.unit
def test_main_hands_transport_settings_to_serve(monkeypatch):
    """main() passes the transport and its settings into serve() via anyio.run.

    mcp 2 has no mcp.settings to mutate, so this is the only path by which
    --host/--port/--path/--stateful/--json-response reach the transport.
    """
    calls = {}
    monkeypatch.setattr(patents.sys, "argv",
                        ["patent-mcp-server", "--transport", "streamable-http", "--port", "9002"])
    monkeypatch.setattr(patents.anyio, "run", lambda fn, *a: calls.update(fn=fn, args=a))

    patents.main()

    assert calls["fn"] is patents.serve
    transport, http = calls["args"]
    assert transport == "streamable-http"
    assert http["port"] == 9002
    assert http["stateless_http"] is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_serve_passes_http_settings_and_cleans_up(monkeypatch):
    """serve() forwards the settings to the HTTP runner and always runs cleanup."""
    from unittest.mock import AsyncMock

    run_http = AsyncMock()
    cleanup = AsyncMock()
    monkeypatch.setattr(patents.mcp, "run_streamable_http_async", run_http)
    monkeypatch.setattr(patents, "cleanup", cleanup)

    settings = {"host": "127.0.0.1", "port": 9003, "streamable_http_path": "/mcp",
                "stateless_http": True, "json_response": False}
    await patents.serve("streamable-http", settings)

    run_http.assert_awaited_once_with(**settings)
    cleanup.assert_awaited_once()
