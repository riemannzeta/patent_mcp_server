"""
Integration tests for the patent tools (PPUBS and ODP).

These make real calls to ppubs.uspto.gov and api.uspto.gov, so they are
deselected by default (pytest.ini) and need USPTO_API_KEY for the ODP
half. Every test asserts on the result; a failure here means the live
API contract moved. Outputs are saved under test/test_results/ for
inspection.

Run with: uv run pytest -m integration
Everything, unit and live: uv run pytest -m ""
"""

import pytest
import base64
from pathlib import Path
import json


# Mark all tests in this module as integration tests
pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

# Import the tools from the main server
from patent_mcp_server.patents import (
    # ppubs.uspto.gov tools
    ppubs_search_patents,
    ppubs_search_applications,
    ppubs_get_full_document,
    ppubs_get_patent_by_number,
    ppubs_download_patent_pdf,

    # api.uspto.gov Open Data Portal tools
    odp_get_application,
    odp_search_applications,
    odp_get_application_metadata,
    odp_get_adjustment,
    odp_get_assignment,
    odp_get_attorney,
    odp_get_continuity,
    odp_get_foreign_priority,
    odp_get_transactions,
    odp_get_documents,
    get_status_code,
    odp_search_datasets,
    odp_get_dataset,
    odp_download_document,
    ppubs_get_citing_patents,
)

# Test constants
PATENT_NUMBER = "6000000"
APP_NUMBER = "16123456"
RESULTS_DIR = Path("test/test_results")

# Ensure results directory exists
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


# Fixtures

@pytest.fixture
def results_dir():
    """Provide the results directory path."""
    return RESULTS_DIR


async def save_result(result: dict, filename: str, results_dir: Path):
    """Helper to save test results to JSON."""
    filepath = results_dir / filename
    with open(filepath, 'w') as f:
        json.dump(result, f, indent=2, default=str)


async def save_pdf(result: dict, filename: str, results_dir: Path) -> bool:
    """Helper to save PDF results."""
    if result.get("success") and result.get("content"):
        filepath = results_dir / filename
        pdf_content = base64.b64decode(result["content"])
        with open(filepath, 'wb') as f:
            f.write(pdf_content)
        return True
    return False


# ===================================================================
# Tests for ppubs.uspto.gov (Public Patent Search)
# ===================================================================


