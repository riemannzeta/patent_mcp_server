"""
Response normalization utilities for consistent API responses.

This module provides utilities for:
- Standardizing response format across different backends
- Token budget awareness and response truncation
- Response envelope creation
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Union

from patent_mcp_server.config import config
from patent_mcp_server.constants import DocumentSections

logger = logging.getLogger('response_util')


class ResponseEnvelope:
    """Standard response envelope for all API responses."""

    @staticmethod
    def success(
        results: Union[List[Any], Dict[str, Any], Any],
        source: str,
        count: Optional[int] = None,
        total: Optional[int] = None,
        offset: int = 0,
        limit: int = 100,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a standardized success response.

        Args:
            results: The actual results data
            source: Data source identifier (e.g., 'patentsview', 'ppubs', 'odp')
            count: Number of results in this response
            total: Total available results (for pagination)
            offset: Current offset position
            limit: Requested limit
            metadata: Optional source-specific metadata

        Returns:
            Standardized response dictionary
        """
        # Calculate count if not provided
        if count is None:
            if isinstance(results, list):
                count = len(results)
            elif isinstance(results, dict):
                count = 1
            else:
                count = 1 if results is not None else 0

        # Calculate has_more
        if total is not None:
            has_more = (offset + count) < total
        else:
            has_more = False
            total = count

        response = {
            "success": True,
            "source": source,
            "count": count,
            "total": total,
            "offset": offset,
            "limit": limit,
            "has_more": has_more,
            "results": results,
        }

        if metadata:
            response["metadata"] = metadata

        return response

    @staticmethod
    def from_ppubs(
        raw_response: Dict[str, Any],
        offset: int = 0,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Normalize a PPUBS API response.

        Args:
            raw_response: Raw response from PPUBS API
            offset: Requested offset
            limit: Requested limit

        Returns:
            Standardized response
        """
        # PPUBS format: {numFound, perPage, page, patents: [...]}
        results = [
            slim_search_hit(hit) if isinstance(hit, dict) else hit
            for hit in raw_response.get("patents", [])
        ]
        total = raw_response.get("numFound", len(results))

        return ResponseEnvelope.success(
            results=results,
            source="ppubs",
            count=len(results),
            total=total,
            offset=offset,
            limit=limit,
            metadata={
                "per_page": raw_response.get("perPage"),
                "page": raw_response.get("page"),
                "total_pages": raw_response.get("totalPages"),
            }
        )

    @staticmethod
    def from_odp(
        raw_response: Dict[str, Any],
        offset: int = 0,
        limit: int = 25,
    ) -> Dict[str, Any]:
        """Normalize an ODP (api.uspto.gov) API response.

        Args:
            raw_response: Raw response from ODP API
            offset: Requested offset
            limit: Requested limit

        Returns:
            Standardized response
        """
        # ODP format varies: {count, patentFileWrapperDataBag: [...]} or direct data
        if "patentFileWrapperDataBag" in raw_response:
            results = raw_response.get("patentFileWrapperDataBag", [])
            total = raw_response.get("count", len(results))
        elif "results" in raw_response:
            results = raw_response.get("results", [])
            total = raw_response.get("count", len(results))
        else:
            # Single result or direct data
            results = raw_response
            total = 1

        return ResponseEnvelope.success(
            results=results,
            source="odp",
            count=len(results) if isinstance(results, list) else 1,
            total=total,
            offset=offset,
            limit=limit,
        )

    @staticmethod
    def from_patentsview(
        raw_response: Dict[str, Any],
        offset: int = 0,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Normalize a PatentsView API response.

        Args:
            raw_response: Raw response from PatentsView API
            offset: Requested offset
            limit: Requested limit

        Returns:
            Standardized response
        """
        # PatentsView format: {patents: [...], count, total_hits}
        # or {assignees: [...], count} etc.
        results = (
            raw_response.get("patents") or
            raw_response.get("assignees") or
            raw_response.get("inventors") or
            raw_response.get("claims") or
            raw_response.get("g_claim") or
            raw_response.get("g_brf_sum_text") or
            raw_response.get("g_detail_desc_text") or
            []
        )
        total = raw_response.get("total_hits") or raw_response.get("count", len(results))

        return ResponseEnvelope.success(
            results=results,
            source="patentsview",
            count=len(results) if isinstance(results, list) else 1,
            total=total,
            offset=offset,
            limit=limit,
        )

    @staticmethod
    def from_ptab(
        raw_response: Dict[str, Any],
        offset: int = 0,
        limit: int = 25,
    ) -> Dict[str, Any]:
        """Normalize a PTAB API response.

        Args:
            raw_response: Raw response from PTAB API
            offset: Requested offset
            limit: Requested limit

        Returns:
            Standardized response
        """
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


    @staticmethod
    def from_tsdr(
        raw_response: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Normalize a TSDR API response (single trademark record).

        Args:
            raw_response: Raw response from TSDR API

        Returns:
            Standardized response
        """
        # TSDR info.json format: {"trademarks": [{...}]} with one record
        trademarks = raw_response.get("trademarks")
        if isinstance(trademarks, list) and trademarks:
            results = trademarks[0] if len(trademarks) == 1 else trademarks
        else:
            results = raw_response

        return ResponseEnvelope.success(
            results=results,
            source="tsdr",
            offset=0,
            limit=1,
        )

    @staticmethod
    def from_tmsearch(
        parsed_response: Dict[str, Any],
        offset: int = 0,
        limit: int = 25,
    ) -> Dict[str, Any]:
        """Normalize a parsed tmsearch.uspto.gov response.

        Args:
            parsed_response: Output of TmSearchClient.parse_search_response,
                shaped {"results": [...], "total": N}
            offset: Requested offset
            limit: Requested limit

        Returns:
            Standardized response
        """
        results = parsed_response.get("results", [])
        total = parsed_response.get("total", len(results))

        return ResponseEnvelope.success(
            results=results,
            source="tmsearch",
            count=len(results) if isinstance(results, list) else 1,
            total=total,
            offset=offset,
            limit=limit,
        )

    @staticmethod
    def from_tm_assignment(
        parsed_response: Dict[str, Any],
        offset: int = 0,
        limit: int = 25,
    ) -> Dict[str, Any]:
        """Normalize a trademark assignment search response.

        Args:
            parsed_response: Parsed response shaped {"results": [...], "total": N},
                optionally with a "backend" key (e.g. "assignment-center")
            offset: Requested offset
            limit: Requested limit

        Returns:
            Standardized response
        """
        results = parsed_response.get("results", [])
        total = parsed_response.get("total", len(results))
        metadata = None
        if parsed_response.get("backend"):
            metadata = {"backend": parsed_response["backend"]}

        return ResponseEnvelope.success(
            results=results,
            source="tm_assignments",
            count=len(results) if isinstance(results, list) else 1,
            total=total,
            offset=offset,
            limit=limit,
            metadata=metadata,
        )


def estimate_tokens(data: Any) -> int:
    """Estimate token count for a data structure.

    Uses rough approximation of 4 characters per token.

    Args:
        data: Data to estimate tokens for

    Returns:
        Estimated token count
    """
    if data is None:
        return 0

    try:
        json_str = json.dumps(data, default=str)
        return len(json_str) // 4
    except (TypeError, ValueError):
        return len(str(data)) // 4


# PTAB response bag keys, tried in order when the response has no top-level
# "results" or "data" key. Listed in preference order.
_PTAB_BAGS = (
    "patentTrialProceedingDataBag",
    "patentTrialDocumentDataBag",
    "patentAppealDataBag",
)

# Heavy nested fields stripped from ODP file-wrapper records when slicing alone
# can't fit the token budget. Listed in priority order — earlier entries are
# stripped first. Callers can fetch the full record via odp_get_application.
LEAN_STRIP_FIELDS = (
    "eventDataBag",
    "foreignPriorityBag",
    "assignmentBag",
    "claims",
    "descriptionBag",
)


def truncate_response(
    response: Dict[str, Any],
    max_tokens: Optional[int] = None,
    max_results: int = 20,
) -> Dict[str, Any]:
    """Truncate a response if it exceeds token budget.

    Two-stage strategy:
      1. Slice the results list down to ``min(max_results, envelope_limit)``.
         Honors the user's requested ``limit`` even when fewer than the global
         default — fixes the case where 20 fat records still bust the budget.
      2. If still over budget, strip heavy nested fields (eventDataBag,
         foreignPriorityBag, assignmentBag, claims, descriptionBag) from each
         record. Records remain visible; stripped fields are replaced with a
         marker so callers know data was elided.

    Args:
        response: Response dictionary to potentially truncate
        max_tokens: Maximum tokens allowed (default from config)
        max_results: Maximum results to keep when truncating

    Returns:
        Original or truncated response
    """
    max_tokens = max_tokens or config.MAX_RESPONSE_TOKENS

    estimated_tokens = estimate_tokens(response)

    if estimated_tokens <= max_tokens:
        return response

    truncated = response.copy()

    # Stage 1: slice results to the effective limit (user request capped by global default).
    envelope_limit = response.get("limit")
    effective_max = max_results
    if isinstance(envelope_limit, int) and envelope_limit > 0:
        effective_max = min(max_results, envelope_limit)

    if "results" in truncated and isinstance(truncated["results"], list):
        original_count = len(truncated["results"])
        if original_count > effective_max:
            truncated["results"] = truncated["results"][:effective_max]
            truncated["_truncated"] = True
            truncated["_original_count"] = original_count
            truncated["_truncated_to"] = effective_max
            truncated["_truncation_message"] = (
                f"Response truncated from {original_count} to {effective_max} results "
                f"to fit within token budget. Use 'offset' parameter to paginate "
                f"through remaining results."
            )
            truncated["count"] = effective_max

            logger.info(
                f"Truncated response from {original_count} to {effective_max} results "
                f"(estimated {estimated_tokens} tokens exceeded {max_tokens} limit)"
            )

    # Stage 2: still too big? Strip heavy nested fields per record.
    if (
        estimate_tokens(truncated) > max_tokens
        and isinstance(truncated.get("results"), list)
    ):
        stripped_fields: set = set()
        for record in truncated["results"]:
            if not isinstance(record, dict):
                continue
            for field in LEAN_STRIP_FIELDS:
                if field in record:
                    record[field] = {"_stripped": True}
                    stripped_fields.add(field)
        if stripped_fields:
            truncated["_lean_mode"] = True
            truncated["_stripped_fields"] = sorted(stripped_fields)
            truncated["_lean_message"] = (
                "Heavy nested fields stripped to fit token budget. "
                "Fetch a single application with odp_get_application(app_num) "
                "to retrieve the full record."
            )
            logger.info(
                f"Stripped fields {sorted(stripped_fields)} from "
                f"{len(truncated['results'])} record(s) to fit token budget"
            )

    return truncated


def _is_empty(value: Any) -> bool:
    """True for the placeholders PPUBS fills unused fields with."""
    return value is None or value == "" or value == [] or value == {}


# Fields on a PPUBS search hit that outweigh the rest of the hit combined:
# `urpn` lists every US reference the hit cites and `urpnCode` repeats it
# (7 KB each on a typical hit against ~2 KB for everything else). They are
# on the document's front page — ppubs_get_patent_by_number(sections=
# ["biblio"]) — for callers that need them.
SEARCH_HIT_DROP_FIELDS = frozenset({"urpn", "urpnCode"})


def slim_search_hit(hit: Dict[str, Any]) -> Dict[str, Any]:
    """Drop empty, highlight and references-cited fields from a search hit.

    A raw hit has ~90 fields, a third of them empty, plus the search
    highlight fields and the two references-cited lists. Removing them
    cuts a hit to roughly a quarter of its size without losing anything a
    search result is read for (identity, title, dates, parties, classes).
    """
    return {
        key: value
        for key, value in hit.items()
        if not _is_empty(value)
        and "KwicHits" not in key
        and "Highlights" not in key
        and key not in SEARCH_HIT_DROP_FIELDS
    }


def slim_document(
    document: Dict[str, Any],
    sections: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Drop what a reader never needs from a PPUBS full-text document.

    A raw document has ~450 fields, two thirds of them empty, plus search
    highlight fields (``*KwicHits``, ``*Highlights``) that only mean
    something inside the PPUBS web app. Those always go. With ``sections``,
    only the named text sections' HTML fields are kept, plus the
    bibliographic fields when "biblio" is among them; the identity fields
    (guid, title, dates) are kept regardless.

    Args:
        document: Raw document from PpubsClient.get_document
        sections: Subset of DocumentSections.ALL, or None for everything

    Returns:
        A new dictionary; the input is not modified.
    """
    text_fields = {
        field
        for fields in DocumentSections.HTML_FIELDS.values()
        for field in fields
    }
    if sections:
        keep_text = {
            field
            for section in sections
            for field in DocumentSections.HTML_FIELDS.get(section, ())
        }
        keep_biblio = DocumentSections.BIBLIO in sections
    else:
        keep_text = text_fields
        keep_biblio = True

    slim: Dict[str, Any] = {}
    for key, value in document.items():
        if _is_empty(value) or "KwicHits" in key or "Highlights" in key:
            continue
        if key in text_fields:
            if key in keep_text:
                slim[key] = value
        elif keep_biblio or key in DocumentSections.IDENTITY_FIELDS:
            slim[key] = value

    if sections:
        slim["_sections"] = list(sections)
    return slim


def _drop_empty(record: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in record.items() if not _is_empty(v)}


def slim_office_action(record: Dict[str, Any]) -> Dict[str, Any]:
    """One ODP Office Action Search record under plain snake_case names.

    ``obsoleteDocumentIdentifier`` is the file-wrapper documentIdentifier
    (verified on application 18402543), so it comes out as ``document_id``
    for odp_download_document. ``officeActionText`` comes out as
    ``text_preview``: the API returns only its first 500 characters.
    """
    art_unit = record.get("groupArtUnitNumber")
    return _drop_empty({
        "record_id": record.get("officeActionRecordIdentifier"),
        "app_num": record.get("applicationNumberText"),
        "document_code": record.get("documentCode"),
        "description": record.get("documentCodeDescriptionText"),
        "submission_date": record.get("submissionDate"),
        "filing_date": record.get("filingDate"),
        "art_unit": str(art_unit) if art_unit is not None else None,
        "title": record.get("inventionTitle"),
        "rejection_types": record.get("rejectionTypeBag"),
        "document_id": record.get("obsoleteDocumentIdentifier"),
        "text_preview": record.get("officeActionText"),
    })


_REJECTION_STATUTES = (
    ("101", "hasRej101"), ("102", "hasRej102"), ("103", "hasRej103"),
    ("112", "hasRej112"), ("DP", "hasRejDP"),
)
_REJECTION_CASE_LAW = (
    ("Alice", "aliceIndicator"), ("Mayo", "mayoIndicator"),
    ("Myriad", "myriadIndicator"), ("Bilski", "bilskiIndicator"),
)


def parse_claim_numbers(values: Any) -> List[Any]:
    """Claim numbers from claimNumberArrayDocument (["1,10,2,3"]), sorted
    numerically. Anything that is not a plain number is kept as text."""
    if isinstance(values, str):
        values = [values]
    numbers: set = set()
    others: List[str] = []
    for value in values or []:
        for part in str(value).split(","):
            part = part.strip()
            if not part:
                continue
            if part.isdigit():
                numbers.add(int(part))
            elif part not in others:
                others.append(part)
    return sorted(numbers) + others


def _day(value: Optional[str]) -> Optional[str]:
    return value[:10] if isinstance(value, str) and value else value


def group_rejection_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """ODP rejection rows grouped into one entry per office action.

    The statute and case-law flags describe the whole action and repeat on
    each of its rows; legalSectionCode, actionTypeCategory and the claim
    list describe one row. Each action keeps its rows, without exact
    repeats, under ``claim_groups`` and sums them up in ``claims`` by
    action type (rejected, objected, allowed, cancelled).
    """
    actions: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        key = row.get("obsoleteDocumentIdentifier") or row.get("id") or str(len(actions))
        action = actions.get(key)
        if action is None:
            art_unit = row.get("groupArtUnitNumber")
            action = actions[key] = {
                "document_id": row.get("obsoleteDocumentIdentifier"),
                "app_num": row.get("patentApplicationNumber"),
                "document_code": row.get("legacyDocumentCodeIdentifier"),
                "mail_date": _day(row.get("submissionDate")),
                "art_unit": str(art_unit) if art_unit is not None else None,
                "statutes": [],
                "case_law": [],
                "claims": {},
                "claim_groups": [],
            }
        for name, flag in _REJECTION_STATUTES:
            if row.get(flag) in (1, True, "1") and name not in action["statutes"]:
                action["statutes"].append(name)
        for name, flag in _REJECTION_CASE_LAW:
            if row.get(flag) is True and name not in action["case_law"]:
                action["case_law"].append(name)

        claims = parse_claim_numbers(row.get("claimNumberArrayDocument"))
        group = _drop_empty({
            "action": row.get("actionTypeCategory"),
            "legal_section": row.get("legalSectionCode"),
            "paragraph": row.get("paragraphNumber"),
            "claims": claims,
        })
        if group and group not in action["claim_groups"]:
            action["claim_groups"].append(group)
        if claims and row.get("actionTypeCategory"):
            bucket = action["claims"].setdefault(row["actionTypeCategory"], [])
            bucket.extend(c for c in claims if c not in bucket)

    out = []
    for action in actions.values():
        for bucket in action["claims"].values():
            bucket.sort(key=lambda c: (isinstance(c, str), c))
        out.append(_drop_empty(action))
    return out


def slim_oa_citation(row: Dict[str, Any]) -> Dict[str, Any]:
    """One ODP office action citation row under plain snake_case names.

    The three indicators keep USPTO's flags under shorter names. Their
    meaning is inferred from samples, not documented: rows with a 102/103
    legal section carry relied_on_in_action true, and rows listed only on
    a PTO-892 carry it false.
    """
    art_unit = row.get("groupArtUnitNumber")
    reference = row.get("referenceIdentifier")
    return _drop_empty({
        "record_id": row.get("id"),
        "app_num": row.get("patentApplicationNumber"),
        "document_id": row.get("obsoleteDocumentIdentifier"),
        "reference": reference.strip() if isinstance(reference, str) else reference,
        "reference_number": row.get("parsedReferenceIdentifier"),
        "legal_section": row.get("legalSectionCode"),
        "action": row.get("actionTypeCategory"),
        "examiner_cited": row.get("examinerCitedReferenceIndicator"),
        "applicant_cited": row.get("applicantCitedExaminerReferenceIndicator"),
        "relied_on_in_action": row.get("officeActionCitationReferenceIndicator"),
        "art_unit": str(art_unit) if art_unit is not None else None,
        "tech_center": row.get("techCenter"),
    })


# ODP wraps each query match in ocrSearchText as
# <b><span style='background-color: yellow;'>term</span></b>.
_HIGHLIGHT_RE = re.compile(r"<b>\s*<span[^>]*>(.*?)</span>\s*</b>", re.DOTALL)


def strip_highlights(text: Optional[str]) -> Optional[str]:
    """Turn ODP's HTML match highlights into «term» markers."""
    if not text:
        return text
    return _HIGHLIGHT_RE.sub(lambda m: f"\u00ab{m.group(1)}\u00bb", text)


def slim_petition_decision(
    record: Dict[str, Any],
    include_full_text: bool = False,
) -> Dict[str, Any]:
    """One ODP Petition Decisions record under plain snake_case names.

    ``allSearchableFields`` repeats the whole record and the decision's
    full OCR text as one string, so it is dropped unless the caller asks
    for the text. The file-wrapper documents are left to the caller.
    """
    slim = _drop_empty({
        "record_id": record.get("petitionDecisionRecordIdentifier"),
        "app_num": record.get("applicationNumberText"),
        "patent_number": record.get("patentNumber"),
        "decision_date": record.get("decisionDate"),
        "decision_mail_date": record.get("decisionMailDate"),
        "petition_mail_date": record.get("petitionMailDate"),
        "petition_type_code": record.get("decisionPetitionTypeCode"),
        "petition_type": record.get("decisionPetitionTypeCodeDescriptionText"),
        "outcome": record.get("decidedPetitionTypeCodeDescriptionText"),
        "deciding_office": record.get("finalDecidingOfficeName"),
        "final_decision": record.get("finalPetitionDecisionIndicator"),
        "court_action": record.get("courtActionIndicator"),
        "technology_center": record.get("technologyCenter"),
        "art_unit": record.get("groupArtUnitNumber"),
        "entity_status": record.get("businessEntityStatusCategory"),
        "title": record.get("inventionTitle"),
        "inventors": record.get("inventorBag"),
        "first_applicant": record.get("firstApplicantName"),
        "application_status": record.get("applicationStatusDescriptionText"),
        "text": strip_highlights(record.get("ocrSearchText")),
    })
    if include_full_text and record.get("allSearchableFields"):
        slim["full_text"] = record["allSearchableFields"]
    return slim


def facet_counts(facets: Any) -> Dict[str, Dict[str, int]]:
    """ODP facets ({field: [{value, count}]}) as {field: {value: count}}."""
    if not isinstance(facets, dict):
        return {}
    return {
        field: {
            str(bucket.get("value")): bucket.get("count")
            for bucket in buckets or []
            if isinstance(bucket, dict)
        }
        for field, buckets in facets.items()
    }


def check_and_truncate(
    response: Dict[str, Any],
    max_tokens: Optional[int] = None,
) -> Dict[str, Any]:
    """Check response size and truncate if necessary.

    This is the main function to call before returning responses.

    Args:
        response: Response to check
        max_tokens: Optional token limit override

    Returns:
        Original or truncated response
    """
    if not config.TRUNCATE_LARGE_RESPONSES:
        return response

    return truncate_response(response, max_tokens)
