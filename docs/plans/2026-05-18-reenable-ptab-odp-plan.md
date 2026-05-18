# Re-enable PTAB Tools on ODP v3.0 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Flip the 7 PTAB MCP tools from hard-coded `API_UNAVAILABLE` back to live, working tools backed by USPTO ODP v3.0 endpoints.

**Architecture:** USPTO released ODP v3.0 on 2025-11-21 adding PTAB endpoints under `https://api.uspto.gov/api/v1/patent/trials/...` (proceedings, documents, decisions) and `.../patent/appeals/...` (ex parte appeals). They are GET endpoints that filter via a single Lucene-style `q=field:value` param plus `offset`/`limit`; flat params (`patentNumber=`, `trialType=`) are silently ignored. There is **no REST `/{id}` route** — single-record fetches are done via `search?q=<idField>:<value>`. Responses are ODP-shaped: top-level `count` plus a `patentTrialProceedingDataBag` / `patentTrialDocumentDataBag` / `patentAppealDataBag` array. The existing `PTABClient` has the right skeleton but wrong paths, wrong param style, and wrong response assumptions; this plan reworks the request/response layer, wires the tools, corrects all docs, and bumps the version.

**Tech Stack:** Python 3.12, httpx (async, http2), tenacity retry, pytest (`uv run pytest`), FastMCP.

**Ground-truth facts (verified live against api.uspto.gov on 2026-05-18, treat as authoritative — blogs disagreed, the live API did not):**
- `GET /api/v1/patent/trials/proceedings/search?q=&offset=&limit=` → 200, `count`, `patentTrialProceedingDataBag` (total corpus count ~19263).
- `GET /api/v1/patent/trials/proceedings/search?q=trialNumber:IPR2022-00001` → 200, `count` 1 (patent 8667559, Kajeet Inc.).
- `GET /api/v1/patent/trials/documents/search?q=trialNumber:IPR2022-00001` → 200, `count` 108; `patentTrialDocumentDataBag`; total corpus ~1517027.
- `GET /api/v1/patent/trials/decisions/search?q=&offset=&limit=` → 200, `count` ~20517, `patentTrialDocumentDataBag` (rows carry `decisionData`).
- `GET /api/v1/patent/trials/decisions/search?q=trialNumber:IPR2022-00001` → 200, `count` 2.
- `GET /api/v1/patent/appeals/decisions/search?q=&offset=&limit=` → 200, `count` ~163513, `patentAppealDataBag`. **Base path is `/api/v1/patent/appeals/` — NOT under `/trials/`.**
- `GET /api/v1/patent/appeals/decisions/search?q=appealNumber:2026001737` → 200, `count` 1.
- Verified filterable `q` fields: `trialNumber`, `appealNumber`, `patentOwnerData.patentNumber`. `offset`/`limit` honored.
- `q=` with multiple space-separated clauses behaves as AND.
- A 403 body `{"message":"Missing Authentication Token"}` from AWS API Gateway means **route does not exist**, not an auth failure.
- `interferences` is **genuinely absent** (403 on every variant). No MCP tool maps to it; client interference methods stay non-functional and out of scope here.
- Other flat params the legacy client/tool expose (`trial_type`, `party_name`, `status`, `filing_date_*`, `decision_date_*`, `application_number`) have **unverified** ODP field names — Task 2 discovers them empirically; never ship a guessed field name.

**Auth/env:** ODP key in `.env` as `USPTO_API_KEY` (`grep USPTO_API_KEY .env | cut -d= -f2`); header `X-API-KEY`. Live probing: `cd /home/triple/patent-research/patent_mcp_server` then `curl -s -H "X-API-KEY: $KEY" "<url>"`.

**Test commands:** unit `uv run pytest` (expect ~258 passing pre-change, 44 deselected); single `uv run pytest path::name -q`; integration `uv run pytest -m integration`.

---

### Task 1: Normalize PTAB databags in `ResponseEnvelope.from_ptab`

`from_ptab` currently only reads `results`/`data`; PTAB returns `count` + a `patent*DataBag`. Make it ODP-shaped-aware.

**Files:**
- Modify: `src/patent_mcp_server/util/response.py:189-212` (`from_ptab`)
- Test: `test/unit/test_response_util.py`

- [ ] **Step 1: Write the failing test** — append to `test/unit/test_response_util.py`:

