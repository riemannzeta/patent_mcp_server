"""
MCP Resources for USPTO Patent Server.

Resources provide read-only access to static or semi-static data that
can be referenced by Claude without triggering tool calls.
"""

# CPC Classification data - main sections
CPC_SECTIONS = {
    "A": {
        "title": "Human Necessities",
        "description": "Agriculture, foodstuffs, personal/domestic articles, health, amusement",
        "subsections": {
            "A01": "Agriculture; Forestry; Animal Husbandry; Hunting; Trapping; Fishing",
            "A21": "Baking; Edible Doughs",
            "A22": "Butchering; Meat Treatment; Processing Poultry or Fish",
            "A23": "Foods or Foodstuffs; Treatment Thereof",
            "A24": "Tobacco; Cigars; Cigarettes; Simulated Smoking Devices",
            "A41": "Wearing Apparel",
            "A42": "Headwear",
            "A43": "Footwear",
            "A44": "Haberdashery; Jewellery",
            "A45": "Hand or Travelling Articles",
            "A46": "Brushware",
            "A47": "Furniture; Domestic Articles or Appliances; Coffee Mills; Spice Mills",
            "A61": "Medical or Veterinary Science; Hygiene",
            "A62": "Life-Saving; Fire-Fighting",
            "A63": "Sports; Games; Amusements",
            "A99": "Subject Matter Not Otherwise Provided For In This Section",
        }
    },
    "B": {
        "title": "Performing Operations; Transporting",
        "description": "Separating, mixing, shaping, printing, transporting, handling",
        "subsections": {
            "B01": "Physical or Chemical Processes or Apparatus in General",
            "B02": "Crushing, Pulverising, or Disintegrating",
            "B03": "Separation of Solid Materials",
            "B04": "Centrifugal Apparatus or Machines",
            "B05": "Spraying or Atomising; Applying Liquids or Other Fluent Materials",
            "B06": "Generating or Transmitting Mechanical Vibrations",
            "B07": "Separating Solids from Solids",
            "B08": "Cleaning",
            "B09": "Disposal of Solid Waste; Reclamation of Contaminated Soil",
            "B21": "Mechanical Metal-Working Without Essentially Removing Material",
            "B22": "Casting; Powder Metallurgy",
            "B23": "Machine Tools; Metal-Working Not Otherwise Provided For",
            "B24": "Grinding; Polishing",
            "B25": "Hand Tools; Portable Power-Driven Tools",
            "B26": "Hand Cutting Tools; Cutting; Severing",
            "B27": "Working or Preserving Wood",
            "B28": "Working Cement, Clay, or Stone",
            "B29": "Working of Plastics",
            "B30": "Presses",
            "B31": "Making Paper Articles; Working Paper",
            "B32": "Layered Products",
            "B33": "Additive Manufacturing Technology",
            "B41": "Printing; Lining Machines; Typewriters; Stamps",
            "B42": "Bookbinding; Albums; Filing; Special Printed Matter",
            "B43": "Writing or Drawing Implements",
            "B44": "Decorative Arts",
            "B60": "Vehicles in General",
            "B61": "Railways",
            "B62": "Land Vehicles for Travelling Otherwise Than on Rails",
            "B63": "Ships or Other Waterborne Vessels",
            "B64": "Aircraft; Aviation; Cosmonautics",
            "B65": "Conveying; Packing; Storing; Handling Thin or Filamentary Material",
            "B66": "Hoisting; Lifting; Hauling",
            "B67": "Opening or Closing Bottles, Jars or Similar Containers",
            "B68": "Saddlery; Upholstery",
            "B81": "Microstructural Technology",
            "B82": "Nanotechnology",
            "B99": "Subject Matter Not Otherwise Provided For In This Section",
        }
    },
    "C": {
        "title": "Chemistry; Metallurgy",
        "description": "Chemistry, metallurgy, combinatorial technology",
        "subsections": {
            "C01": "Inorganic Chemistry",
            "C02": "Treatment of Water, Waste Water, Sewage, or Sludge",
            "C03": "Glass; Mineral or Slag Wool",
            "C04": "Cements; Concrete; Artificial Stone; Ceramics; Refractories",
            "C05": "Fertilisers; Manufacture Thereof",
            "C06": "Explosives; Matches",
            "C07": "Organic Chemistry",
            "C08": "Organic Macromolecular Compounds",
            "C09": "Dyes; Paints; Polishes; Natural Resins; Adhesives",
            "C10": "Petroleum, Gas or Coke Industries",
            "C11": "Animal or Vegetable Oils, Fats, Fatty Substances or Waxes",
            "C12": "Biochemistry; Beer; Spirits; Wine; Vinegar; Microbiology",
            "C13": "Sugar Industry",
            "C14": "Skins; Hides; Pelts; Leather",
            "C21": "Metallurgy of Iron",
            "C22": "Metallurgy; Ferrous or Non-Ferrous Alloys",
            "C23": "Coating Metallic Material",
            "C25": "Electrolytic or Electrophoretic Processes",
            "C30": "Crystal Growth",
            "C40": "Combinatorial Technology",
            "C99": "Subject Matter Not Otherwise Provided For In This Section",
        }
    },
    "D": {
        "title": "Textiles; Paper",
        "description": "Textiles, flexible materials, paper making",
        "subsections": {
            "D01": "Natural or Man-Made Threads or Fibres; Spinning",
            "D02": "Yarns; Mechanical Finishing of Yarns or Ropes",
            "D03": "Weaving",
            "D04": "Braiding; Lace-Making; Knitting; Trimmings",
            "D05": "Sewing; Embroidering; Tufting",
            "D06": "Treatment of Textiles; Laundering; Flexible Materials",
            "D07": "Ropes; Cables Other Than Electric",
            "D21": "Paper-Making; Production of Cellulose",
            "D99": "Subject Matter Not Otherwise Provided For In This Section",
        }
    },
    "E": {
        "title": "Fixed Constructions",
        "description": "Building, mining, earth drilling",
        "subsections": {
            "E01": "Construction of Roads, Railways, or Bridges",
            "E02": "Hydraulic Engineering; Foundations; Soil-Shifting",
            "E03": "Water Supply; Sewerage",
            "E04": "Building",
            "E05": "Locks; Keys; Window or Door Fittings; Safes",
            "E06": "Doors, Windows, Shutters, or Roller Blinds",
            "E21": "Earth or Rock Drilling; Mining",
            "E99": "Subject Matter Not Otherwise Provided For In This Section",
        }
    },
    "F": {
        "title": "Mechanical Engineering; Lighting; Heating; Weapons; Blasting",
        "description": "Engines, pumps, engineering, lighting, heating, weapons",
        "subsections": {
            "F01": "Machines or Engines in General",
            "F02": "Combustion Engines",
            "F03": "Machines or Engines for Liquids; Wind, Spring, or Weight Motors",
            "F04": "Positive-Displacement Machines for Liquids; Pumps",
            "F15": "Fluid-Pressure Actuators; Hydraulics or Pneumatics",
            "F16": "Engineering Elements or Units",
            "F17": "Storing or Distributing Gases or Liquids",
            "F21": "Lighting",
            "F22": "Steam Generation",
            "F23": "Combustion Apparatus; Combustion Processes",
            "F24": "Heating; Ranges; Ventilating",
            "F25": "Refrigeration or Cooling",
            "F26": "Drying",
            "F27": "Furnaces; Kilns; Ovens; Retorts",
            "F28": "Heat Exchange in General",
            "F41": "Weapons",
            "F42": "Ammunition; Blasting",
            "F99": "Subject Matter Not Otherwise Provided For In This Section",
        }
    },
    "G": {
        "title": "Physics",
        "description": "Instruments, nucleonics, computing, data processing",
        "subsections": {
            "G01": "Measuring; Testing",
            "G02": "Optics",
            "G03": "Photography; Cinematography; Analogous Techniques",
            "G04": "Horology",
            "G05": "Controlling; Regulating",
            "G06": "Computing; Calculating; Counting",
            "G07": "Checking-Devices",
            "G08": "Signalling",
            "G09": "Educating; Cryptography; Display; Advertising; Seals",
            "G10": "Musical Instruments; Acoustics",
            "G11": "Information Storage",
            "G12": "Instrument Details",
            "G16": "Information and Communication Technology [ICT]",
            "G21": "Nuclear Physics; Nuclear Engineering",
            "G99": "Subject Matter Not Otherwise Provided For In This Section",
        }
    },
    "H": {
        "title": "Electricity",
        "description": "Electrical technology, electronics, communications",
        "subsections": {
            "H01": "Electric Elements",
            "H02": "Generation, Conversion, or Distribution of Electric Power",
            "H03": "Electronic Circuitry",
            "H04": "Electric Communication Technique",
            "H05": "Electric Techniques Not Otherwise Provided For",
            "H10": "Semiconductor Devices; Electric Solid-State Devices",
            "H99": "Subject Matter Not Otherwise Provided For In This Section",
        }
    },
    "Y": {
        "title": "General Tagging of New Technological Developments",
        "description": "Cross-sectional technologies spanning multiple CPC sections",
        "subsections": {
            "Y02": "Technologies for Climate Change Mitigation",
            "Y04": "Information and Communication Technologies with Potential 4IR Applications",
            "Y10": "Technical Subjects Covered by Former USPC",
        }
    },
}

