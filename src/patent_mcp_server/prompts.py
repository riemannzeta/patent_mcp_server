"""
MCP Prompts for USPTO Patent Server.

Prompts provide reusable workflow templates for common patent research tasks.
Users can access these via / commands.
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
Use patentsview_search_patents or ppubs_search_patents:
- Search key terms from the invention description
- Try synonyms and alternative phrasings
- Use search_type="any" for broad results first
```

## Step 3: Identify Relevant CPC Codes
From initial results, identify CPC classification codes:

```
Use patentsview_lookup_cpc to understand classifications:
- Note CPC codes from relevant patents found
- Look up parent/child codes for broader/narrower scope
```

## Step 4: CPC-Based Search (Focused)
Search within relevant CPC classifications:

```
Use patentsview_search_by_cpc:
- Focus on identified CPC codes
- Combine with keywords if needed
```

## Step 5: Inventor/Assignee Search
Find patents from key players in the field:

```
Use patentsview_search_inventors and patentsview_search_assignees:
- Search for prolific inventors in the field
- Find competitors' patent portfolios
```

## Step 6: Citation Analysis
Review what prior art examiners have cited:

```
Use get_office_action_citations:
- Check citations from related applications
- Follow citation chains backward and forward
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
- Check patent family relationships with get_app_continuity
- Review full claims using patentsview_get_claims
"""

PATENT_VALIDITY_ANALYSIS_PROMPT = """
# Patent Validity Analysis Workflow

Analyze the validity and prosecution history of a patent to assess its strength.

## Step 1: Get Patent Details
```
Use ppubs_get_patent_by_number or patentsview_get_patent:
- Review claims (especially independent claims)
- Note the filing and priority dates
- Identify the assignee and inventors
```

## Step 2: Review Claims
```
Use patentsview_get_claims:
- Identify independent vs dependent claims
- Note claim scope and key limitations
- Look for potential narrow vs broad interpretations
```

## Step 3: Examine Prosecution History
```
Use get_app (with application number) to get file wrapper data:
- Review office action history
- Check amendments made during prosecution
- Note any disclaimer or terminal disclaimers
```

## Step 4: Review Office Actions
```
Use get_office_action_text and get_office_action_rejections:
- See what prior art examiner cited
- Understand rejection bases (102, 103, 112)
- Review applicant's arguments and claim amendments
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
Use get_patent_litigation_history:
- Check for past infringement suits
- Review outcomes and claim construction rulings
- Note any settlements or licensing
```

## Step 7: Citation Analysis
```
Use get_enriched_citations:
- Review forward citations (indicator of importance)
- Check backward citations for prior art
- Analyze citation metrics
```

## Step 8: Family Analysis
```
Use get_app_continuity:
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
Use patentsview_search_assignees:
- Search for company name and variations
- Note subsidiary names
- Record disambiguated assignee IDs
```

## Step 2: Get Portfolio Overview
```
Use patentsview_search with assignee filter:
- Get count of total patents
- Identify date range of filings
- Note technology distribution by CPC
```

## Step 3: Technology Focus Analysis
```
Use patentsview_search_by_cpc:
- Identify top CPC codes in portfolio
- Map technology areas covered
- Find gaps or emerging focus areas
```

## Step 4: Inventor Analysis
```
Use patentsview_search_inventors:
- Identify key inventors
- Track inventor movement (acquired talent)
- Find prolific inventors by patent count
```

## Step 5: Filing Trends
```
Search with date filters:
- Analyze year-over-year filing trends
- Identify ramp-up or slow-down periods
- Correlate with business events if known
```

## Step 6: Citation Analysis
```
Use get_enriched_citations on key patents:
- Identify most-cited patents (crown jewels)
- Find citation relationships with competitors
- Analyze technology influence
```

## Step 7: Litigation Profile
```
Use get_party_litigation_history:
- Review assertion history (offensive use)
- Check defense cases (being sued)
- Identify frequent opponents
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
Use ptab_get_proceeding_documents:
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
Use patentsview_search and patentsview_search_by_cpc:
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
Use patentsview_get_claims and ppubs_get_patent_by_number:
- Read independent claims carefully
- Compare each claim element to your product
- Document any differences (design-arounds)
```

## Step 5: Check Patent Status
```
Use get_app_metadata and get_app_transactions:
- Verify patent is not expired
- Check for maintenance fee status
- Note any terminal disclaimers
```

## Step 6: Review Prosecution History
```
Use get_office_action_text and get_office_action_rejections:
- Understand scope limitations from prosecution
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
Use get_patent_litigation_history:
- Check if patent has been asserted
- Review claim construction rulings
- Note any licenses or settlements
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
Use patentsview_lookup_cpc:
- Find relevant CPC codes
- Map hierarchical relationships
- Note any cross-cutting codes
```

## Step 3: Quantitative Analysis
```
Use patentsview_search_by_cpc with large limits:
- Count total patents per CPC code
- Track filings over time
- Identify growth trends
```

## Step 4: Top Assignee Analysis
```
Use patentsview_search_assignees:
- Rank companies by patent count
- Calculate market share of filings
- Identify new entrants vs incumbents
```

## Step 5: Geographic Distribution
```
Use patentsview_search_patents with assignee filters:
- Compare filing volumes by assignee location
- Identify regional leaders among US filers
- Note PCT (WO) filing trends via ppubs_search_applications
```

## Step 6: Technology Clustering
Group patents into sub-categories:
- By specific CPC subclasses
- By claim feature keywords
- By application type (method, system, composition)

## Step 7: Citation Network Analysis
```
Use get_enriched_citations:
- Identify highly-cited foundational patents
- Map citation relationships
- Find technology leaders by citation metrics
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
