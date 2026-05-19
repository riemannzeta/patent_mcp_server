"""
Live PTAB integration tests.

These tests make real HTTP calls to api.uspto.gov/api/v3/ptab and require
network access plus a valid USPTO_API_KEY in the environment (or .env file).

Run:  uv run pytest test/test_ptab_integration.py -m integration -q
Skip: (default) pytest -m "not integration" deselects these automatically.
"""

import pytest

from patent_mcp_server.patents import (
    ptab_search_proceedings,
    ptab_get_proceeding,
    ptab_get_documents,
    ptab_search_appeals,
)

# Mark every test in this module as an integration test so they are
# deselected by the default addopts = -m "not integration" in pytest.ini.
#
# loop_scope="module" shares one event loop across all tests in this file.
# This prevents "Event loop is closed" errors from the module-level
# ptab_client singleton (an httpx.AsyncClient bound to the first loop).
pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="module")]


async def test_live_search_proceedings_returns_real_data():
    """Unfiltered search should return thousands of PTAB proceedings."""
    r = await ptab_search_proceedings(query="", limit=3)
    assert r["success"] is True
    assert r["total"] > 1000
    assert len(r["results"]) <= 3


async def test_live_get_proceeding_by_trial_number():
    """Fetch a specific, well-known IPR proceeding by trial number."""
    r = await ptab_get_proceeding(proceeding_number="IPR2022-00001")
    assert r["success"] is True
    assert r["total"] >= 1


async def test_live_documents_and_appeals():
    """Smoke-test document retrieval and appeal search in one pass."""
    d = await ptab_get_documents(proceeding_number="IPR2022-00001", limit=2)
    assert d["success"] is True
    assert d["total"] > 0

    a = await ptab_search_appeals(query="", limit=2)
    assert a["success"] is True
    # The PTAB appeal corpus is large; > 1000 is a conservative lower bound.
    assert a["total"] > 1000