```python
@pytest.mark.unit
def test_from_ptab_unwraps_proceeding_databag():
    raw = {
        "count": 2,
        "patentTrialProceedingDataBag": [
            {"trialNumber": "IPR2022-00001"},
            {"trialNumber": "IPR2022-00002"},
        ],
    }
    env = ResponseEnvelope.from_ptab(raw, offset=0, limit=25)
    assert env["success"] is True
    assert env["source"] == "ptab"
    assert env["total"] == 2
    assert len(env["results"]) == 2
    assert env["results"][0]["trialNumber"] == "IPR2022-00001"


@pytest.mark.unit
def test_from_ptab_unwraps_document_and_appeal_databags():
    for bag in ("patentTrialDocumentDataBag", "patentAppealDataBag"):
        raw = {"count": 1, bag: [{"x": 1}]}
        env = ResponseEnvelope.from_ptab(raw, 0, 25)
        assert env["results"] == [{"x": 1}]
        assert env["total"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest test/unit/test_response_util.py -k from_ptab -q`
Expected: FAIL — current `from_ptab` returns `results=[]` because it never reads `patentTrialProceedingDataBag`.

- [ ] **Step 3: Write minimal implementation** — replace the body of `from_ptab` (lines 204-210) so it checks the PTAB bag keys before falling back:

```python
        _PTAB_BAGS = (
            "patentTrialProceedingDataBag",
            "patentTrialDocumentDataBag",
            "patentAppealDataBag",
        )
        results = raw_response.get("results", raw_response.get("data", []))
        if not results:
            for _bag in _PTAB_BAGS:
                if isinstance(raw_response.get(_bag), list):
                    results = raw_response[_bag]
                    break
        total = raw_response.get(
            "total",
            raw_response.get(
                "count", len(results) if isinstance(results, list) else 1
            ),
        )

        return ResponseEnvelope.success(
            results=results,
            source="ptab",
            count=len(results) if isinstance(results, list) else 1,
            total=total,
            offset=offset,
            limit=limit,
        )
```

(Match the exact kwargs `ResponseEnvelope.success` already receives below line 210 — read lines 208-218 first and preserve every existing kwarg; only the `results`/`total` derivation changes.)

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest test/unit/test_response_util.py -q`
Expected: PASS, no other response-util test regressed.

- [ ] **Step 5: Commit**

```bash
git add src/patent_mcp_server/util/response.py test/unit/test_response_util.py
git commit -m "Normalize PTAB count/databag responses in from_ptab"
```

---

### Task 2: Discover unverified `q` field names (empirical, no guessing)

We only verified `trialNumber`, `appealNumber`, `patentOwnerData.patentNumber`. Before implementing `trial_type`/`party_name`/`status`/date filters we must learn the real ODP field names — or decide to fold them into free-text `q`.

**Files:**
- Create: `docs/plans/ptab-field-findings.md` (a findings note, not code)
- Modify: `src/patent_mcp_server/constants.py` (add a `PTABFields` class with only VERIFIED fields)

- [ ] **Step 1: Probe candidate fields against the live API.** For each, compare the filtered `count` to the unfiltered baseline (`count` changes ⇒ field is real; identical ⇒ silently ignored). Run, substituting `$KEY`:

```bash
cd /home/triple/patent-research/patent_mcp_server
KEY=$(grep USPTO_API_KEY .env | cut -d= -f2)
B="https://api.uspto.gov/api/v1/patent/trials/proceedings/search"
c(){ curl -s -H "X-API-KEY: $KEY" "$1" | python3 -c "import sys,json;print('count=',json.load(sys.stdin).get('count'))"; }
c "$B?limit=1"                                             # baseline
c "$B?q=trialTypeCategory:IPR&limit=1"
c "$B?q=proceedingTypeCategory:IPR&limit=1"
c "$B?q=trialType:IPR&limit=1"
c "$B?q=petitionerPartyName:Apple&limit=1"
c "$B?q=patentOwnerName:Apple&limit=1"
c "$B?q=proceedingStatusCategory:Terminated&limit=1"
c "$B?q=proceedingFilingDate:[2022-01-01 TO 2022-12-31]&limit=1"
c "$B?q=proceedingFilingDate:%3E2022-01-01&limit=1"
```

- [ ] **Step 2: Record findings.** Write `docs/plans/ptab-field-findings.md` with a table: candidate field → verified? (count delta) → decision. **Rule:** a field is "verified" only if a filtered query returns a count strictly different from baseline AND not zero-for-a-known-present-value. List the final verified field name for each of: trial type, party name, status, proceeding filing-date range, decision-date range, application number (probe analogous fields on `/decisions/search` and `/appeals/decisions/search`).

- [ ] **Step 3: Add `PTABFields` constants** — append to `src/patent_mcp_server/constants.py`:

```python
class PTABFields:
    """Verified ODP PTAB `q=` filter field names (see docs/plans/ptab-field-findings.md).

    Only fields confirmed against the live API are listed. Anything not
    here is folded into the free-text `q` term as best-effort.
    """
    TRIAL_NUMBER = "trialNumber"
    APPEAL_NUMBER = "appealNumber"
    PATENT_NUMBER = "patentOwnerData.patentNumber"
    # Add ONLY fields Step 2 verified, e.g.:
    # TRIAL_TYPE = "<verified name>"
    # PARTY_NAME = "<verified name>"
    # STATUS = "<verified name>"
    # FILING_DATE = "<verified name>"
    # DECISION_DATE = "<verified name>"
    # APPLICATION_NUMBER = "<verified name>"