# USPTO Application Status Codes
STATUS_CODES = {
    # Examination Status
    "30": {"description": "Docketed New Case - Ready for Examination", "stage": "examination"},
    "31": {"description": "Non-Final Action Mailed", "stage": "examination"},
    "32": {"description": "Final Action Mailed", "stage": "examination"},
    "33": {"description": "Response to Non-Final Office Action Entered", "stage": "examination"},
    "34": {"description": "Response after Final Action Forwarded to Examiner", "stage": "examination"},
    "35": {"description": "Advisory Action Mailed", "stage": "examination"},
    "36": {"description": "Notice of Allowance Mailed", "stage": "allowance"},
    "37": {"description": "Amendment/Argument after Notice of Allowance", "stage": "allowance"},
    "38": {"description": "Issue Fee Payment Received", "stage": "allowance"},
    "39": {"description": "Issue Fee Payment Verified", "stage": "allowance"},

    # Appeal Status
    "40": {"description": "Appeal Brief Filed", "stage": "appeal"},
    "41": {"description": "Notice of Appeal Filed", "stage": "appeal"},
    "42": {"description": "Appeal Forwarded to Board of Appeals", "stage": "appeal"},
    "43": {"description": "Board of Appeals Decision Rendered", "stage": "appeal"},
    "44": {"description": "On Appeal - Awaiting Board Decision", "stage": "appeal"},

    # Pre-Examination
    "10": {"description": "Application Received in Office of Initial Patent Exam", "stage": "pre-exam"},
    "11": {"description": "Application Dispatched from Preexam", "stage": "pre-exam"},
    "12": {"description": "Request for Continued Examination (RCE)", "stage": "examination"},

    # Post-Grant
    "50": {"description": "Patent Issued", "stage": "granted"},
    "51": {"description": "Patent Expired Due to NonPayment of Fees", "stage": "expired"},
    "52": {"description": "Reissue Application Filed", "stage": "reissue"},
    "53": {"description": "Reexamination Ordered", "stage": "reexam"},

    # Abandonment
    "60": {"description": "Abandoned - Failure to Respond to Office Action", "stage": "abandoned"},
    "61": {"description": "Abandoned - Failure to Pay Issue Fee", "stage": "abandoned"},
    "62": {"description": "Expressly Abandoned", "stage": "abandoned"},
    "63": {"description": "Abandoned - Incomplete Application", "stage": "abandoned"},

    # Publication
    "70": {"description": "Published Application", "stage": "published"},
    "71": {"description": "Non-Publication Request Acknowledged", "stage": "pre-pub"},

    # Continuity
    "80": {"description": "Continuation Application Filed", "stage": "continuity"},
    "81": {"description": "Divisional Application Filed", "stage": "continuity"},
    "82": {"description": "Continuation-in-Part Application Filed", "stage": "continuity"},
}

