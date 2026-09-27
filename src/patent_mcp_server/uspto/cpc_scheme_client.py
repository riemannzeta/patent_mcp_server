"""
CPC scheme client: group-level titles from USPTO's classification pages.

USPTO publishes the Cooperative Patent Classification scheme as one static
HTML page per subclass, e.g.
https://www.uspto.gov/web/patents/classification/cpc/html/cpc-G06N.html,
listing the subclass title and every main group and subgroup beneath it
with its indent level. There is no JSON API and no key. The full scheme
runs to ~260,000 symbols, too many to bundle, so this client fetches one
subclass page on demand and caches it in process.

Page contract (verified live 2026-09-26):
  - each entry is ``<table class="classItem ..." id="G06N3/08">``
  - the title sits in ``<div class="class-title">`` as an ``ipc-text`` span
    (shared with the IPC) or a brace-wrapped ``cpc-text`` span (CPC-only)
  - subgroups carry ``title="Indent level is N"``; main groups and the
    subclass header carry none
  - a ``date-revised`` span follows the title and is dropped
"""

import asyncio
import html
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx2
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from patent_mcp_server.util.logging import LoggingTransport
from patent_mcp_server.util.errors import ApiError
from patent_mcp_server.config import config
from patent_mcp_server.constants import CpcDefaults

logger = logging.getLogger('cpc_scheme_client')

# "G06N 3/08", "G06N3/08", "g06n 3/08 (2006.01)", "H04B7/0417 20130101",
# "G06N", "G06", "G" — anything the tools or PPUBS hand back.
_SYMBOL_RE = re.compile(r"^([A-HY])(\d{2})?([A-Z])?(?:(\d{1,4})/(\d{2,6}))?$")
_TRAILING_RE = re.compile(r"(\s+\d{8}|\s*\(\d{4}\.\d{2}\))\s*$")

_ITEM_RE = re.compile(r'<table class="classItem[^"]*" id="([^"]+)">(.*?)</table>', re.S)
_INDENT_RE = re.compile(r'Indent level is (\d+)')
_TITLE_RE = re.compile(r'<div class="class-title">(.*?)</div>', re.S)
_REVISED_RE = re.compile(r'<span class="date-revised">.*?</span>', re.S)
_TAG_RE = re.compile(r"<[^>]+>")


def normalize_cpc_symbol(code: str) -> Optional[Dict[str, Optional[str]]]:
    """Split a CPC code into its parts, or None if it is not one.

    Returns {"section": "G", "class": "G06", "subclass": "G06N",
    "group": "3/08", "symbol": "G06N3/08", "display": "G06N 3/08"} with
    the deeper keys None when the code stops short of them.
    """
    cleaned = _TRAILING_RE.sub("", str(code).strip().upper())
    compact = re.sub(r"\s+", "", cleaned)
    match = _SYMBOL_RE.match(compact)
    if not match:
        return None
    section, class_digits, subclass_letter, main, sub = match.groups()
    if (subclass_letter and not class_digits) or (main and not subclass_letter):
        return None
    klass = f"{section}{class_digits}" if class_digits else None
    subclass = f"{klass}{subclass_letter}" if subclass_letter else None
    group = f"{int(main)}/{sub}" if main else None
    symbol = f"{subclass}{group}" if group else (subclass or klass or section)
    display = f"{subclass} {group}" if group else symbol
    return {
        "section": section,
        "class": klass,
        "subclass": subclass,
        "group": group,
        "symbol": symbol,
        "display": display,
    }


def parse_scheme_page(page: str) -> List[Dict[str, Any]]:
    """Parse a subclass page into ordered entries.

    Each entry: {"symbol": "G06N3/08", "title": "Learning methods",
    "indent": 2, "cpc_specific": False}. The subclass header comes first
    with indent -1; main groups have indent 0; subgroups 1 and deeper.
    """
    entries: List[Dict[str, Any]] = []
    for match in _ITEM_RE.finditer(page):
        symbol, body = match.group(1), match.group(2)
        title_match = _TITLE_RE.search(body)
        raw = _REVISED_RE.sub("", title_match.group(1)) if title_match else ""
        cpc_specific = 'class="cpc-text"' in raw and 'class="ipc-text"' not in raw
        text = re.sub(r"\s+", " ", html.unescape(_TAG_RE.sub("", raw))).strip()
        if cpc_specific and text.startswith("{") and text.endswith("}"):
            text = text[1:-1].strip()
        indent_match = _INDENT_RE.search(body)
        if indent_match:
            indent = int(indent_match.group(1))
        elif "/" in symbol:
            indent = 0
        else:
            indent = -1
        entries.append({
            "symbol": symbol,
            "title": text,
            "indent": indent,
            "cpc_specific": cpc_specific,
        })
    return entries


def _display(symbol: str) -> str:
    parts = normalize_cpc_symbol(symbol)
    return parts["display"] if parts else symbol