```

Fill the commented lines with exactly the field names Step 2 verified; delete any that could not be verified (those become free-text `q` terms in Task 3).

- [ ] **Step 4: Commit**

```bash
git add src/patent_mcp_server/constants.py docs/plans/ptab-field-findings.md
git commit -m "Document and constant-ize verified PTAB q= filter fields"
```

---

### Task 3: Rework `PTABClient` request/response layer

Fix base paths (appeals is NOT under `/trials`), build a single `q=` from filters, drop nonexistent `/{id}` routes, route single-record fetches through search.

**Files:**
- Modify: `src/patent_mcp_server/uspto/ptab_client.py` (whole class body; module docstring lines 1-13)
- Test: `test/unit/test_ptab_client.py` (rewrite — existing tests assert the old broken contract)

- [ ] **Step 1: Write the failing tests** — replace the bodies of the existing tests in `test/unit/test_ptab_client.py` (keep the `ptab_client` fixture) so they assert the NEW contract. Core cases:

```python
@pytest.mark.unit
async def test_search_proceedings_builds_q_and_correct_path(ptab_client):
    with patch.object(ptab_client, "_make_request",
                       new_callable=AsyncMock) as m:
        m.return_value = {"count": 0, "patentTrialProceedingDataBag": []}
        await ptab_client.search_proceedings(
            query="estoppel", patent_number="8667559", offset=5, limit=3
        )
    path, kwargs = m.call_args.args[0], m.call_args.kwargs
    assert path == "/api/v1/patent/trials/proceedings/search"
    q = kwargs["params"]["q"]
    assert "estoppel" in q
    assert "patentOwnerData.patentNumber:8667559" in q
    assert kwargs["params"]["offset"] == 5
    assert kwargs["params"]["limit"] == 3


@pytest.mark.unit
async def test_get_proceeding_uses_search_not_id_route(ptab_client):
    with patch.object(ptab_client, "_make_request",
                       new_callable=AsyncMock) as m:
        m.return_value = {"count": 1, "patentTrialProceedingDataBag": [{}]}
        await ptab_client.get_proceeding("IPR2022-00001")
    path, kwargs = m.call_args.args[0], m.call_args.kwargs
    assert path == "/api/v1/patent/trials/proceedings/search"
    assert kwargs["params"]["q"] == "trialNumber:IPR2022-00001"


@pytest.mark.unit
async def test_get_documents_uses_documents_search(ptab_client):
    with patch.object(ptab_client, "_make_request",
                       new_callable=AsyncMock) as m:
        m.return_value = {"count": 0, "patentTrialDocumentDataBag": []}
        await ptab_client.get_proceeding_documents("IPR2022-00001")
    path, kwargs = m.call_args.args[0], m.call_args.kwargs
    assert path == "/api/v1/patent/trials/documents/search"
    assert kwargs["params"]["q"] == "trialNumber:IPR2022-00001"


@pytest.mark.unit
async def test_appeals_use_appeals_base_path(ptab_client):
    with patch.object(ptab_client, "_make_request",
                       new_callable=AsyncMock) as m:
        m.return_value = {"count": 1, "patentAppealDataBag": [{}]}
        await ptab_client.get_appeal_decision("2026001737")
    path, kwargs = m.call_args.args[0], m.call_args.kwargs
    assert path == "/api/v1/patent/appeals/decisions/search"
    assert kwargs["params"]["q"] == "appealNumber:2026001737"


@pytest.mark.unit
async def test_search_decisions_path_and_q(ptab_client):
    with patch.object(ptab_client, "_make_request",
                       new_callable=AsyncMock) as m:
        m.return_value = {"count": 0, "patentTrialDocumentDataBag": []}
        await ptab_client.search_decisions(query="anticipation")
    path, kwargs = m.call_args.args[0], m.call_args.kwargs
    assert path == "/api/v1/patent/trials/decisions/search"
    assert "anticipation" in kwargs["params"]["q"]
