"""
MCP Prompts for USPTO Patent & Trademark Server.

Prompts provide reusable workflow templates for common patent and trademark
research tasks. Users can access these via / commands.
"""

PRIOR_ART_SEARCH_PROMPT = """
# Prior Art Search Workflow

A comprehensive prior art search helps identify existing patents and publications
relevant to an invention. Follow this structured approach:

## Step 1: Define the Invention
- Identify the key technical features
- List the problem being solved
- Note any unique aspects or improvements

## Step 2: Keyword Search (Broad)
Start with broad text searches to understand the landscape:

```
Use ppubs_search_patents and ppubs_search_applications:
- Search key terms from the invention description
- Try synonyms and alternative phrasings
- Quote phrases that must appear together (terms are AND-ed by default)
```

## Step 3: Identify Relevant CPC Codes
From initial results, identify CPC classification codes:

```
Use get_cpc_info to understand classifications:
- Note CPC codes from relevant patents found
- Look up section/subsection meanings for broader/narrower scope
```

## Step 4: CPC-Based Search (Focused)
Search within relevant CPC classifications:

```
Use ppubs_search_patents with CPC field qualifiers:
- CPC/G06N3/08 - search a specific classification
- Combine with keywords: CPC/G06N AND "transformer"
```

## Step 5: Inventor/Assignee Search
Find patents from key players in the field:

```
Use ppubs_search_patents with IN/ and AN/ qualifiers:
- IN/Smith - patents by inventor Smith
- AN/"International Business Machines" - assignee search
```

## Step 6: Examiner Citation Review
Review what prior art examiners have cited:

```
Use odp_get_documents on related applications:
- Office actions in the file wrapper list cited references
- Follow citation chains backward and forward
(Note: the dedicated citation APIs were decommissioned in early 2026.)
```

## Step 7: International Coverage
Expand to international patents:

```
Use ppubs_search_patents for PCT applications published in US:
- Search for WO (PCT) applications
- Note: USPTO tools focus on US patents and applications
```

## Tips:
- Document all searches performed for completeness
- Save relevant patent numbers for detailed review
- Check patent family relationships with odp_get_continuity
- Review full claims using ppubs_get_full_document
"""

PATENT_VALIDITY_ANALYSIS_PROMPT = """
# Patent Validity Analysis Workflow

Analyze the validity and prosecution history of a patent to assess its strength.

## Step 1: Get Patent Details
```
Use ppubs_get_patent_by_number:
- Review claims (especially independent claims)
- Note the filing and priority dates
- Identify the assignee and inventors
```

## Step 2: Review Claims
```
Use ppubs_get_full_document:
- Identify independent vs dependent claims
- Note claim scope and key limitations
- Look for potential narrow vs broad interpretations
```

## Step 3: Examine Prosecution History
```
Use odp_get_application (with application number) to get file wrapper data:
- Review office action history
- Check amendments made during prosecution
- Note any disclaimer or terminal disclaimers
```

## Step 4: Review Office Actions
```
Use odp_get_documents and odp_get_transactions:
- Find office action documents in the file wrapper
- Understand rejection bases (102, 103, 112) from the documents
- Review applicant's arguments and claim amendments
(Note: the dedicated Office Action APIs were decommissioned in early 2026.)
```

## Step 5: Check PTAB Proceedings
```
Use ptab_search_proceedings with the patent number:
- Check for IPR, PGR, or CBM challenges
- Review institution decisions
- Examine final written decisions if available
```

## Step 6: Review Litigation History
```
Patent litigation data is not available via API. The OCE Patent
Litigation dataset (74,000+ district court cases) is a bulk download:
https://www.uspto.gov/ip-policy/economic-research/research-datasets/patent-litigation-docket-reports-data
```

## Step 7: Citation Analysis
```
Use ppubs_get_full_document:
- Review references cited on the face of the patent
- Search forward citations with ppubs_search_patents
(Note: the Enriched Citation API was decommissioned in early 2026.)
```

## Step 8: Family Analysis
```
Use odp_get_continuity:
- Identify parent/child applications
- Check for continuation claim variations
- Note any related patents with different claim scope
```

## Assessment Factors:
- Prosecution history estoppel from amendments
- Strength of prior art cited by examiner
- Survival of PTAB challenges
- Claim construction history in litigation
"""

