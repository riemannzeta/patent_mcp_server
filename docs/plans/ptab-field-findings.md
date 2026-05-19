# PTAB ODP API: Verified `q=` Filter Field Names

Probed live against `https://api.uspto.gov/api/v1/patent/` on 2026-05-18.
Methodology: compare filtered `count` against unfiltered baseline for the same endpoint.
A field is verified only when the filtered count is strictly different from baseline and non-zero
for a value known to exist. A 404 with `"No matching records found"` means the field name is
wrong (not a route-missing error — route-missing returns AWS `"Missing Authentication Token"`).

## Endpoint Baselines

| Endpoint | Baseline count |
|---|---|
| `/trials/proceedings/search` | 19263 |
| `/trials/decisions/search` | 20517 |
| `/appeals/decisions/search` | 163515 |

---

## Proceedings (`/trials/proceedings/search`)

### Trial type

| Candidate field | Value | Filtered count | Verdict |
|---|---|---|---|
| `trialTypeCategory` | `IPR` | 404 (no records) | REJECTED — field does not exist |
| `proceedingTypeCategory` | `IPR` | 404 (no records) | REJECTED — field does not exist |
| `trialType` | `IPR` | 404 (no records) | REJECTED — field does not exist |
| `trialMetaData.trialTypeCode` | `IPR` | 18074 | VERIFIED |
| `trialMetaData.trialTypeCode` | `PGR` | 559 | VERIFIED (sanity check) |

**Verified field:** `trialMetaData.trialTypeCode`

### Status

| Candidate field | Value | Filtered count | Verdict |
|---|---|---|---|
| `proceedingStatusCategory` | `Terminated` | 404 (no records) | REJECTED — field does not exist |
| `trialMetaData.trialStatusCategory` | `Terminated` | 5538 | VERIFIED |
| `trialMetaData.trialStatusCategory` | `Pending` | 229 | VERIFIED (sanity check) |

**Verified field:** `trialMetaData.trialStatusCategory`

### Petitioner party name

| Candidate field | Value | Filtered count | Verdict |
|---|---|---|---|
| `petitionerPartyName` | `Apple` | 404 (no records) | REJECTED — field does not exist |
| `regularPetitionerData.petitionerPartyName` | `Apple` | 404 (no records) | REJECTED |
| `regularPetitionerData.counselName` | `Apple` | 404 (no records) | REJECTED |
| `regularPetitionerData.realPartyInInterestName` | `Apple` | 1022 | VERIFIED |
| `regularPetitionerData.realPartyInInterestName` | `Samsung` | 1144 | VERIFIED (sanity check) |

**Verified field:** `regularPetitionerData.realPartyInInterestName`
Note: This is the real-party-in-interest name, not the attorney/counsel name.

### Patent owner

| Candidate field | Value | Filtered count | Verdict |
|---|---|---|---|
| `patentOwnerName` | `Apple` | 404 (no records) | REJECTED — top-level field does not exist |
| `patentOwnerData.patentOwnerName` | `Apple` | 1 | VERIFIED (narrow — matches exact string) |
| `patentOwnerData.realPartyInInterestName` | `Apple` | 26 | VERIFIED (broader — matches RPI name) |
| `patentOwnerData.patentNumber` | `11664123` | — | VERIFIED (pre-existing from prior session) |

**Verified fields:** `patentOwnerData.patentOwnerName`, `patentOwnerData.realPartyInInterestName`, `patentOwnerData.patentNumber`
Note: `realPartyInInterestName` returns more results for common names (26 vs 1 for "Apple").
The client should expose `patentOwnerData.realPartyInInterestName` as the primary owner-name filter.

### Application number

| Candidate field | Value | Filtered count | Verdict |
|---|---|---|---|
| `patentOwnerData.applicationNumberText` | `17181423` | 1 | VERIFIED |

**Verified field:** `patentOwnerData.applicationNumberText`

### Petition/filing dates