```

Also delete/replace old assertions referencing `/proceedings/{n}`, `/decisions/{id}`, `trialType`/`patentNumber` flat params.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest test/unit/test_ptab_client.py -q`
Expected: FAIL — current client calls `/proceedings/{n}`, uses `self.base_url` (`…/trials`) for appeals, and sets flat `params["patentNumber"]`.

- [ ] **Step 3: Implement.** In `ptab_client.py`:

  (a) Replace module docstring (lines 1-13) with an accurate one (PTAB live on ODP v3.0; cite endpoints).

  (b) `__init__`: drop the `self.base_url = …/trials` coupling. Keep host only:

```python
        self.api_base = config.API_BASE_URL  # https://api.uspto.gov
```

  (c) `_make_request(self, path, method=HTTPMethods.GET, params=None, data=None)` — `path` is now the FULL path after the host:

```python
        url = f"{self.api_base}{path}"
```

(rest of `_make_request` body unchanged.)

  (d) Add a helper:

```python
    @staticmethod
    def _build_q(free_text, clauses):
        """Join a free-text term and `field:value` clauses (AND = space).

        Values containing whitespace are double-quoted.
        """
        parts = []
        if free_text:
            parts.append(free_text)
        for field, value in clauses:
            if value is None:
                continue
            v = f'"{value}"' if " " in str(value) else str(value)
            parts.append(f"{field}:{v}")
        return " ".join(parts)
```

  (e) Rewrite each method to the verified contract (only verified `PTABFields`; unverified user inputs appended to `free_text`). Example for proceedings — apply the same pattern to the rest:

```python
    async def search_proceedings(self, query=None, trial_type=None,
            patent_number=None, party_name=None, filing_date_from=None,
            filing_date_to=None, status=None,
            offset=Defaults.SEARCH_START, limit=Defaults.API_LIMIT):
        clauses = []
        if patent_number:
            clauses.append((PTABFields.PATENT_NUMBER, patent_number))
        # add verified-field clauses here per Task 2 findings; fold any
        # unverified inputs (trial_type/party_name/status/dates) into
        # free text:
        extra = " ".join(str(x) for x in
                          (trial_type, party_name, status,
                           filing_date_from, filing_date_to) if x)
        q = self._build_q(" ".join(p for p in (query, extra) if p), clauses)
        params = {"offset": offset, "limit": limit}
        if q:
            params["q"] = q
        return await self._make_request(
            "/api/v1/patent/trials/proceedings/search", params=params)

    async def get_proceeding(self, proceeding_number):
        return await self._make_request(
            "/api/v1/patent/trials/proceedings/search",
            params={"q": f"{PTABFields.TRIAL_NUMBER}:{proceeding_number}"})

    async def get_proceeding_documents(self, proceeding_number,
            document_type=None, offset=Defaults.SEARCH_START,
            limit=Defaults.API_LIMIT):
        q = self._build_q(
            document_type or "",
            [(PTABFields.TRIAL_NUMBER, proceeding_number)])
        return await self._make_request(
            "/api/v1/patent/trials/documents/search",
            params={"q": q, "offset": offset, "limit": limit})

    async def search_decisions(self, query=None, decision_type=None,
            proceeding_number=None, patent_number=None,
            decision_date_from=None, decision_date_to=None,
            offset=Defaults.SEARCH_START, limit=Defaults.API_LIMIT):
        clauses = []
        if proceeding_number:
            clauses.append((PTABFields.TRIAL_NUMBER, proceeding_number))
        if patent_number:
            clauses.append((PTABFields.PATENT_NUMBER, patent_number))
        extra = " ".join(str(x) for x in
                          (decision_type, decision_date_from,
                           decision_date_to) if x)
        q = self._build_q(" ".join(p for p in (query, extra) if p), clauses)
        params = {"offset": offset, "limit": limit}
        if q:
            params["q"] = q
        return await self._make_request(
            "/api/v1/patent/trials/decisions/search", params=params)

    async def get_decision(self, decision_id):
        # No decision-id route exists; decisions are keyed by trial number.
        return await self._make_request(
            "/api/v1/patent/trials/decisions/search",
            params={"q": f"{PTABFields.TRIAL_NUMBER}:{decision_id}"})

    async def search_appeals(self, query=None, application_number=None,
            patent_number=None, appeal_number=None,
            decision_date_from=None, decision_date_to=None,
            offset=Defaults.SEARCH_START, limit=Defaults.API_LIMIT):
        clauses = []
        if appeal_number:
            clauses.append((PTABFields.APPEAL_NUMBER, appeal_number))
        if patent_number:
            clauses.append((PTABFields.PATENT_NUMBER, patent_number))
        extra = " ".join(str(x) for x in
                          (application_number, decision_date_from,
                           decision_date_to) if x)
        q = self._build_q(" ".join(p for p in (query, extra) if p), clauses)
        params = {"offset": offset, "limit": limit}
        if q:
            params["q"] = q
        return await self._make_request(
            "/api/v1/patent/appeals/decisions/search", params=params)

    async def get_appeal_decision(self, appeal_number):
        return await self._make_request(
            "/api/v1/patent/appeals/decisions/search",
            params={"q": f"{PTABFields.APPEAL_NUMBER}:{appeal_number}"})
```

  (f) `search_interferences`/`get_interference`: ODP has no interference route. Make both return `ApiError.create(message="PTAB interference proceedings are not available on the USPTO Open Data Portal.", status_code=501)` and add a docstring note. (No MCP tool calls these; this just prevents a misleading 403.)

  (g) Add `from patent_mcp_server.constants import ... PTABFields` to the imports.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest test/unit/test_ptab_client.py -q`
Expected: PASS.

- [ ] **Step 5: Live smoke check**

```bash
cd /home/triple/patent-research/patent_mcp_server
uv run python -c "
import asyncio
from patent_mcp_server.uspto.ptab_client import PTABClient
async def m():
    async with PTABClient() as c:
        r=await c.get_proceeding('IPR2022-00001')
        print('proc count', r.get('count'))
        d=await c.get_proceeding_documents('IPR2022-00001', limit=2)
        print('docs count', d.get('count'))
        a=await c.get_appeal_decision('2026001737')
        print('appeal count', a.get('count'))