COMPETITOR_PORTFOLIO_ANALYSIS_PROMPT = """
# Competitor Patent Portfolio Analysis Workflow

Analyze a company's patent portfolio to understand their IP position and strategy.

## Step 1: Identify Company Variations
Companies often file under different names:
```
Use ppubs_search_patents with AN/ qualifier:
- Search for company name and variations: AN/"Acme" OR AN/"Acme Corp"
- Note subsidiary names
- Also try odp_search_applications with assignee_name
```

## Step 2: Get Portfolio Overview
```
Use ppubs_search_patents with assignee filter:
- Get count of total patents (check the "total" field)
- Identify date range of filings with ISD/ ranges
- Note technology distribution by CPC codes in results
```

## Step 3: Technology Focus Analysis
```
Use ppubs_search_patents combining AN/ and CPC/ qualifiers:
- Identify top CPC codes in portfolio
- Map technology areas covered (interpret with get_cpc_info)
- Find gaps or emerging focus areas
```

## Step 4: Inventor Analysis
```
Use ppubs_search_patents with IN/ qualifier:
- Identify key inventors appearing in results
- Track inventor movement (acquired talent)
```

## Step 5: Filing Trends
```
Search with date filters:
- Analyze year-over-year filing trends (ISD/ ranges)
- Identify ramp-up or slow-down periods
- Correlate with business events if known
```

## Step 6: Trademark Portfolio
```
Use tm_search_trademarks with owner_name:
- Map the company's brand portfolio alongside its patents
- Filter status_filter="live" for active marks
- Check assignment history with tm_search_assignments
```

## Step 7: Litigation Profile
```
Patent litigation data is not available via API. Use the OCE Patent
Litigation bulk dataset for assertion/defense history:
https://www.uspto.gov/ip-policy/economic-research/research-datasets/patent-litigation-docket-reports-data
```

## Step 8: PTAB Exposure
```
Use ptab_search_proceedings with party name:
- Count IPR/PGR challenges received
- Review survival rate
- Identify vulnerable technology areas
```

## Deliverables:
- Total patent count and active patents
- Top technology areas (by CPC)
- Key patents (high citations, litigated)
- Trademark/brand portfolio summary
- Filing trend analysis
- Risk areas (PTAB challenges, invalidations)
"""

PTAB_PROCEEDING_RESEARCH_PROMPT = """
# PTAB Proceeding Research Workflow

Research Patent Trial and Appeal Board proceedings for a patent or party.

## Understanding PTAB Proceeding Types

- **IPR (Inter Partes Review)**: Challenge based on patents/publications (35 USC 102/103)
- **PGR (Post-Grant Review)**: Broader challenge within 9 months of grant
- **CBM (Covered Business Method)**: For financial service method patents (sunsetted)
- **Derivation**: Priority disputes between applications

## Step 1: Search by Patent Number
```
Use ptab_search_proceedings with patent_number:
- Find all proceedings involving the patent
- Note proceeding numbers (e.g., IPR2023-00001)
- Check status (Pending, Instituted, Terminated, FWD Entered)
```

## Step 2: Get Proceeding Details
```
Use ptab_get_proceeding:
- Review petitioner and patent owner
- Check filing date and current status
- Note challenged claims
```

## Step 3: Review Documents
```
Use ptab_get_documents:
- Get petition and patent owner response
- Review expert declarations
- Find settlement documents if terminated
```

## Step 4: Search Related Decisions
```
Use ptab_search_decisions:
- Find institution decision
- Get final written decision (FWD)
- Review any terminations or settlements
```

## Step 5: Analyze Decision
```
Use ptab_get_decision:
- Review claim-by-claim determinations
- Note key prior art relied upon
- Understand Board's reasoning
```

## Step 6: Check Appeals
```
Use ptab_search_appeals:
- Find ex parte appeal decisions
- Review CAFC appeals of PTAB decisions
```

## Step 7: Party History
```
Use ptab_search_proceedings with party_name:
- Find other proceedings involving same parties
- Identify serial petitioners
- Review party success rates
```

## Key Metrics to Track:
- Institution rate (% of petitions instituted)
- Claim survival rate (% claims surviving FWD)
- Settlement rate
- Average proceeding duration
- Serial petition patterns
"""

