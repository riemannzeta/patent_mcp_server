---
title: Add ODP Office Action Search and Petition Decisions tools
type: feature
date: 2026-10-14
priority: high
---

# Add ODP Office Action Search and Petition Decisions tools

## Overview

USPTO released two Open Data Portal datasets for applications filed since 2001: Office Action Search and Petition Decisions. Both answer on `api.uspto.gov` with the ODP key the server already uses, and both take the same search body as `odp_search_applications`. This plan adds two search tools, rewires the four Office Action legacy stubs to point at them, and records the API contracts in CLAUDE.md. A later phase adds full text for office actions and revives the citation and rejection datasets, which also turned out to be live.

The server ships 38 tools today. This plan adds two in Phase 1 (40), and Phase 3 adds up to two more.

## What the API does (verified live 2026-10-14 with an ODP key)

### Office Action Search

| Item | Contract |
| --- | --- |
| Search | `GET` or `POST /api/v1/patent/office-action/search` |
| Detail | `GET /api/v1/patent/office-action/{officeActionRecordIdentifier}`, which returns the same record and the same 500-character text as search |
| Body | `q`, `filters`, `rangeFilters`, `sort`, `facets`, `fields`, `pagination`: the file-wrapper search shape |
| Envelope | `count`, `officeActionDataBag`, `facets`, `requestIdentifier` |
| Size | 19,939,188 records; earliest `submissionDate` 2007-07-27 |
| Page cap | `limit` must be between 1 and 100; 101 returns 400 "exceeds allowed limit 100" |
| Not found | 404 with `detailedMessage` "No matching records found" |

Record fields: `officeActionRecordIdentifier`, `applicationNumberText`, `documentCode`, `documentCodeDescriptionText`, `submissionDate`, `filingDate`, `groupArtUnitNumber` (an int here, a string in petitions), `inventionTitle`, `rejectionTypeBag` (values `101`, `102`, `103`, `112`, `DoublePatent`, `Other`), `officeActionText`, `obsoleteDocumentIdentifier`, `publicStatusIndicator`, `lastModifiedDateTime`. Records carry no patent number.

Four facts shape the design:

1. **The API returns only the first 500 characters of text but indexes all of it.** Search and detail both cut `officeActionText` at 500 characters and append " ...". The phrase "Response to Arguments", which appears near the end of a final rejection, matches 3.70M of the 4.41M CTFR records. The endpoint therefore finds office actions; it cannot be used to read them.
2. **`obsoleteDocumentIdentifier` is the file-wrapper `documentIdentifier`.** For application 18402543 it matched the CTFR in `/applications/18402543/documents`, which offers PDF, MS_WORD and XML downloads. That match lets a search hit go straight to `odp_download_document`. Only one record was checked.
3. **Document codes extend past rejections.** The facet lists CTNF 8.9M, NOA 4.8M, CTFR 4.4M, CTRS 1.3M, APEA, CTEQ, PETDEC (90k), PPH.DECISION, CTAV, PET.DEC.* and about 60 rarer codes. The PET.DEC.* records overlap the petitions dataset.
4. **Facets give counts cheaply.** `limit=1` with `facets: ["documentCode","rejectionTypeBag"]` returns a breakdown of every match, so questions like "how many §101 rejections did art unit 3689 issue in 2026" cost one call.

### Petition Decisions

| Item | Contract |
| --- | --- |
| Search | `GET` or `POST /api/v1/petition/decisions/search` |
| Detail | `GET /api/v1/petition/decisions/{petitionDecisionRecordIdentifier}` |
| Body / envelope | Same shape; `petitionDecisionDataBag` |
| Size | 1,114,590 records; earliest `decisionDate` 1991-01-10 |
| Documents | `documentBag[].documentIdentifier`; `/download/applications/{app}/{id}.pdf` answers 302, so `odp_download_document` already reads them |

Record fields: `petitionDecisionRecordIdentifier`, `applicationNumberText`, `patentNumber`, `decisionDate`, `decisionMailDate`, `petitionMailDate`, `decisionPetitionTypeCode` and its description (for example 533, "REINSTATE PATENT - UNINTENTIONALLY DELAYED PAYMENT OF MAINTENANCE FEE ..."), `decidedPetitionTypeCodeDescriptionText` (GRANTED 881k, DISMISSED 224k, DENIED 7.5k, GRANTED-IN-PART 1.9k), `finalDecidingOfficeName` (Office of Petitions 939k, Technology Center 101k, International Division 71k, Office of Data Management 3k), `finalPetitionDecisionIndicator`, `courtActionIndicator`, `technologyCenter`, `groupArtUnitNumber`, `businessEntityStatusCategory`, `customerNumber`, `inventorBag`, `firstApplicantName`, `firstInventorToFileIndicator`, `applicationStatusDescriptionText`, `ocrSearchText`, `allSearchableFields`, `documentBag`.

