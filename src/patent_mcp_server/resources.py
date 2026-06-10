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

# Nice Classification - International trademark classes (goods 1-34, services 35-45)
NICE_CLASSES = {
    "1": {"title": "Chemicals", "type": "goods", "description": "Chemicals for industry, science, photography, agriculture; unprocessed plastics; fertilizers; adhesives for industry"},
    "2": {"title": "Paints", "type": "goods", "description": "Paints, varnishes, lacquers; preservatives against rust; colorants, dyes; raw natural resins; printing inks"},
    "3": {"title": "Cosmetics and Cleaning Preparations", "type": "goods", "description": "Cleaning, polishing and abrasive preparations; soaps; perfumery, essential oils, cosmetics, hair lotions; dentifrices"},
    "4": {"title": "Lubricants and Fuels", "type": "goods", "description": "Industrial oils and greases; lubricants; fuels and illuminants; candles and wicks"},
    "5": {"title": "Pharmaceuticals", "type": "goods", "description": "Pharmaceutical and veterinary preparations; sanitary preparations; dietetic food and supplements; plasters; disinfectants"},
    "6": {"title": "Metal Goods", "type": "goods", "description": "Common metals and their alloys; metal building materials; pipes and tubes of metal; small items of metal hardware"},
    "7": {"title": "Machinery", "type": "goods", "description": "Machines and machine tools; motors and engines (except for land vehicles); agricultural implements; vending machines"},
    "8": {"title": "Hand Tools", "type": "goods", "description": "Hand tools and implements (hand-operated); cutlery; side arms; razors"},
    "9": {"title": "Electrical and Scientific Apparatus", "type": "goods", "description": "Scientific, measuring, signalling apparatus; computers and computer software; data processing equipment; recorded media"},
    "10": {"title": "Medical Apparatus", "type": "goods", "description": "Surgical, medical, dental and veterinary apparatus and instruments; artificial limbs; orthopedic articles; suture materials"},
    "11": {"title": "Environmental Control Apparatus", "type": "goods", "description": "Apparatus for lighting, heating, steam generating, cooking, refrigerating, drying, ventilating, water supply and sanitary purposes"},
    "12": {"title": "Vehicles", "type": "goods", "description": "Vehicles; apparatus for locomotion by land, air or water"},
    "13": {"title": "Firearms", "type": "goods", "description": "Firearms; ammunition and projectiles; explosives; fireworks"},
    "14": {"title": "Jewelry", "type": "goods", "description": "Precious metals and their alloys; jewelry, precious and semi-precious stones; horological and chronometric instruments"},
    "15": {"title": "Musical Instruments", "type": "goods", "description": "Musical instruments; music stands and stands for musical instruments; conductors' batons"},
    "16": {"title": "Paper Goods and Printed Matter", "type": "goods", "description": "Paper and cardboard; printed matter; bookbinding material; photographs; stationery; office requisites; instructional materials"},
    "17": {"title": "Rubber Goods", "type": "goods", "description": "Unprocessed rubber, gutta-percha, gum, asbestos, mica; plastics in extruded form; packing and insulating materials; flexible pipes"},
    "18": {"title": "Leather Goods", "type": "goods", "description": "Leather and imitations of leather; animal skins; luggage and carrying bags; umbrellas and parasols; saddlery"},
    "19": {"title": "Non-metallic Building Materials", "type": "goods", "description": "Building materials (non-metallic); non-metallic rigid pipes; asphalt, pitch and bitumen; non-metallic transportable buildings; monuments"},
    "20": {"title": "Furniture and Articles Not Otherwise Classified", "type": "goods", "description": "Furniture, mirrors, picture frames; containers (not of metal) for storage or transport; bone, horn, shell articles"},
    "21": {"title": "Housewares and Glass", "type": "goods", "description": "Household or kitchen utensils and containers; cookware and tableware; combs and sponges; brushes; glassware, porcelain and earthenware"},
    "22": {"title": "Cordage and Fibers", "type": "goods", "description": "Ropes and string; nets; tents and tarpaulins; awnings; sails; sacks; padding and stuffing materials; raw fibrous textile materials"},
    "23": {"title": "Yarns and Threads", "type": "goods", "description": "Yarns and threads for textile use"},
    "24": {"title": "Fabrics", "type": "goods", "description": "Textiles and substitutes for textiles; household linen; curtains of textile or plastic"},
    "25": {"title": "Clothing", "type": "goods", "description": "Clothing, footwear, headwear"},
    "26": {"title": "Fancy Goods", "type": "goods", "description": "Lace, braid and embroidery; buttons, hooks and eyes, pins and needles; artificial flowers; hair decorations; false hair"},
    "27": {"title": "Floor Coverings", "type": "goods", "description": "Carpets, rugs, mats and matting; linoleum and other materials for covering floors; wall hangings (non-textile)"},
    "28": {"title": "Toys and Sporting Goods", "type": "goods", "description": "Games, toys and playthings; video game apparatus; gymnastic and sporting articles; decorations for Christmas trees"},
    "29": {"title": "Meats and Processed Foods", "type": "goods", "description": "Meat, fish, poultry and game; preserved, frozen, dried and cooked fruits and vegetables; jellies, jams; eggs; milk and milk products; edible oils"},
    "30": {"title": "Staple Foods", "type": "goods", "description": "Coffee, tea, cocoa; rice, pasta and noodles; flour and preparations made from cereals; bread, pastries and confectionery; salt; spices"},
    "31": {"title": "Natural Agricultural Products", "type": "goods", "description": "Raw and unprocessed agricultural, aquacultural, horticultural and forestry products; fresh fruits and vegetables; live animals; seeds"},
    "32": {"title": "Light Beverages", "type": "goods", "description": "Beers; non-alcoholic beverages; mineral and aerated waters; fruit beverages and fruit juices; syrups for making beverages"},
    "33": {"title": "Wines and Spirits", "type": "goods", "description": "Alcoholic beverages (except beers); alcoholic preparations for making beverages"},
    "34": {"title": "Smokers' Articles", "type": "goods", "description": "Tobacco and tobacco substitutes; cigarettes and cigars; electronic cigarettes and oral vaporizers; smokers' articles; matches"},
    "35": {"title": "Advertising and Business", "type": "services", "description": "Advertising; business management, organization and administration; office functions; retail and online store services"},
    "36": {"title": "Insurance and Financial", "type": "services", "description": "Financial, monetary and banking services; insurance services; real estate services"},
    "37": {"title": "Building Construction and Repair", "type": "services", "description": "Construction services; installation and repair services; mining extraction, oil and gas drilling"},
    "38": {"title": "Telecommunications", "type": "services", "description": "Telecommunications services; broadcasting; providing internet chatrooms and forums"},
    "39": {"title": "Transportation and Storage", "type": "services", "description": "Transport; packaging and storage of goods; travel arrangement"},
    "40": {"title": "Treatment of Materials", "type": "services", "description": "Treatment of materials; recycling of waste and trash; air purification; custom manufacturing; 3D printing services"},
    "41": {"title": "Education and Entertainment", "type": "services", "description": "Education; providing of training; entertainment; sporting and cultural activities"},
    "42": {"title": "Computer and Scientific", "type": "services", "description": "Scientific and technological services; industrial research; design and development of computer hardware and software; SaaS; IT services"},
    "43": {"title": "Hotels and Restaurants", "type": "services", "description": "Services for providing food and drink; temporary accommodation; restaurant, bar and catering services"},
    "44": {"title": "Medical, Beauty and Agricultural", "type": "services", "description": "Medical services; veterinary services; hygienic and beauty care; agriculture, horticulture and forestry services"},
    "45": {"title": "Personal and Legal", "type": "services", "description": "Legal services; security services; personal and social services rendered by others to meet the needs of individuals"},
}