FREEDOM_TO_OPERATE_PROMPT = """
# Freedom to Operate (FTO) Analysis Workflow

Assess the risk of patent infringement for a product or technology.

## Step 1: Define the Product/Technology
- List all technical features and components
- Identify the country/countries of operation
- Note planned manufacturing, sale, and use locations

## Step 2: Keyword and Classification Search
```
Use ppubs_search_patents with keywords and CPC/ qualifiers:
- Search for each technical feature
- Use multiple synonyms and phrasings
- Focus on relevant CPC classifications
```

## Step 3: Identify Potentially Relevant Patents
For each patent found, evaluate:
- Is it still in force? (check expiration)
- Does it cover the geography of interest?
- Are the claims potentially reading on your product?

## Step 4: Detailed Claim Analysis
```
Use ppubs_get_full_document and ppubs_get_patent_by_number:
- Read independent claims carefully
- Compare each claim element to your product
- Document any differences (design-arounds)
```

## Step 5: Check Patent Status
```
Use odp_get_application_metadata and odp_get_transactions:
- Verify patent is not expired
- Check for maintenance fee status
- Note any terminal disclaimers
```

## Step 6: Review Prosecution History
```
Use odp_get_documents:
- Find office actions in the file wrapper
- Note any estoppel from claim amendments
- Review applicant's arguments for claim interpretation
```

## Step 7: Check Validity Challenges
```
Use ptab_search_proceedings:
- See if patents have been challenged
- Review any claim invalidations
- Note surviving claims
```

## Step 8: Assess Litigation History
```
Patent litigation data is not available via API. Use the OCE Patent
Litigation bulk dataset:
https://www.uspto.gov/ip-policy/economic-research/research-datasets/patent-litigation-docket-reports-data
```

## Risk Assessment Categories:
- **High Risk**: Claims appear to cover product, patent is valid and enforced
- **Medium Risk**: Claims may cover, some validity questions, or design-around possible
- **Low Risk**: Clear non-infringement or strong invalidity arguments
- **Clear**: No relevant patents found or all expired

## Recommended Actions by Risk Level:
- High: Consider license, design-around, or validity challenge
- Medium: Monitor, prepare non-infringement/invalidity positions
- Low: Document analysis, monitor for new patents
"""

PATENT_LANDSCAPE_PROMPT = """
# Patent Landscape Analysis Workflow

Map the patent landscape for a technology area to understand the competitive environment.

## Step 1: Define Technology Scope
- Identify the core technology area
- List related/adjacent technologies
- Define time period of interest

## Step 2: Identify Key CPC Classifications
```
Use get_cpc_info:
- Find relevant CPC codes
- Map hierarchical relationships
- Note any cross-cutting codes
```

## Step 3: Quantitative Analysis
```
Use ppubs_search_patents with CPC/ qualifiers:
- Check the "total" field for patents per CPC code
- Track filings over time with ISD/ date ranges
- Identify growth trends
```

## Step 4: Top Assignee Analysis
```
Use ppubs_search_patents combining CPC/ and AN/ qualifiers:
- Rank companies by patent count
- Calculate market share of filings
- Identify new entrants vs incumbents
```

## Step 5: Geographic Distribution
```
Use ppubs_search_patents with assignee filters:
- Compare filing volumes by assignee location
- Identify regional leaders among US filers
- Note PCT (WO) filing trends via ppubs_search_applications
```

## Step 6: Technology Clustering
Group patents into sub-categories:
- By specific CPC subclasses
- By claim feature keywords
- By application type (method, system, composition)

## Step 7: Key Patent Identification
```
Use ppubs_get_full_document on candidate patents:
- Identify foundational patents by references cited
- Search forward citations with ppubs_search_patents
(Note: the Enriched Citation API was decommissioned in early 2026.)
```

## Step 8: White Space Analysis
Identify underserved areas:
- CPC codes with low filing activity
- Technology combinations not covered
- Emerging areas with few patents

## Deliverables:
- Filing trend charts
- Top assignee rankings
- Technology taxonomy/map
- Geographic distribution
- Key/seminal patents
- White space opportunities
"""