class CpcSchemeClient:
    """Fetches and caches USPTO CPC subclass scheme pages.

    Supports context manager protocol for proper resource cleanup.
    """

    def __init__(self):
        self.headers = {
            "User-Agent": config.USER_AGENT,
            "Accept": "text/html",
        }
        transport = httpx2.AsyncHTTPTransport()
        logging_transport = LoggingTransport(transport)
        self.client = httpx2.AsyncClient(
            headers=self.headers,
            http2=True,
            follow_redirects=True,
            transport=logging_transport,
            timeout=config.REQUEST_TIMEOUT,
        )
        # subclass -> (fetched_at, entries)
        self._cache: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
        self._lock = asyncio.Lock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def page_url(self, subclass: str) -> str:
        return f"{config.CPC_SCHEME_BASE_URL}/cpc-{subclass}.html"

    @retry(
        stop=stop_after_attempt(config.MAX_RETRIES),
        wait=wait_exponential(
            multiplier=config.RETRY_DELAY,
            min=config.RETRY_MIN_WAIT,
            max=config.RETRY_MAX_WAIT
        ),
        retry=retry_if_exception_type((httpx2.TimeoutException, httpx2.NetworkError)),
        reraise=True
    )
    async def _get(self, url: str) -> httpx2.Response:
        return await self.client.get(url)

    async def get_subclass(self, subclass: str) -> Any:
        """Return the parsed entries for a subclass page, from cache when fresh.

        Returns the entry list, or an error dictionary.
        """
        subclass = subclass.upper()
        now = time.monotonic()
        cached = self._cache.get(subclass)
        if cached and now - cached[0] < CpcDefaults.CACHE_SECONDS:
            return cached[1]

        url = self.page_url(subclass)
        logger.info(f"Fetching CPC scheme page {url}")
        try:
            response = await self._get(url)
        except (httpx2.TimeoutException, httpx2.NetworkError) as e:
            return ApiError.from_exception(e, f"Request to {url} failed")
        except Exception as e:
            return ApiError.from_exception(e, f"Request to {url} failed")

        if response.status_code == 404:
            return ApiError.not_found("CPC subclass", subclass)
        if response.status_code != 200:
            return ApiError.from_http_error(
                status_code=response.status_code, response_text=response.text[:500]
            )

        entries = parse_scheme_page(response.text)
        if not entries:
            return ApiError.create(
                message=(
                    f"The CPC scheme page for {subclass} had no entries the "
                    f"parser recognizes; USPTO may have changed the page layout."
                ),
                error_code="PARSE_ERROR",
                details={"url": url},
            )

        async with self._lock:
            if len(self._cache) >= CpcDefaults.CACHE_MAX_SUBCLASSES:
                oldest = min(self._cache, key=lambda k: self._cache[k][0])
                del self._cache[oldest]
            self._cache[subclass] = (now, entries)
        return entries

    async def lookup(self, code: str) -> Dict[str, Any]:
        """Title and hierarchy for a subclass, main group or subgroup.

        Returns:
            {"code", "symbol", "title", "cpc_specific", "level",
             "hierarchy": [...ancestors and self...], "children": [...],
             "source"} or an error dictionary
        """
        parts = normalize_cpc_symbol(code)
        if not parts or not parts["subclass"]:
            return ApiError.validation_error(
                f"{code!r} is not a CPC subclass or group symbol (e.g. G06N or G06N 3/08)",
                "cpc_code",
            )
        subclass = parts["subclass"]
        entries = await self.get_subclass(subclass)
        if isinstance(entries, dict):
            return entries

        index = {e["symbol"]: i for i, e in enumerate(entries)}
        target = parts["symbol"]
        if target not in index:
            main_groups = [
                {"symbol": _display(e["symbol"]), "title": e["title"]}
                for e in entries if e["indent"] == 0
            ]
            return ApiError.create(
                message=(
                    f"{parts['display']} is not in the current CPC scheme for "
                    f"{subclass}. Its main groups are listed under details."
                ),
                status_code=404,
                error_code="NOT_FOUND",
                details={"subclass": subclass, "main_groups": main_groups[:40],
                         "source": self.page_url(subclass)},
            )

        pos = index[target]
        entry = entries[pos]

        # Ancestors: walk back, keeping the nearest entry at each shallower indent.
        hierarchy = [entry]
        need = entry["indent"] - 1
        for prev in reversed(entries[:pos]):
            if prev["indent"] == need:
                hierarchy.append(prev)
                need -= 1
            if need < -1:
                break
        hierarchy.reverse()

        # Direct children: following entries until indent returns to ours.
        children = []
        for nxt in entries[pos + 1:]:
            if nxt["indent"] <= entry["indent"]:
                break
            if nxt["indent"] == entry["indent"] + 1:
                children.append(nxt)

        level = "subclass" if entry["indent"] == -1 else (
            "main_group" if entry["indent"] == 0 else "subgroup"
        )
        return {
            "code": parts["display"],
            "symbol": entry["symbol"],
            "title": entry["title"],
            "cpc_specific": entry["cpc_specific"],
            "level": level,
            "hierarchy": [
                {"symbol": _display(e["symbol"]), "title": e["title"]} for e in hierarchy
            ],
            "children": [
                {"symbol": _display(e["symbol"]), "title": e["title"]} for e in children
            ],
            "child_count": len(children),
            "source": self.page_url(subclass),
        }

    async def close(self):
        """Close the client connections and clean up resources."""
        logger.info("Closing CPC scheme client connections")
        await self.client.aclose()