# Data Sources Information
DATA_SOURCES = {
    "ppubs": {
        "name": "USPTO Patent Public Search (PPUBS)",
        "base_url": "https://ppubs.uspto.gov",
        "description": "Full-text patent search with PDF downloads. Updated daily.",
        "coverage": {
            "patents": "All US patents from 1790 to present",
            "applications": "All published applications from 2001 to present",
        },
        "rate_limits": "Undocumented, but throttled for heavy usage",
        "auth_required": False,
        "best_for": [
            "Full-text patent search",
            "PDF document downloads",
            "Most recent filings (daily updates)",
            "Exact patent number lookups",
        ],
    },
    "odp": {
        "name": "USPTO Open Data Portal (ODP)",
        "base_url": "https://api.uspto.gov",
        "description": "Patent metadata, file wrapper data, continuity, assignments.",
        "coverage": {
            "applications": "Patent applications with prosecution history",
            "assignments": "Recorded patent assignments",
            "transactions": "Prosecution transaction history",
        },
        "rate_limits": "Requires API key, standard rate limits apply",
        "auth_required": True,
        "best_for": [
            "Prosecution history and file wrapper data",
            "Patent term adjustments",
            "Assignment/ownership records",
            "Attorney/agent information",
            "Continuity data (parent/child relationships)",
        ],
    },
    "patentsview": {
        "name": "PatentsView Patent Search API",
        "base_url": "https://search.patentsview.org",
        "description": "Advanced patent search with disambiguated inventor/assignee data.",
        "coverage": {
            "patents": "US granted patents from 1976 to present",
            "inventors": "Disambiguated inventor records",
            "assignees": "Disambiguated assignee/company records",
        },
        "rate_limits": "45 requests per minute",
        "auth_required": True,
        "best_for": [
            "Inventor disambiguation (linking same inventor across patents)",
            "Assignee disambiguation (company name variations)",
            "CPC classification searches",
            "Patent claims and description text",
            "Citation analysis",
        ],
    },
    "ptab": {
        "name": "USPTO PTAB API",
        "base_url": "https://api.uspto.gov/api/v1/patent/trials",
        "description": "Patent Trial and Appeal Board data - IPR, PGR, CBM proceedings.",
        "coverage": {
            "proceedings": "IPR, PGR, CBM, derivation proceedings from 2012",
            "decisions": "Institution and final written decisions",
            "appeals": "Ex parte appeal decisions",
            "interferences": "Historical interference proceedings (pre-AIA)",
        },
        "rate_limits": "Standard USPTO API limits",
        "auth_required": True,
        "best_for": [
            "IPR/PGR/CBM proceeding research",
            "PTAB decision analysis",
            "Appeal outcomes",
            "Patent validity challenges",
        ],
    },
    "office_actions": {
        "name": "USPTO Office Action APIs",
        "base_url": "https://developer.uspto.gov",
        "description": "Full-text office actions, citations, and rejection data.",
        "coverage": {
            "applications": "12-series applications from June 2018",
            "citations": "References cited in office actions",
            "rejections": "Rejection data with claim-level details",
        },
        "rate_limits": "Standard USPTO API limits",
        "auth_required": True,
        "best_for": [
            "Office action full text",
            "Examiner citation analysis",
            "Rejection pattern analysis",
            "Prosecution strategy research",
        ],
    },
    "litigation": {
        "name": "USPTO Patent Litigation API",
        "base_url": "https://api.uspto.gov/api/v1/patent/litigation",
        "description": "District court patent litigation case records.",
        "coverage": {
            "cases": "74,000+ district court cases",
            "date_range": "Historical litigation records",
        },
        "rate_limits": "Standard USPTO API limits",
        "auth_required": True,
        "best_for": [
            "Patent litigation history",
            "Company litigation profiles",
            "Patent enforcement patterns",
        ],
    },
}

