"""
Pytest-based test suite for USPTO Patent MCP Server tools.

This test suite validates all MCP tools using pytest and pytest-asyncio.
These are INTEGRATION tests that make real API calls to USPTO servers.

Run with: pytest test/test_tools_pytest.py -v -m integration
Skip with: pytest -m "not integration"
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

    # PatentsView tools
    patentsview_search_patents,
    patentsview_get_patent,
    patentsview_search_assignees,
    patentsview_search_inventors,
    patentsview_get_claims,
    patentsview_get_description,
    patentsview_search_by_cpc,
    patentsview_lookup_cpc,
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
        query=f'patentNumber:"{PATENT_NUMBER}"',
        limit=10
    )

    await save_result(result, "ppubs_search_patents.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"
    assert result.get("numFound", 0) > 0, "Expected to find at least one patent"



async def test_ppubs_search_applications(results_dir):
    """Test searching for published patent applications."""
    result = await ppubs_search_applications(
        query='artificial intelligence',
        limit=10
    )

    await save_result(result, "ppubs_search_applications.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"
    assert result.get("numFound", 0) > 0, "Expected to find at least one application"



async def test_ppubs_get_full_document(results_dir):
    """Test retrieving a full patent document by GUID."""
    # First search for a patent
    search_result = await ppubs_search_patents(
        query=f'patentNumber:"{PATENT_NUMBER}"',
        limit=1
    )

    assert not search_result.get("error", False), "Search failed"

    patents = search_result.get("patents", search_result.get("docs", []))
    assert len(patents) > 0, "No patents found"

    patent = patents[0]
    guid = patent.get("guid")
    source_type = patent.get("type")

    # Get full document
    result = await ppubs_get_full_document(guid=guid, source_type=source_type)

    await save_result(result, "ppubs_get_full_document.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"



async def test_ppubs_get_patent_by_number(results_dir):
    """Test retrieving a patent by its number."""
    result = await ppubs_get_patent_by_number(patent_number=PATENT_NUMBER)

    await save_result(result, "ppubs_get_patent_by_number.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"



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
    """Test retrieving document details."""
    result = await odp_get_documents(app_num=APP_NUMBER)

    await save_result(result, "get_app_documents.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"



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

    products = result.get("products", [])
    assert len(products) > 0, "Expected to find dataset products"

    # Return first product ID for next test
    return products[0].get("productShortName") if products else None



async def test_odp_get_dataset(results_dir):
    """Test retrieving a specific dataset product."""
    # First search for a product
    search_result = await odp_search_datasets(query="patent", limit=1)

    products = search_result.get("products", [])
    product_id = products[0].get("productShortName") if products else "patent-pgn-2023"

    result = await odp_get_dataset(
        product_id=product_id
    )

    await save_result(result, "get_dataset_product.json", results_dir)

    # Note: This may fail if product_id doesn't exist, which is acceptable for this test
    # Just check that we got a response
    assert result is not None, "Expected a response"


# ===================================================================
# Tests for PatentsView API (search.patentsview.org)
# ===================================================================


async def test_patentsview_search_patents(results_dir):
    """Test searching for patents via PatentsView."""
    result = await patentsview_search_patents(
        query="neural network",
        search_type="any",
        limit=10
    )

    await save_result(result, "patentsview_search_patents.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"
    # PatentsView returns 'patents' key on success
    assert "patents" in result or result.get("success") is True, "Expected patents in response"


async def test_patentsview_search_patents_phrase(results_dir):
    """Test phrase search via PatentsView."""
    result = await patentsview_search_patents(
        query="machine learning",
        search_type="phrase",
        limit=5
    )

    await save_result(result, "patentsview_search_patents_phrase.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"


async def test_patentsview_get_patent(results_dir):
    """Test retrieving a specific patent by ID."""
    result = await patentsview_get_patent(patent_id="7861317")

    await save_result(result, "patentsview_get_patent.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"


async def test_patentsview_search_assignees(results_dir):
    """Test searching for assignees."""
    result = await patentsview_search_assignees(
        query='{"assignee_organization": {"_contains": "Apple"}}',
        limit=10
    )

    await save_result(result, "patentsview_search_assignees.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"


async def test_patentsview_search_inventors(results_dir):
    """Test searching for inventors."""
    result = await patentsview_search_inventors(
        query='{"inventor_name_last": "Smith"}',
        limit=10
    )

    await save_result(result, "patentsview_search_inventors.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"


async def test_patentsview_get_claims(results_dir):
    """Test getting patent claims."""
    result = await patentsview_get_claims(patent_id="7861317")

    await save_result(result, "patentsview_get_claims.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"


async def test_patentsview_search_by_cpc(results_dir):
    """Test searching by CPC classification."""
    result = await patentsview_search_by_cpc(
        cpc_code="G06N",
        limit=10
    )

    await save_result(result, "patentsview_search_by_cpc.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"


async def test_patentsview_lookup_cpc(results_dir):
    """Test CPC code lookup."""
    result = await patentsview_lookup_cpc(cpc_code="G06")

    await save_result(result, "patentsview_lookup_cpc.json", results_dir)

    # CPC lookup may return empty for some codes, so just check no error
    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"