asyncio.run(m())"
```
Expected: `proc count 1`, `docs count 108` (or current), `appeal count 1`.

- [ ] **Step 6: Commit**

```bash
git add src/patent_mcp_server/uspto/ptab_client.py test/unit/test_ptab_client.py
git commit -m "Rework PTABClient to live ODP v3.0 contract (paths, q=, search-by-id)"
```

---

### Task 4: Wire the 7 PTAB tools in `patents.py`

**Files:**
- Modify: `src/patent_mcp_server/patents.py` — add `PTABClient` import (line ~42 area, with the other uspto client imports), instantiate `ptab_client = PTABClient()` (line ~63, after `api_client`), replace each `return _ptab_unavailable()` (lines 974, 991, 1013, 1043, 1056, 1084, 1097), delete `_ptab_unavailable` (lines 1100-1119) and remove the false "IMPORTANT: …not available…" paragraphs from the 7 docstrings.
- Test: `test/unit/test_ptab_tools.py` (create)

- [ ] **Step 1: Write the failing test** — create `test/unit/test_ptab_tools.py`:

```python
"""Tool-layer tests: PTAB tools call PTABClient and envelope results."""
from unittest.mock import AsyncMock, patch
import pytest
from patent_mcp_server.patents import (
    ptab_search_proceedings, ptab_get_proceeding, ptab_get_documents,
    ptab_search_decisions, ptab_get_decision, ptab_search_appeals,
    ptab_get_appeal,
)

PROC = {"count": 1, "patentTrialProceedingDataBag": [{"trialNumber": "IPR2022-00001"}]}


@pytest.mark.unit
async def test_search_proceedings_returns_envelope():
    with patch("patent_mcp_server.patents.ptab_client.search_proceedings",
               new=AsyncMock(return_value=PROC)):
        r = await ptab_search_proceedings(query="estoppel", limit=5)
    assert r["success"] is True
    assert r["source"] == "ptab"
    assert r["results"][0]["trialNumber"] == "IPR2022-00001"