async def test_ppubs_search_patents(results_dir):
    """Test searching for granted patents."""
    result = await ppubs_search_patents(
        query=f"{PATENT_NUMBER}.pn.",
        limit=10
    )

    await save_result(result, "ppubs_search_patents.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"
    assert result.get("total", 0) > 0, "Expected to find at least one patent"
    hit = result["results"][0]
    assert hit["guid"] == f"US-{PATENT_NUMBER}-A"
    # Hits are slimmed: no references-cited lists, no empty fields
    assert "urpn" not in hit and "urpnCode" not in hit
    assert all(v not in (None, "", [], {}) for v in hit.values())



async def test_ppubs_search_applications(results_dir):
    """Test searching for published patent applications."""
    result = await ppubs_search_applications(
        query='artificial intelligence',
        limit=10
    )

    await save_result(result, "ppubs_search_applications.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"
    assert result.get("total", 0) > 0, "Expected to find at least one application"



async def test_ppubs_get_full_document(results_dir):
    """Test retrieving a full patent document by GUID."""
    # First search for a patent
    search_result = await ppubs_search_patents(
        query=f"{PATENT_NUMBER}.pn.",
        limit=1
    )

    assert not search_result.get("error", False), "Search failed"

    patents = search_result.get("results", [])
    assert len(patents) > 0, "No patents found"

    patent = patents[0]
    guid = patent.get("guid")
    source_type = patent.get("type")

    # Get full document, claims only
    result = await ppubs_get_full_document(
        guid=guid, source_type=source_type, sections=["claims"]
    )

    await save_result(result, "ppubs_get_full_document.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"
    assert result["guid"] == guid
    assert result["claimsHtml"]
    assert "descriptionHtml" not in result
    assert result["_sections"] == ["claims"]



async def test_ppubs_get_patent_by_number(results_dir):
    """Test retrieving a patent by its number."""
    result = await ppubs_get_patent_by_number(patent_number=PATENT_NUMBER)

    await save_result(result, "ppubs_get_patent_by_number.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"
    assert result["guid"] == f"US-{PATENT_NUMBER}-A"
    for section in ("abstractHtml", "claimsHtml", "descriptionHtml"):
        assert result.get(section), f"{section} missing from the full document"
    # Slimmed: no empty fields, no search-highlight fields
    assert all(v not in (None, "", [], {}) for v in result.values())
    assert not [k for k in result if "KwicHits" in k or "Highlights" in k]


async def test_ppubs_get_patent_by_number_sections(results_dir):
    """`sections` returns the front page and claims without the description."""
    result = await ppubs_get_patent_by_number(
        patent_number=PATENT_NUMBER, sections=["biblio", "claims"]
    )

    await save_result(result, "ppubs_get_patent_by_number_sections.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"
    assert result["claimsHtml"]
    assert result["usRefGroup"], "front page should list the references cited"
    assert "descriptionHtml" not in result and "abstractHtml" not in result
    assert result["_sections"] == ["biblio", "claims"]


@pytest.mark.parametrize("raw,guid", [
    ("US 6,000,000 A", "US-6000000-A"),
    ("D845123", "US-D845123-S"),
    ("RE49123", "US-RE49123-E"),
])
async def test_ppubs_get_patent_by_number_accepts_prefixes_and_kind_codes(raw, guid):
    """Formatted, design and reissue numbers resolve to the right document."""
    result = await ppubs_get_patent_by_number(patent_number=raw, sections=["biblio"])

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"
    assert result["guid"] == guid


async def test_ppubs_get_citing_patents(results_dir):
    """Forward citations come back as slimmed search hits."""
    result = await ppubs_get_citing_patents(patent_number=PATENT_NUMBER, limit=5)

    await save_result(result, "ppubs_get_citing_patents.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"
    assert result["total"] > 0, "US 6,000,000 has forward citations"
    assert result["metadata"]["query"] == f"{PATENT_NUMBER}.urpn."
    assert result["metadata"]["cited_patent"] == PATENT_NUMBER
    for hit in result["results"]:
        assert hit["guid"] != f"US-{PATENT_NUMBER}-A"
        assert "urpn" not in hit



@pytest.mark.slow
async def test_ppubs_download_patent_pdf(results_dir):
    """Test downloading a patent as PDF."""
    result = await ppubs_download_patent_pdf(patent_number=PATENT_NUMBER)

    # Save PDF if successful
    success = await save_pdf(result, f"US-{PATENT_NUMBER}-B2.pdf", results_dir)
    await save_result(result, "ppubs_download_patent_pdf.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"
    assert success, "Failed to save PDF"


# ===================================================================
# Tests for api.uspto.gov (Open Data Portal API)
# ===================================================================


async def test_odp_get_application(results_dir):
    """Test retrieving patent application data."""
    result = await odp_get_application(app_num=APP_NUMBER)

    await save_result(result, "get_app.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"



async def test_odp_search_applications(results_dir):
    """Test searching applications."""
    result = await odp_search_applications(
        application_number=APP_NUMBER,
        limit=10
    )

    await save_result(result, "search_applications.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"
    assert result.get("total", 0) > 0, "Expected to find at least one application"



async def test_odp_get_application_metadata(results_dir):
    """Test retrieving application metadata."""
    result = await odp_get_application_metadata(app_num=APP_NUMBER)

    await save_result(result, "get_app_metadata.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"



async def test_odp_get_adjustment(results_dir):
    """Test retrieving patent term adjustment data."""
    result = await odp_get_adjustment(app_num=APP_NUMBER)

    await save_result(result, "get_app_adjustment.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"



async def test_odp_get_assignment(results_dir):
    """Test retrieving assignment data."""
    result = await odp_get_assignment(app_num=APP_NUMBER)

    await save_result(result, "get_app_assignment.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"



async def test_odp_get_attorney(results_dir):
    """Test retrieving attorney/agent data."""
    result = await odp_get_attorney(app_num=APP_NUMBER)

    await save_result(result, "get_app_attorney.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"



async def test_odp_get_continuity(results_dir):
    """Test retrieving continuity data."""
    result = await odp_get_continuity(app_num=APP_NUMBER)

    await save_result(result, "get_app_continuity.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"



async def test_odp_get_foreign_priority(results_dir):
    """Test retrieving foreign priority data."""
    result = await odp_get_foreign_priority(app_num=APP_NUMBER)

    await save_result(result, "get_app_foreign_priority.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"



async def test_odp_get_transactions(results_dir):
    """Test retrieving transaction data."""
    result = await odp_get_transactions(app_num=APP_NUMBER)

    await save_result(result, "get_app_transactions.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"



async def test_odp_get_documents(results_dir):
    """The file wrapper lists newest first, with codes counted in metadata."""
    result = await odp_get_documents(app_num=APP_NUMBER)

    await save_result(result, "get_app_documents.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"
    assert result["total"] > 0 and result["count"] > 0
    assert result["metadata"]["documents_in_wrapper"] == result["total"]
    assert sum(result["metadata"]["code_counts"].values()) == result["total"]
    doc = result["results"][0]
    for key in ("documentIdentifier", "documentCode", "officialDate", "directionCategory", "formats"):
        assert key in doc, f"{key} missing from document summary"
    assert "downloadOptionBag" not in doc


async def test_odp_get_documents_filtered_by_code(results_dir):
    """document_code narrows the listing to the office actions."""
    result = await odp_get_documents(app_num=APP_NUMBER, document_code="ctnf,ctfr,noa")

    await save_result(result, "get_app_documents_filtered.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"
    assert result["total"] > 0, "expected at least one office action or allowance"
    assert {d["documentCode"] for d in result["results"]} <= {"CTNF", "CTFR", "NOA"}
    assert result["total"] < result["metadata"]["documents_in_wrapper"]


@pytest.mark.slow
async def test_odp_download_document(results_dir):
    """A listed office action downloads as a real PDF."""
    listing = await odp_get_documents(app_num=APP_NUMBER, document_code="CTNF", limit=1)
    assert not listing.get("error", False), f"Error: {listing.get('message', 'Unknown error')}"
    assert listing["results"], "no non-final rejection in the wrapper"
    document_id = listing["results"][0]["documentIdentifier"]

    result = await odp_download_document(app_num=APP_NUMBER, document_id=document_id)

    saved = await save_pdf(result, f"{APP_NUMBER}-{document_id}.pdf", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"
    assert saved, "Failed to save PDF"
    pdf = base64.b64decode(result["content"])
    assert pdf[:5] == b"%PDF-", "download is not a PDF"
    assert result["size_bytes"] == len(pdf) > 10_000
    assert result["filename"] == f"{APP_NUMBER}-{document_id}.pdf"



async def test_get_status_code(results_dir):
    """Test retrieving status code info."""
    # Use a valid status code "30" = "Docketed New Case - Ready for Examination"
    result = await get_status_code(code="30")

    await save_result(result, "get_status_codes.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('error', 'Unknown error')}"
    assert result.get("code") == "30"
    assert "description" in result



async def test_odp_search_datasets(results_dir):
    """Test searching bulk datasets."""
    result = await odp_search_datasets(
        query="patent",
        limit=10
    )

    await save_result(result, "search_datasets.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"

    # Live shape (2026-09-26): {"count": N, "bulkDataProductBag": [...]}
    products = result.get("bulkDataProductBag", [])
    assert len(products) > 0, "Expected to find dataset products"
    assert result["count"] >= len(products)
    assert products[0]["productIdentifier"]
    assert products[0]["productTitleText"]



async def test_odp_get_dataset(results_dir):
    """A product found by search can be fetched by its identifier."""
    search_result = await odp_search_datasets(query="patent", limit=1)
    products = search_result.get("bulkDataProductBag", [])
    assert products, "search returned no products to look up"
    product_id = products[0]["productIdentifier"]

    result = await odp_get_dataset(product_id=product_id)

    await save_result(result, "get_dataset_product.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"
    bag = result.get("bulkDataProductBag", [])
    assert len(bag) == 1, "expected exactly the requested product"
    assert bag[0]["productIdentifier"] == product_id