Three facts shape the design:

1. **A text query turns `ocrSearchText` into a highlighted snippet.** Without `q`, the field holds the first 500 OCR characters. With `q=ocrSearchText:"unintentional delay"`, it holds a passage around the match, wrapped in `<b><span style='background-color: yellow;'>…</span></b>`. The tool should convert that markup to plain markers.
2. **`allSearchableFields` repeats the rest of the record** as one string. The tool should drop it.
3. **`finalPetitionDecisionIndicator` is true for exactly the 7,493 DENIED decisions.** It appears to mark a final agency action, which matters for APA review under 5 U.S.C. § 704. A `final_only` filter exposes it.

### Bonus finding: citations and rejections are back

The alert does not mention them, but both datasets that the server's legacy stubs call "decommissioned" answer on ODP:

| Dataset | Endpoint | Records |
| --- | --- | --- |
| OA Rejections | `POST /api/v1/patent/oa/oa_rejections/v2/records` | 93.4M claim-level rows, with `hasRej101`…`hasRejDP`, `aliceIndicator`, `mayoIndicator`, `myriadIndicator`, `bilskiIndicator`, `claimNumberArrayDocument`, `cite103Max` |
| OA Citations | `POST /api/v1/patent/oa/oa_citations/v2/records` | 51.0M rows, with `referenceIdentifier`, `legalSectionCode`, `examinerCitedReferenceIndicator`, `applicantCitedExaminerReferenceIndicator` |

They take form-encoded Solr parameters (`criteria`, `start`, `rows`) and return `response.numFound/docs`. `OfficeActionClient` points at `developer.uspto.gov/ds-api/...` with different paths and parameters, so reviving these datasets means rewriting the client, not changing a base URL. Phase 3 handles them.

## Phase 1: two search tools (one PR, minor version 1.6.0)

### `odp_search_office_actions`

```python
@tool()
async def odp_search_office_actions(
    query: Optional[str] = None,          # Lucene over officeActionText and other fields
    app_num: Optional[str] = None,
    patent_number: Optional[str] = None,  # resolved to app_num via applications search
    document_code: Optional[str] = None,  # comma list: CTNF,CTFR,NOA,CTRS,CTAV,APEA ...
    rejection_type: Optional[str] = None, # comma list of 101,102,103,112,DoublePatent,Other; AND-ed
    art_unit: Optional[str] = None,
    date_from: Optional[str] = None,      # submissionDate range
    date_to: Optional[str] = None,
    record_id: Optional[str] = None,      # officeActionRecordIdentifier
    sort: str = "newest",                 # newest | oldest
    offset: int = 0,
    limit: int = 25,                      # clamped to 100
) -> Dict[str, Any]:
```

- **Docstring**, under `USE THIS TOOL WHEN`: finding office actions across applications by what the examiner wrote ("means-plus-function", "Alice", "inherent anticipation"), by statute, by art unit or by date, and counting them. The docstring must say that `text_preview` holds only the first 500 characters. To read a hit, pass `app_num` and `document_id` to `odp_download_document`. For one application's history, `odp_get_documents` stays cheaper.
- **Result per hit**: `record_id`, `app_num`, `document_code`, `description`, `submission_date`, `filing_date`, `art_unit`, `title`, `rejection_types`, `document_id` (renamed from `obsoleteDocumentIdentifier` so the next call reads naturally), and `text_preview`.
- **Metadata**: the `documentCode` and `rejectionTypeBag` facets for the full match set, every time. The facets cost little and answer counting questions without paging.
- **`patent_number`**: OA records have no patent number. The tool resolves it with one `applications/search` call on `applicationMetaData.patentNumber`. That call adds latency but avoids a two-step workflow for the commonest starting point.
- **Validation**: at least one filter is required, as in `odp_search_applications`. That requirement prevents an accidental 20M-row browse. `limit > 100` is clamped, and the clamp is reported in metadata rather than surfaced as a 400.
- **No separate getter**, because the detail route returns nothing that search does not. `record_id` covers lookup and saves one tool schema in every session.

### `odp_search_petition_decisions`

