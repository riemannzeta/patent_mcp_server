"""Unit tests for the MCP protocol layer.

The rest of the suite calls the tool functions directly, which skips
everything FastMCP does: schema generation, resource and prompt
registration, and serialization of results. These tests drive the server
through a real ClientSession over an in-memory transport, so a change that
breaks registration or a tool signature fails here rather than in a user's
client.
"""
import json

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from patent_mcp_server import patents


def connect():
    """Open a client session against the real server object.

    Used inline as ``async with connect() as session``. Deliberately not a
    pytest fixture: the session holds a running server task for as long as
    it is open, and handing that across a fixture yield deadlocks when the
    fixture and the test resolve to different event loops.
    """
    return create_connected_server_and_client_session(patents.mcp)


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

    FastMCP builds these from the function signature and docstring, so this
    catches an unannotated argument or a missing docstring.
    """
    async with connect() as session:
        result = await session.list_tools()

        for tool in result.tools:
            assert tool.description, f"{tool.name} has no description"
            assert tool.inputSchema["type"] == "object", f"{tool.name} schema is not an object"


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

        assert not result.isError
        payload = json.loads(result.content[0].text)
        assert payload["code"] == "G06"
        assert payload["section"] == "G"


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
async def test_decommissioned_tool_reports_unavailable():
    """A shut-down API surfaces its guidance through the protocol.

    These tools stay registered on purpose so clients get a workaround
    instead of an unknown-tool error.
    """
    async with connect() as session:
        result = await session.call_tool("patentsview_search_patents", {"query": "test"})

        payload = json.loads(result.content[0].text)
        assert payload["error"] is True
        assert payload["error_code"] == "API_UNAVAILABLE"
        assert payload["workaround"]


# ============================================================================
# Statelessness
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_server_survives_repeated_sessions():
    """Consecutive sessions each work against the same server object.

    In stateless HTTP mode the low-level server is entered once per request,
    so anything torn down at the end of a session would leave later requests
    broken. This is the regression test for putting client shutdown in a
    lifespan.
    """
    for _ in range(3):
        async with create_connected_server_and_client_session(patents.mcp) as client:
            result = await client.call_tool("get_cpc_info", {"cpc_code": "G06"})
            assert not result.isError

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
        async with create_connected_server_and_client_session(patents.mcp) as client:
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