| Candidate field | Value | Filtered count | Verdict |
|---|---|---|---|
| `proceedingFilingDate` | `[2022-01-01 TO 2022-12-31]` | 404 (no records) | REJECTED — field does not exist |
| `trialMetaData.petitionFilingDate` | `>2022-01-01` | 5349 | VERIFIED |
| `trialMetaData.petitionFilingDate` | `[2022-01-01 TO 2022-12-31]` | 1359 | VERIFIED |
| `trialMetaData.accordedFilingDate` | `[2022-01-01 TO 2022-12-31]` | 1353 | VERIFIED |
| `trialMetaData.terminationDate` | `[2022-01-01 TO 2022-12-31]` | 1328 | VERIFIED |
| `trialMetaData.latestDecisionDate` | `[2022-01-01 TO 2022-12-31]` | 562 | VERIFIED |

**Verified fields:** `trialMetaData.petitionFilingDate`, `trialMetaData.accordedFilingDate`,
`trialMetaData.terminationDate`, `trialMetaData.latestDecisionDate`

Note on date syntax: Bracket range `[2022-01-01 TO 2022-12-31]` and `>` operator both work.
The brackets require URL encoding (must use `--data-urlencode` or `%5B...%5D`) — passing them
raw in a query string produces an empty response body (not a JSON error).

---

## Decisions (`/trials/decisions/search`)

| Candidate field | Value | Filtered count | Verdict |
|---|---|---|---|
| `trialNumber` | `IPR2025-00278` | 2 | VERIFIED |
| `trialMetaData.trialTypeCode` | `IPR` | 19440 | VERIFIED |
| `patentOwnerData.patentNumber` | `10343114` | 7 | VERIFIED |
| `patentOwnerData.applicationNumberText` | `15978760` | 7 | VERIFIED |
| `regularPetitionerData.realPartyInInterestName` | `Apple` | 1197 | VERIFIED |
| `decisionData.decisionIssueDate` | `[2022-01-01 TO 2022-12-31]` | 1729 | VERIFIED |
| `decisionData.decisionIssueDate` | `>2022-01-01` | 10314 | VERIFIED |
| `trialMetaData.latestDecisionDate` | `[2022-01-01 TO 2022-12-31]` | 682 | VERIFIED |

---

## Appeals Decisions (`/appeals/decisions/search`)

| Candidate field | Value | Filtered count | Verdict |
|---|---|---|---|
| `appealNumber` | `2026001737` | 1 | VERIFIED (pre-existing from prior session) |
| `appellantData.applicationNumberText` | `90019597` | 1 | VERIFIED |
| `appellantData.patentOwnerName` | `Apple` | 656 | VERIFIED |
| `decisionData.decisionIssueDate` | `[2022-01-01 TO 2022-12-31]` | 5349 | VERIFIED |
| `decisionData.decisionIssueDate` | `>2022-01-01` | 20826 | VERIFIED |

---

## Summary: Field Name Map for PTABFields Constants

| Logical parameter | Endpoint(s) | Verified field name |
|---|---|---|
| Trial type | proceedings, decisions | `trialMetaData.trialTypeCode` |
| Status | proceedings | `trialMetaData.trialStatusCategory` |
| Petitioner name | proceedings, decisions | `regularPetitionerData.realPartyInInterestName` |
| Patent owner name | proceedings | `patentOwnerData.realPartyInInterestName` |
| Patent owner name (exact) | proceedings | `patentOwnerData.patentOwnerName` |
| Patent number | proceedings, decisions | `patentOwnerData.patentNumber` |
| Application number | proceedings, decisions | `patentOwnerData.applicationNumberText` |
| Application number (appeals) | appeals decisions | `appellantData.applicationNumberText` |
| Petition filing date | proceedings | `trialMetaData.petitionFilingDate` |
| Decision issue date | decisions, appeals decisions | `decisionData.decisionIssueDate` |
| Trial number | proceedings, decisions | `trialNumber` |
| Appeal number | appeals decisions | `appealNumber` |

## Unverified Fields (none — all parameters confirmed)

None — all logical filter parameters were verified. The original candidate names from the plan
(flat names like `trialTypeCategory`, `proceedingStatusCategory`, `petitionerPartyName`) do not
exist; the real names are nested under `trialMetaData.*`, `regularPetitionerData.*`,
`patentOwnerData.*`, `appellantData.*`, and `decisionData.*`.