# Search Query Syntax Guide
SEARCH_SYNTAX_GUIDE = """
# Patent Search Query Syntax Guide

## PPUBS (Patent Public Search)

PPUBS uses a field-based search syntax:

### Common Fields:
- `TTL/` - Title
- `ABST/` - Abstract
- `ACLM/` - All Claims
- `SPEC/` - Specification/Description
- `ISD/` - Issue Date (format: YYYYMMDD)
- `APD/` - Application Date
- `IN/` - Inventor Name
- `AN/` - Assignee Name
- `PN/` - Patent Number
- `CPC/` - CPC Classification

### Example Queries:
- `TTL/"machine learning"` - Title contains "machine learning"
- `IN/Smith AND AN/IBM` - Inventor Smith, assigned to IBM
- `CPC/G06N3/08` - Neural network patents
- `ISD/20230101->20231231` - Patents issued in 2023

---

## PatentsView

PatentsView uses JSON query syntax:

### Operators:
- `_eq` - Equals
- `_neq` - Not equals
- `_gt`, `_gte` - Greater than (or equal)
- `_lt`, `_lte` - Less than (or equal)
- `_begins` - Starts with
- `_contains` - Contains
- `_text_any` - Full-text match any word
- `_text_all` - Full-text match all words
- `_text_phrase` - Full-text exact phrase

### Example Queries:
```json
{"patent_title": {"_contains": "neural network"}}
{"_and": [
    {"patent_date": {"_gte": "2020-01-01"}},
    {"assignee_organization": {"_contains": "IBM"}}
]}
{"_or": [
    {"_text_any": {"patent_title": "machine learning"}},
    {"_text_any": {"patent_abstract": "machine learning"}}
]}
```

---

## ODP (Open Data Portal)

### Application Search:
- `q` - General query string
- `applicationNumberText` - Application number
- `patentNumber` - Patent number
- `inventorName` - Inventor name
- `assigneeName` - Assignee name
- `appFilingDate` - Filing date range

### Example:
`q=machine learning&appFilingDate=2020-01-01,2023-12-31`

---

## Common Tips:

1. **Use quotes for phrases**: "neural network" vs neural network
2. **Combine with AND/OR**: term1 AND term2, term1 OR term2
3. **Use wildcards carefully**: wildcard* searches can be slow
4. **Filter by date**: Narrow results with date ranges
5. **Use CPC codes**: Most precise for technology areas
"""