@pytest.mark.unit
async def test_all_seven_tools_no_longer_unavailable():
    bags = {
        "search_proceedings": PROC, "get_proceeding": PROC,
        "get_proceeding_documents": {"count": 0, "patentTrialDocumentDataBag": []},
        "search_decisions": {"count": 0, "patentTrialDocumentDataBag": []},
        "get_decision": {"count": 0, "patentTrialDocumentDataBag": []},
        "search_appeals": {"count": 0, "patentAppealDataBag": []},
        "get_appeal_decision": {"count": 0, "patentAppealDataBag": []},
    }
    with patch.multiple(
        "patent_mcp_server.patents.ptab_client",
        **{k: AsyncMock(return_value=v) for k, v in bags.items()},
    ):
        results = [
            await ptab_search_proceedings(query="x"),
            await ptab_get_proceeding(proceeding_number="IPR2022-00001"),
            await ptab_get_documents(proceeding_number="IPR2022-00001"),
            await ptab_search_decisions(query="x"),
            await ptab_get_decision(decision_id="IPR2022-00001"),
            await ptab_search_appeals(query="x"),
            await ptab_get_appeal(appeal_number="2026001737"),
        ]
    for r in results:
        assert r.get("error_code") != "API_UNAVAILABLE"
        assert r.get("success") is True
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest test/unit/test_ptab_tools.py -q`
Expected: FAIL — tools still return `API_UNAVAILABLE`; also `patent_mcp_server.patents.ptab_client` does not exist yet (AttributeError).

- [ ] **Step 3: Implement.**
  - Import: add `from patent_mcp_server.uspto.ptab_client import PTABClient` next to the other `uspto.*` imports.
  - Instantiate near line 63: `ptab_client = PTABClient()`.
  - Ensure the existing `atexit`/cleanup path that closes `api_client`/`ppubs_client` also closes `ptab_client` (grep for where `ppubs_client.close`/`api_client.close` are awaited in the shutdown handler and add `ptab_client`).
  - Replace each tool body. Patterns:

```python
# ptab_search_proceedings
    result = await ptab_client.search_proceedings(
        query=query, trial_type=trial_type, patent_number=patent_number,
        party_name=party_name, filing_date_from=filing_date_from,
        filing_date_to=filing_date_to, status=status,
        offset=offset, limit=limit)
    if is_error(result):
        return result
    return check_and_truncate(
        ResponseEnvelope.from_ptab(result, offset, limit))

# ptab_get_proceeding
    result = await ptab_client.get_proceeding(proceeding_number)
    if is_error(result):
        return result
    return check_and_truncate(ResponseEnvelope.from_ptab(result))

# ptab_get_documents
    result = await ptab_client.get_proceeding_documents(
        proceeding_number, document_type=document_type,
        offset=offset, limit=limit)
    if is_error(result):
        return result
    return check_and_truncate(
        ResponseEnvelope.from_ptab(result, offset, limit))

# ptab_search_decisions
    result = await ptab_client.search_decisions(
        query=query, decision_type=decision_type,
        proceeding_number=proceeding_number, patent_number=patent_number,
        decision_date_from=decision_date_from,
        decision_date_to=decision_date_to, offset=offset, limit=limit)
    if is_error(result):
        return result
    return check_and_truncate(
        ResponseEnvelope.from_ptab(result, offset, limit))

# ptab_get_decision
    result = await ptab_client.get_decision(decision_id)
    if is_error(result):
        return result
    return check_and_truncate(ResponseEnvelope.from_ptab(result))

# ptab_search_appeals
    result = await ptab_client.search_appeals(
        query=query, application_number=application_number,
        patent_number=patent_number,
        decision_date_from=decision_date_from,
        decision_date_to=decision_date_to, offset=offset, limit=limit)
    if is_error(result):
        return result
    return check_and_truncate(
        ResponseEnvelope.from_ptab(result, offset, limit))

# ptab_get_appeal
    result = await ptab_client.get_appeal(appeal_number)
    if is_error(result):
        return result
    return check_and_truncate(ResponseEnvelope.from_ptab(result))
```
  Note: `ptab_get_appeal` calls `ptab_client.get_appeal` — either add a thin `get_appeal = get_appeal_decision` alias in the client or call `get_appeal_decision` here; pick one and keep it consistent with Task 3 method names.
  - Delete `_ptab_unavailable` (lines 1100-1119) and scrub the "IMPORTANT: …not available…" lines from all 7 docstrings; replace with accurate one-liners (e.g. "Live via USPTO ODP v3.0.").

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest test/unit/test_ptab_tools.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/patent_mcp_server/patents.py test/unit/test_ptab_tools.py
git commit -m "Wire 7 PTAB tools to live PTABClient; remove _ptab_unavailable"
```

---

### Task 5: Remove PTAB from the unavailable-tools test suite

`test/unit/test_unavailable_tools.py` asserts the 7 PTAB tools return `API_UNAVAILABLE` — now false.

**Files:**
- Modify: `test/unit/test_unavailable_tools.py` (imports lines 27-33; `class TestUnavailablePTABTools` lines 208-255; parametrized list lines 323-330)