TRADEMARK_CLEARANCE_SEARCH_PROMPT = """
# Trademark Clearance (Knockout) Search Workflow

Assess whether a proposed mark is available for use and registration by
finding existing marks that could block it.

## Step 1: Define the Proposed Mark
- The exact mark text (and any design elements)
- The goods/services it will cover
- Identify relevant Nice classes with get_trademark_class_info
  (goods are classes 1-34, services 35-45)

## Step 2: Identical-Mark Knockout Search
```
Use tm_search_trademarks:
- mark_text=<exact proposed mark>, status_filter="live"
- An identical live mark in the same class is a strong blocker
```

## Step 3: Variant Searches
Likelihood of confusion extends beyond exact matches. Search separately for:
- Phonetic equivalents (e.g., "KWIK" for "QUICK", "XPRESS" for "EXPRESS")
- Alternative spellings and plurals
- Translations of foreign-word marks (doctrine of foreign equivalents)
- The dominant word in compound marks

## Step 4: Narrow by Class and Goods/Services
```
Use tm_search_trademarks with international_class:
- Focus on the classes identified in Step 1
- Also check related/complementary classes (e.g., class 9 software
  vs class 42 software services)
Use tm_search_trademarks with goods_services:
- Search the actual goods/services wording (e.g., "athletic footwear")
  to catch marks classified differently than expected
```

## Step 5: Verify Status of Close Hits
```
Use tsdr_get_trademark_status on each concerning mark:
- Confirm live/dead status and registration details (TSDR is authoritative)
- Interpret status codes with get_trademark_status_code
- Note filing basis, dates, and goods/services descriptions
```

## Step 6: Investigate Owners of Blocking Marks
```
Use tm_search_trademarks with owner_name:
- See the owner's full portfolio (aggressive filers may oppose)
- Check ownership transfers with tm_search_assignments
```

## Step 7: Review Documents if Needed
```
Use tsdr_list_trademark_documents first:
- See what file-wrapper documents exist (metadata only, no rate limit)
Then tsdr_download_trademark_documents for the ones you need:
- Examine specimens to see how a mark is actually used
- Review office actions for examiner views on similar marks
(PDF downloads rate limited to 4/minute.)
```

## Important Caveats:
- This search covers US **federal** applications/registrations only
- Common-law (unregistered) and state-registered marks are NOT covered
- Likelihood of confusion is a legal judgment (similarity of marks,
  relatedness of goods, trade channels) — flag close calls for counsel
"""

TRADEMARK_PORTFOLIO_REVIEW_PROMPT = """
# Trademark Portfolio Review Workflow

Review a company's trademark portfolio for status, coverage, and deadlines.

## Step 1: Find the Portfolio
```
Use tm_search_trademarks with owner_name:
- Search the company name and known variations/subsidiaries
- Run once without status_filter to capture dead marks too
```

## Step 2: Check Status of Each Mark
```
Use tsdr_get_trademark_status for each mark of interest:
- Current status and prosecution stage
- Registration and renewal dates
- Goods/services and classes covered
```

## Step 3: Map Class Coverage
```
Use get_trademark_class_info:
- Tabulate which Nice classes the portfolio covers
- Identify gaps versus the company's actual products/services
```

## Step 4: Renewal Deadline Awareness
From TSDR dates, flag upcoming maintenance windows:
- **Section 8 declaration of use**: between the 5th and 6th year after
  registration (with a 6-month grace period)
- **Section 8 & 9 renewal**: every 10 years after registration
- Marks past these windows without filings risk cancellation
  (status codes 710/900 — interpret with get_trademark_status_code)

## Step 5: Ownership Verification
```
Use tm_search_assignments:
- Confirm recorded chain of title for key marks
- Find any unrecorded transfers (gaps in the chain)
- Search by registration_number for specific marks
```

## Step 6: Spot Risks
- Marks published for opposition (status 686) — opposition window open
- Office actions outstanding — pull with tsdr_download_trademark_documents
- Abandoned applications (status 602/604/606/608) for brands still in use

## Deliverables:
- Inventory of live marks with classes and renewal dates
- Gap analysis (unprotected brands or classes)
- Deadline calendar (Section 8/9 windows)
- Chain-of-title issues
"""