def get_cpc_section_info(section: str) -> dict:
    """Get information about a CPC section."""
    section = section.upper()
    if section in CPC_SECTIONS:
        return CPC_SECTIONS[section]
    return {"error": f"Unknown CPC section: {section}"}


def get_cpc_subsection_info(code: str) -> dict:
    """Get information about a CPC subsection."""
    code = code.upper()
    section = code[0] if code else ""

    if section in CPC_SECTIONS:
        subsections = CPC_SECTIONS[section].get("subsections", {})
        # Try exact match first
        if code in subsections:
            return {
                "code": code,
                "section": section,
                "section_title": CPC_SECTIONS[section]["title"],
                "subsection_title": subsections[code],
            }
        # Try prefix match for more specific codes
        for prefix, title in subsections.items():
            if code.startswith(prefix):
                return {
                    "code": code,
                    "matched_prefix": prefix,
                    "section": section,
                    "section_title": CPC_SECTIONS[section]["title"],
                    "subsection_title": title,
                }

    return {"error": f"Unknown CPC code: {code}"}


def get_status_code_info(code: str) -> dict:
    """Get information about a USPTO status code."""
    if code in STATUS_CODES:
        info = STATUS_CODES[code].copy()
        info["code"] = code
        return info
    return {"error": f"Unknown status code: {code}"}


def get_all_status_codes() -> dict:
    """Get all USPTO status codes."""
    return STATUS_CODES


def get_data_source_info(source: str) -> dict:
    """Get information about a data source."""
    source = source.lower()
    if source in DATA_SOURCES:
        return DATA_SOURCES[source]
    return {"error": f"Unknown data source: {source}"}


def get_all_data_sources() -> dict:
    """Get all data source information."""
    return DATA_SOURCES


def get_search_syntax_guide() -> str:
    """Get the search syntax guide."""
    return SEARCH_SYNTAX_GUIDE