- [ ] **Step 1: Update tests** — delete the entire `class TestUnavailablePTABTools` block (lines ~208-255), delete the 7 PTAB tuples from the `TestUnavailableToolErrorStructure` parametrize list (lines ~323-330) and their `# PTAB tools …` comment, and remove the 7 now-unused PTAB imports (lines 27-33).

- [ ] **Step 2: Run to verify suite is consistent**

Run: `uv run pytest test/unit/test_unavailable_tools.py -q`
Expected: PASS (no PTAB references; PatentsView/Office-Action/etc. tests untouched).

- [ ] **Step 3: Commit**

```bash
git add test/unit/test_unavailable_tools.py
git commit -m "Drop PTAB from unavailable-tools tests (now live on ODP)"
```

---

### Task 6: Correct `check_api_status`, `resources.py`, prompt text

**Files:**
- Modify: `src/patent_mcp_server/patents.py` lines ~324-333 (the `"ptab"` block in `check_api_status`) and the module header comment lines ~10-11 if it lists PTAB as unavailable
- Modify: `src/patent_mcp_server/resources.py` lines ~314-323 (`"ptab"` DATA_SOURCES entry) and line ~335 (the "PTAB decision analysis (UNAVAILABLE …)" prompt string)

- [ ] **Step 1: Failing test** — add to `test/unit/test_ptab_tools.py`:

```python
@pytest.mark.unit
async def test_check_api_status_reports_ptab_active():
    from patent_mcp_server.patents import check_api_status
    s = await check_api_status()
    assert s["sources"]["ptab"]["status"] != "UNAVAILABLE"
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest test/unit/test_ptab_tools.py -k api_status -q`
Expected: FAIL — status currently `"UNAVAILABLE"`.

- [ ] **Step 3: Implement.** In `check_api_status` `"ptab"` block: set `"status": "ACTIVE"`, `"configured": bool(config.USPTO_API_KEY)`, replace the `"note"` with: `"PTAB Trial/Appeal data via USPTO ODP v3.0 (api.uspto.gov). Requires USPTO_API_KEY."`. In `resources.py` `"ptab"` entry: rewrite the description to state it is live on ODP v3.0 with the proceedings/documents/decisions/appeals endpoints; drop the "UNAVAILABLE"/developer.uspto.gov text; fix line ~335 prompt string to remove "(UNAVAILABLE …)". Scrub any PTAB "UNAVAILABLE" line in the patents.py module header comment.

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest test/unit/test_ptab_tools.py -q && uv run pytest -q`
Expected: PASS; full suite green.

- [ ] **Step 5: Commit**

```bash
git add src/patent_mcp_server/patents.py src/patent_mcp_server/resources.py
git commit -m "Mark PTAB ACTIVE in status/resources/prompts"
```

---

### Task 7: Integration tests (live, skipped by default)

**Files:**
- Create: `test/test_ptab_integration.py`

- [ ] **Step 1: Write integration tests**

```python
"""Live PTAB integration tests. Run: uv run pytest -m integration"""
import pytest
from patent_mcp_server.patents import (
    ptab_search_proceedings, ptab_get_proceeding, ptab_get_documents,
    ptab_search_appeals,
)


@pytest.mark.integration
async def test_live_search_proceedings_returns_real_data():
    r = await ptab_search_proceedings(query="", limit=3)
    assert r["success"] is True
    assert r["total"] > 1000
    assert len(r["results"]) <= 3


@pytest.mark.integration
async def test_live_get_proceeding_by_trial_number():
    r = await ptab_get_proceeding(proceeding_number="IPR2022-00001")
    assert r["success"] is True
    assert r["total"] >= 1


@pytest.mark.integration
async def test_live_documents_and_appeals():
    d = await ptab_get_documents(proceeding_number="IPR2022-00001", limit=2)
    assert d["success"] is True and d["total"] > 0
    a = await ptab_search_appeals(query="", limit=2)
    assert a["success"] is True and a["total"] > 1000