```python
@tool()
async def odp_search_petition_decisions(
    query: Optional[str] = None,          # Lucene over ocrSearchText and other fields
    app_num: Optional[str] = None,
    patent_number: Optional[str] = None,
    petition_type: Optional[str] = None,  # numeric code ("533") or words in the description ("revive")
    outcome: Optional[str] = None,        # GRANTED | DISMISSED | DENIED | GRANTED-IN-PART
    deciding_office: Optional[str] = None,
    technology_center: Optional[str] = None,
    date_from: Optional[str] = None,      # decisionDate range
    date_to: Optional[str] = None,
    final_only: bool = False,
    record_id: Optional[str] = None,
    sort: str = "newest",
    offset: int = 0,
    limit: int = 25,
) -> Dict[str, Any]:
```

- **Docstring**: reviving abandoned applications, reinstating patents after missed maintenance fees, delayed priority claims, petitions to make special, and supervisory review of examiners. Also how the Office of Petitions has ruled on an argument, found through `query`. The decision letter itself comes from `odp_download_document(app_num, document_id)`.
- **Result per hit**: identifiers, dates, petition type code and text, outcome, deciding office, final and court-action flags, TC and art unit, entity status, title, inventors, application status, `text` (the snippet, highlights converted to `«term»`), and `documents` passed through the existing `_summarize_document`. `allSearchableFields` is dropped.
- **Metadata**: facets on outcome, deciding office and petition type, which give grant rates for a petition type in one call.

### Shared plumbing

- `constants.py`: add `OfficeActionFields` and `PetitionDecisionFields` beside `PTABFields`, plus `Defaults.ODP_SEARCH_MAX_LIMIT = 100`.
- One private helper builds the POST body (`q` from escaped clauses, `rangeFilters`, `sort`, `facets`, clamped `pagination`). It reuses the Lucene quoting already duplicated in `odp_search_applications` and `PTABClient._quote_value`; moving that quoting to `util/validation.py` is the minimal shared fix.
- Requests go through the existing `api_client.make_request(url, method="POST", data=body)`, so no new client class is needed.
- `util/response.py`: add `slim_office_action` and `slim_petition_decision`, including highlight stripping.

### Housekeeping the repo requires (CLAUDE.md, PR template)

1. Change the workaround messages in the legacy stubs `get_office_action_text` and `search_office_actions` to name the new tools. Keep the stubs, since `get_office_action_citations` and `get_office_action_rejections` wait on Phase 3.
2. Under `check_api_status`, add the two datasets as ACTIVE (ODP) and keep the developer.uspto.gov OA entry UNAVAILABLE.
3. In `resources.py`, rewrite the `office_actions` source entry and add `petition_decisions`.
4. In `prompts.py`, add `odp_search_office_actions` to the prosecution-history steps (lines ~107–120, ~356). The note "dedicated Office Action APIs were decommissioned" becomes false and must go.
5. In README, update the tool count (38 → 40), the API Sources table, the features list and the version history. Add a line on the ODP profile requirement (below).
6. In CLAUDE.md, add an "ODP office actions and petitions (verified live 2026-10-14)" contract paragraph like the existing PPUBS and TSDR ones, and update the counts.
7. Bump the version to 1.6.0 in `pyproject.toml` and `config.py` USER_AGENT.

### Tests

- Fixtures in `test/fixtures/odp_office_action_responses.py` and `odp_petition_responses.py`, trimmed from the live responses captured during this plan.
- Unit tests:
  - query building and escaping, including a `"` in `query` values
  - the AND semantics of `rejection_type`
  - clamping `limit` to 100
  - converting the `MISSING_FILTER` error
  - mapping 404 to an empty success
  - resolving `patent_number` → `app_num`, including a patent with no match
  - stripping highlights
  - dropping `allSearchableFields`
  - renaming `document_id`
- Update the tool count in `test_mcp_server.py`, and use the in-memory `mcp.client.Client` to confirm both tools register with read-only annotations.
- Integration tests (`-m integration`): one known CTFR, one known 533 petition, and one facet-only count query.

## Phase 2: full office action text (spike first)

Without full text, an LLM user still has to decode a base64 PDF. The file wrapper offers an `XML` download (`/download/applications/{app}/{id}/xmlarchive`) for office actions. It redirects to `data-documents.uspto.gov`, which this session's network policy blocks, so its format is unverified.

- **Spike**: download three xmlarchives (a CTNF, a CTFR, a NOA). Record the container format (zip or bare XML) and whether the body text is present and clean.
- **If yes**: add `format: "pdf" | "text"` to `odp_download_document`. `text` would fetch the XML, extract the body, and cap it at the existing response-size limit. This option beats a new tool, because it covers every document type that offers XML, including applicant remarks (REM).
- **If no**: return to PDF text extraction. That path adds a dependency, which CLAUDE.md asks us to justify, so it needs a separate decision.

## Phase 3: revive citations and rejections (separate PR)