# USPTO Trademark Status Codes (commonly encountered subset).
# TSDR responses include the status description inline; this reference covers
# the codes most often seen in search results and portfolio reviews.
TM_STATUS_CODES = {
    # New applications / examination
    "630": {"description": "New application - record initialized, not assigned to examiner", "stage": "pre-examination"},
    "638": {"description": "New application - assigned to examiner", "stage": "examination"},
    "640": {"description": "Non-final action - mailed", "stage": "examination"},
    "644": {"description": "Final refusal - mailed", "stage": "examination"},
    "650": {"description": "Suspension letter - mailed", "stage": "suspension"},
    "660": {"description": "Examiner's amendment - mailed", "stage": "examination"},
    "661": {"description": "Response after non-final action - entered", "stage": "examination"},
    "681": {"description": "Publication/issue review complete", "stage": "publication"},

    # Publication / allowance
    "686": {"description": "Published for opposition", "stage": "publication"},
    "688": {"description": "Notice of allowance - issued", "stage": "allowance"},
    "730": {"description": "First extension of time to file statement of use - granted", "stage": "allowance"},

    # Registration
    "700": {"description": "Registered", "stage": "registered"},
    "701": {"description": "Section 8 declaration - accepted", "stage": "registered"},
    "702": {"description": "Section 8 & 15 declarations - accepted and acknowledged", "stage": "registered"},
    "800": {"description": "Registered and renewed", "stage": "registered"},

    # Abandonment
    "602": {"description": "Abandoned - failure to respond or late response", "stage": "abandoned"},
    "604": {"description": "Abandoned - express abandonment", "stage": "abandoned"},
    "606": {"description": "Abandoned - after ex parte appeal", "stage": "abandoned"},
    "608": {"description": "Abandoned - no statement of use filed", "stage": "abandoned"},

    # Cancellation / expiration
    "710": {"description": "Cancelled - Section 8 (failure to file declaration of use)", "stage": "cancelled"},
    "712": {"description": "Cancelled by court order", "stage": "cancelled"},
    "900": {"description": "Expired - registration not renewed", "stage": "expired"},
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
        "portal_url": "https://data.uspto.gov",
        "description": "Patent metadata, file wrapper data, continuity, assignments. API key from data.uspto.gov required.",
        "coverage": {
            "applications": "Patent applications with prosecution history (filed on or after Jan 1, 2001)",
            "assignments": "Recorded patent assignments",
            "transactions": "Prosecution transaction history",
        },
        "rate_limits": "Requires ODP API key (register at data.uspto.gov), standard rate limits apply",
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
        "base_url": "N/A",
        "description": (
            "SHUT DOWN. The PatentsView API (search.patentsview.org) was shut "
            "down on March 20, 2026. Data has been migrated to the USPTO Open "
            "Data Portal as bulk downloadable datasets (Granted Patent "
            "Disambiguated Data, Pre-Grant Publication Disambiguated Data, "
            "Long Text Data, Sorted Patent Data). Use ppubs_search_patents "
            "for patent search, odp_search_datasets to find bulk datasets."
        ),
        "coverage": {
            "patents": "Use ppubs_search_patents or ppubs_get_patent_by_number",
            "inventors": "Bulk data via odp_search_datasets (PatentsView disambiguated data)",
            "assignees": "Bulk data via odp_search_datasets (PatentsView disambiguated data)",
        },
        "rate_limits": "N/A",
        "auth_required": False,
        "best_for": [
            "Patent search (UNAVAILABLE - use ppubs_search_patents)",
            "Inventor disambiguation (UNAVAILABLE - use odp_search_datasets for bulk data)",
            "Assignee disambiguation (UNAVAILABLE - use odp_search_datasets for bulk data)",
            "CPC searches (UNAVAILABLE - use ppubs_search_patents with CPC query)",
            "Patent claims/description (UNAVAILABLE - use ppubs_get_full_document)",
        ],
    },
    "ptab": {
        "name": "USPTO PTAB Trial API",
        "base_url": "https://api.uspto.gov",
        "description": (
            "Live via USPTO ODP v3.0 (api.uspto.gov). Provides access to "
            "Patent Trial and Appeal Board trial proceedings (IPR, PGR, CBM, "
            "derivation), trial documents, trial decisions, and ex parte "
            "appeal decisions. Requires a USPTO API key (register at data.uspto.gov)."
        ),
        "coverage": {
            "proceedings": "IPR, PGR, CBM, and derivation proceedings via ptab_search_proceedings / ptab_get_proceeding / ptab_get_documents",
            "decisions": "Trial decisions via ptab_search_decisions / ptab_get_decision (keyed by trial number)",
            "appeals": "Ex parte appeal decisions via ptab_search_appeals / ptab_get_appeal",
        },
        "rate_limits": "Requires ODP API key (register at data.uspto.gov), standard rate limits apply",
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
        "base_url": "N/A",
        "description": (
            "TEMPORARILY UNAVAILABLE. Legacy endpoints at developer.uspto.gov "
            "were decommissioned in early 2026. Migration to ODP (api.uspto.gov) "
            "is pending. Use odp_get_documents to access office action documents "
            "from the file wrapper as a workaround."
        ),
        "coverage": {
            "applications": "Unavailable pending ODP migration",
            "citations": "Use odp_get_documents or ppubs tools",
            "rejections": "Use odp_get_documents to find office action documents",
        },
        "rate_limits": "N/A",
        "auth_required": True,
        "best_for": [
            "Office action full text (UNAVAILABLE - use odp_get_documents)",
            "Examiner citation analysis (UNAVAILABLE - use odp_get_documents)",
            "Rejection pattern analysis (UNAVAILABLE - use odp_get_documents)",
            "Prosecution strategy research (use odp_get_transactions instead)",
        ],
    },
    "litigation": {
        "name": "USPTO Patent Litigation API",
        "base_url": "N/A",
        "description": (
            "UNAVAILABLE. The Patent Litigation API is not available on the "
            "USPTO Open Data Portal (api.uspto.gov) and is not listed in the "
            "ODP Swagger catalog. The OCE Patent Litigation dataset (74,000+ "
            "district court cases) is distributed as a bulk download at "
            "https://www.uspto.gov/ip-policy/economic-research/research-"
            "datasets/patent-litigation-docket-reports-data."
        ),
        "coverage": {
            "cases": "Unavailable via API - use OCE bulk dataset",
            "date_range": "Unavailable via API - use OCE bulk dataset",
        },
        "rate_limits": "N/A",
        "auth_required": False,
        "best_for": [
            "Patent litigation history (UNAVAILABLE - use OCE bulk dataset)",
            "Company litigation profiles (UNAVAILABLE - use OCE bulk dataset)",
            "Patent enforcement patterns (UNAVAILABLE - use OCE bulk dataset)",
        ],
    },
    "tsdr": {
        "name": "USPTO Trademark Status and Document Retrieval (TSDR)",
        "base_url": "https://tsdrapi.uspto.gov/ts/cd",
        "description": (
            "Official API for live trademark case status, prosecution "
            "documents, and mark images, keyed by serial or registration "
            "number. Requires a TSDR-specific API key sent as the "
            "USPTO-API-KEY header (TSDR_API_KEY env var). The ODP key does "
            "NOT work — request a TSDR key at "
            "account.uspto.gov/profile/api-manager ('TSDR API' product)."
        ),
        "coverage": {
            "status": "Live status for all US trademark applications and registrations",
            "documents": "Prosecution document metadata and PDF bundles",
            "images": "Mark drawings/images",
        },
        "rate_limits": "Peak (5am-10pm ET): 60 requests/min general, 4 requests/min PDF/ZIP; off-peak: 120/12 (per API key)",
        "auth_required": True,
        "best_for": [
            "Authoritative live status of a specific trademark",
            "Office actions, specimens, and other file-wrapper documents",
            "Mark images for design marks",
            "Renewal deadline data (Section 8/9 dates)",
        ],
    },
    "tmsearch": {
        "name": "USPTO Trademark Search (tmsearch.uspto.gov)",
        "base_url": "https://tmsearch.uspto.gov",
        "description": (
            "Full-text trademark search via the undocumented internal API "
            "behind the USPTO trademark search web app (the TESS "
            "replacement). Same risk profile as PPUBS: not an official "
            "public API and may change without notice (contract verified "
            "live 2026-06-10). Sits behind AWS WAF — if requests start "
            "failing with 403/202, set TMSEARCH_WAF_TOKEN from a browser "
            "session cookie. USPTO offers no official REST API for "
            "full-text trademark search."
        ),
        "coverage": {
            "trademarks": "US federal trademark applications and registrations, searchable by mark text, owner, goods/services, and class",
        },
        "rate_limits": "Undocumented, but throttled for heavy usage",
        "auth_required": False,
        "best_for": [
            "Clearance/knockout searches for a proposed mark",
            "Finding marks by owner name or goods/services wording",
            "Filtering by Nice international class and live/dead status",
        ],
    },
    "tm_assignments": {
        "name": "USPTO Trademark Assignment Search (Assignment Center)",
        "base_url": "https://assignmentcenter.uspto.gov",
        "description": (
            "Recorded trademark assignment (ownership transfer) records, "
            "1955-present, via the USPTO Assignment Center public API "
            "(verified live 2026-06-10; no API key required). Replaced the "
            "legacy assignment-api.uspto.gov XML API, decommissioned with "
            "the Developer Hub on June 5, 2026."
        ),
        "coverage": {
            "assignments": "Recorded trademark assignments from 1955 to present",
        },
        "rate_limits": "Not published",
        "auth_required": False,
        "best_for": [
            "Tracing trademark ownership history",
            "Finding marks assigned to or from a company",
            "Due diligence on trademark transfers",
            "Looking up a recordation by reel/frame",
        ],
    },
    "ttab": {
        "name": "Trademark Trial and Appeal Board (TTAB)",
        "base_url": "N/A",
        "description": (
            "NOT AVAILABLE AS API. TTAB proceedings (oppositions, "
            "cancellations, ex parte appeals) have no public REST API. Case "
            "status and documents are available via the TTABVUE web "
            "interface, and daily TTAB XML data is published as bulk "
            "datasets on the Open Data Portal (find products via "
            "odp_search_datasets, e.g. the Trademark Daily XML File TTAB "
            "product)."
        ),
        "coverage": {
            "proceedings": "Bulk XML only - use odp_search_datasets",
        },
        "rate_limits": "N/A",
        "auth_required": False,
        "best_for": [
            "Opposition/cancellation research (bulk XML via odp_search_datasets)",
            "TTAB decisions (bulk XML via odp_search_datasets)",
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

NOTE: The PatentsView API was shut down March 20, 2026. This syntax is
retained for reference only; use PPUBS or ODP search instead.

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

## Trademark Search (tm_search_trademarks)

Search US federal trademarks by one or more filters:

- `mark_text` - Word mark text (e.g., "ACME")
- `owner_name` - Owner/applicant name (e.g., "Acme Corporation")
- `international_class` - Nice class number 1-45 (e.g., "9" for software, "25" for clothing)
- `status_filter` - "live" (active marks only), "dead" (abandoned/cancelled/expired), or omit for both
- `query` - Raw query string for advanced searches

### Clearance search tips:
1. Start broad: search the exact proposed mark with status_filter="live"
2. Search phonetic and spelling variants separately (e.g., "KWIK" for "QUICK")
3. Narrow by international_class once you know the relevant classes (use get_trademark_class_info)
4. Check authoritative status of any close hits with tsdr_get_trademark_status
5. Federal search only - common-law and state marks are not covered

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


def get_trademark_class_info(class_number: str) -> dict:
    """Get information about a Nice/international trademark class."""
    cleaned = str(class_number).strip().lstrip("0") or "0"
    if cleaned in NICE_CLASSES:
        info = NICE_CLASSES[cleaned].copy()
        info["class"] = cleaned
        return info
    return {"error": f"Unknown trademark class: {class_number}. Valid classes are 1-45 (goods 1-34, services 35-45)."}


def get_all_trademark_classes() -> dict:
    """Get all Nice/international trademark classes."""
    return NICE_CLASSES


def get_trademark_status_code_info(code: str) -> dict:
    """Get information about a USPTO trademark status code."""
    code = str(code).strip()
    if code in TM_STATUS_CODES:
        info = TM_STATUS_CODES[code].copy()
        info["code"] = code
        return info
    return {
        "error": f"Unknown trademark status code: {code}. This reference covers "
                 "commonly encountered codes only; TSDR status responses include "
                 "the full status description inline (tsdr_get_trademark_status)."
    }


def get_all_trademark_status_codes() -> dict:
    """Get all known USPTO trademark status codes."""
    return TM_STATUS_CODES


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