```

- [ ] **Step 2: Run integration subset**

Run: `uv run pytest test/test_ptab_integration.py -m integration -q`
Expected: PASS (needs network + `USPTO_API_KEY`).

- [ ] **Step 3: Verify default run still skips them**

Run: `uv run pytest -q`
Expected: integration tests deselected; full unit suite green.

- [ ] **Step 4: Commit**

```bash
git add test/test_ptab_integration.py
git commit -m "Add live PTAB integration tests (skipped by default)"
```

---

### Task 8: Docs + version bump

**Files:**
- Modify: `CLAUDE.md` (the "Current state" line + Active/Unavailable lists)
- Modify: `README.md` (tool counts, version history)
- Modify: `pyproject.toml:7` (`version = "0.10.0"`)
- Modify: `src/patent_mcp_server/config.py:39` (`USER_AGENT` → `patent-mcp-server/0.10.0`)

- [ ] **Step 1: Update CLAUDE.md** — change "v0.9.0 … 20 active, 32 unavailable" framing to the new reality: PTAB (7) moves from Unavailable to Active; Active becomes PPUBS (5), ODP (12), PTAB (7), Utility (3); Unavailable drops PTAB. Update the "Handling Decommissioned APIs" section is not needed; just the state summary and counts. State current version 0.10.0.

- [ ] **Step 2: Update README.md** — bump tool counts/active list to include PTAB; add a version-history entry: `v0.10.0 — Re-enable 7 PTAB tools on USPTO ODP v3.0; fix odp_search_applications/odp_search_datasets query contracts; fix ppubs_download_patent_pdf arity.`

- [ ] **Step 3: Bump version** — `pyproject.toml` `version = "0.10.0"`; `config.py` `USER_AGENT` default to `patent-mcp-server/0.10.0`.

- [ ] **Step 4: Verify**

Run: `uv run pytest -q`
Expected: full suite green.

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md README.md pyproject.toml src/patent_mcp_server/config.py
git commit -m "Docs + version bump to 0.10.0 (PTAB re-enabled)"
```

---

### Task 9: Final full verification

- [ ] **Step 1: Full unit suite**

Run: `uv run pytest -q`
Expected: all pass, ~44 deselected, zero PTAB `API_UNAVAILABLE` references remain (`grep -rn "API_UNAVAILABLE" src | grep -i ptab` → empty).

- [ ] **Step 2: Live end-to-end of all 7 tools**

```bash
cd /home/triple/patent-research/patent_mcp_server
uv run python -c "
import asyncio
from patent_mcp_server.patents import (ptab_search_proceedings,
 ptab_get_proceeding, ptab_get_documents, ptab_search_decisions,
 ptab_get_decision, ptab_search_appeals, ptab_get_appeal)
async def m():
    for label,coro in [
      ('search_proceedings', ptab_search_proceedings(query='', limit=2)),
      ('get_proceeding', ptab_get_proceeding(proceeding_number='IPR2022-00001')),
      ('get_documents', ptab_get_documents(proceeding_number='IPR2022-00001', limit=2)),
      ('search_decisions', ptab_search_decisions(query='', limit=2)),
      ('get_decision', ptab_get_decision(decision_id='IPR2022-00001')),
      ('search_appeals', ptab_search_appeals(query='', limit=2)),
      ('get_appeal', ptab_get_appeal(appeal_number='2026001737')),
    ]:
        r=await coro
        print(label, 'success=', r.get('success'), 'total=', r.get('total'))
asyncio.run(m())"
```
Expected: every line `success= True` with a plausible `total`.

- [ ] **Step 3: Integration suite**

Run: `uv run pytest -m integration -q`
Expected: PASS.

- [ ] **Step 4: Final commit (if anything uncommitted)**

```bash
git add -A && git commit -m "PTAB re-enable: final verification"
```

---

## Self-Review

- **Spec coverage:** client rework (T3) ✓, response shape (T1) ✓, field discovery without guessing (T2) ✓, tool wiring + remove `_ptab_unavailable` (T4) ✓, unavailable-test cleanup (T5) ✓, status/resources/prompts (T6) ✓, integration (T7) ✓, docs+version (T8) ✓, final verify (T9) ✓. Interferences explicitly scoped out (no MCP tool; client returns 501) — covered in T3 step (f).
- **Placeholders:** T2 Step 3 intentionally leaves field constants to be filled from empirical findings — this is a discovery task, not a placeholder; the rule for filling it is explicit. All code steps contain real code.
- **Type/name consistency:** client methods referenced by T4 (`search_proceedings`, `get_proceeding`, `get_proceeding_documents`, `search_decisions`, `get_decision`, `search_appeals`, `get_appeal`/`get_appeal_decision`) match T3 definitions; the one ambiguity (`get_appeal` vs `get_appeal_decision`) is called out in T4 Step 3 with a directive to reconcile. `ResponseEnvelope.from_ptab` signature `(raw, offset=0, limit=25)` used consistently. `PTABFields` defined T2, used T3.
- **Risk note:** T2 may find that trial_type/party/status/date fields cannot be verified; the plan's fallback (fold into free-text `q`) is honest and documented rather than shipping guessed field names.