- Rewrite `OfficeActionClient` for `/api/v1/patent/oa/oa_{citations,rejections}/v2/records` with form-encoded `criteria/start/rows`. Annotate the `developer.uspto.gov` paths as dead.
- Promote `get_office_action_rejections` and `get_office_action_citations` from `@legacy_tool()` to `@tool()`. Keep their names so existing users' prompts still work. The rejection rows' Alice, Mayo, Myriad and Bilski flags and claim arrays give claim-level §101 analytics that the Phase 1 tool cannot.
- Undo the decommission steps in reverse: the status entry, the resources, the unavailability tests (remove these two from the parametrized list), and the counts.

## Risks and how each would show itself

| Risk | Evidence that would show it | Mitigation |
| --- | --- | --- |
| `obsoleteDocumentIdentifier` does not always equal the file-wrapper ID | `odp_download_document` 404s on search hits | Integration test over ~20 random hits before release; fall back to listing `odp_get_documents` filtered by code and date |
| The 500-character cap belongs to a key tier or a parameter, not the API | A documented `fields`/`includeText` switch or a different key returns longer text | Read the Swagger spec at data.uspto.gov/swagger (blocked here) before coding; the tool's design does not depend on the cap |
| ODP deactivates keys for incomplete customer profiles | 401/403 on keys that worked before | Map 401/403 to a message telling users to complete their data.uspto.gov profile (job title, organization, intended use), as the alert asks |
| Coverage is thinner than "filed since 2001" | Facet counts by year fall off before ~2010 | State observed coverage in docstrings ("records from 2007 on"), not the press-release claim |
| Petition `ocrSearchText` is noisy OCR ("EENITED STATES") | Exact-phrase queries miss | Docstring suggests proximity or term queries over exact phrases |

## Out of scope

- Bulk downloads (`/search/download`). The JSON form omits the text fields, and bulk export does not fit a chat tool.
- Markmanator ingestion. Both datasets hold only USPTO-side papers. Prosecution disclaimer usually arises from the applicant's remarks (REM), which only the file wrapper holds, so Markmanator's `prosecution` and `disclaimer` channels still need `odp_get_documents` plus Phase 2 text.

## Implementation notes (Phase 1, 2026-10-14)

Phase 1 shipped as planned, with four changes that live checks forced or allowed:

- **Outcome filters on the code, not the text.** `decidedPetitionTypeCodeDescriptionText:"GRANTED"` matched 883,142 records, because the field is analyzed and also matches GRANTED-IN-PART. The tool filters on `decidedPetitionTypeCode` (A granted, B granted-in-part, C denied, D dismissed), which is exact.
- **`allSearchableFields` holds the full decision text.** The plan dropped it as a repeat of the record. It also carries the decision letter's full OCR text (about 1.3k–2.8k characters on 20 sampled decisions), so `include_full_text=True` returns it as `full_text`. The default still drops it.
- **The first risk did not materialize.** `obsoleteDocumentIdentifier` matched a file-wrapper `documentIdentifier` on 12 of 12 hits sampled from January 2015, in addition to 18402543.
- **No `rangeFilters`.** Date ranges go into `q` as `field:[from TO to]`, as `odp_search_applications` already does; dates are validated as YYYY-MM-DD before they reach the query.

Phases 2 and 3 remain open.

## Implementation notes (Phase 2, 2026-10-14)

The spike answered "yes", so `odp_download_document` gained `format="text"` instead of a new tool.

- **Container.** `/xmlarchive` answers 302 to `data-documents.uspto.gov`, which this environment can reach. It returns a POSIX tar holding one XML file. Applicant papers also carry an `_svg.zip` of page images.
- **Coverage.** XML was offered for CTNF, CTFR, NOA, PETDEC, REM, CLM, IDS, SPEC, ABST and PET.PCT papers back to 2011. Notices such as ISSUE.NTF have none and answer 404 "No files were found".
- **Schemas.** Eleven samples used four schemas: ST96 `OutgoingDocument` (USPTO papers), ST96 `IncomingDocument`/`ClaimsDocument` (applicant papers since about 2018), an older `pat:` `IncomingDocument` (2016), and red-book `us-patent-application` claims (2012). One extractor keyed on local tag names handles all four, so no new dependency was needed.
- **Quality.** USPTO papers come out clean. Applicant papers are OCR text; `OCRConfidenceData` wraps low-confidence characters inline, and old claims can include the page header in the first claim. Claim amendments keep `com:Ins`/`com:Del`, rendered `++…++`/`~~…~~`.
- **Size.** A final rejection was 16k characters and a specification 59k. Pages of 24k characters fit the default 8,000-token response budget.

Phase 3 remains open.