TRADEMARK_STATUS_MONITORING_PROMPT = """
# Trademark Status Monitoring Workflow

Track the status of trademark applications and registrations over time —
your own filings or marks you are watching.

## Step 1: Establish the Watch List
- Collect serial numbers (applications) and registration numbers
- For competitor watching, find marks with tm_search_trademarks
  (mark_text or owner_name)

## Step 2: Pull Current Status
```
Use tsdr_get_trademark_status for each watched mark:
- Record the status code and date
- Interpret codes with get_trademark_status_code
  (e.g., 630 new, 686 published for opposition, 700 registered)
```

## Step 3: Interpret Stage Transitions
Key transitions to watch for:
- **Examination → Office action** (640/644): response deadline running
  (generally 3 months, extendable)
- **Published for opposition** (686): 30-day opposition window opens
- **Notice of allowance** (688): statement of use deadline running (ITU)
- **Registered** (700): calendar Section 8/9 maintenance windows

## Step 4: Pull New Documents
```
Use tsdr_list_trademark_documents when status changes:
- Check what new documents arrived (metadata only, no PDF rate limit)
Then tsdr_download_trademark_documents for the documents you need:
- Filter by date_from to get only new documents
- Office actions, examiner amendments, suspension notices
(PDF downloads rate limited to 4/minute.)
```

## Step 5: Watch for Oppositions
TTAB proceedings (oppositions/cancellations) have no REST API:
- Case status and filings: TTABVUE web interface
- Bulk monitoring: daily TTAB XML datasets via odp_search_datasets

## Step 6: Watch for New Conflicting Filings
```
Periodically re-run tm_search_trademarks:
- mark_text variants of your marks, status_filter="live"
- New applications similar to watched marks may warrant opposition
  (file within the 30-day window after publication)
```

## Tips:
- TSDR is the authoritative status source; search-index data may lag
- Log status snapshots with dates to build a timeline
- Escalate close conflicts and approaching deadlines to counsel
"""

# Map of prompt names to content
PROMPTS = {
    "prior_art_search": {
        "name": "Prior Art Search",
        "description": "Guide for conducting a comprehensive prior art search",
        "content": PRIOR_ART_SEARCH_PROMPT,
    },
    "patent_validity": {
        "name": "Patent Validity Analysis",
        "description": "Guide for analyzing patent validity and prosecution history",
        "content": PATENT_VALIDITY_ANALYSIS_PROMPT,
    },
    "competitor_portfolio": {
        "name": "Competitor Portfolio Analysis",
        "description": "Guide for analyzing a company's patent portfolio",
        "content": COMPETITOR_PORTFOLIO_ANALYSIS_PROMPT,
    },
    "ptab_research": {
        "name": "PTAB Proceeding Research",
        "description": "Guide for researching PTAB proceedings (IPR/PGR/CBM)",
        "content": PTAB_PROCEEDING_RESEARCH_PROMPT,
    },
    "freedom_to_operate": {
        "name": "Freedom to Operate Analysis",
        "description": "Guide for FTO/infringement risk analysis",
        "content": FREEDOM_TO_OPERATE_PROMPT,
    },
    "patent_landscape": {
        "name": "Patent Landscape Analysis",
        "description": "Guide for mapping a technology patent landscape",
        "content": PATENT_LANDSCAPE_PROMPT,
    },
    "trademark_clearance": {
        "name": "Trademark Clearance Search",
        "description": "Guide for clearance/knockout searching of a proposed mark",
        "content": TRADEMARK_CLEARANCE_SEARCH_PROMPT,
    },
    "trademark_portfolio": {
        "name": "Trademark Portfolio Review",
        "description": "Guide for reviewing a trademark portfolio and deadlines",
        "content": TRADEMARK_PORTFOLIO_REVIEW_PROMPT,
    },
    "trademark_monitoring": {
        "name": "Trademark Status Monitoring",
        "description": "Guide for monitoring trademark status and watching for conflicts",
        "content": TRADEMARK_STATUS_MONITORING_PROMPT,
    },
}


def get_prompt(name: str) -> dict:
    """Get a prompt by name."""
    if name in PROMPTS:
        return PROMPTS[name]
    return {"error": f"Unknown prompt: {name}"}


def list_prompts() -> dict:
    """List all available prompts."""
    return {
        name: {"name": p["name"], "description": p["description"]}
        for name, p in PROMPTS.items()
    }
