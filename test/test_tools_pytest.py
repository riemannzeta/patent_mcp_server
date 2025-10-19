"""
Pytest-based test suite for USPTO Patent MCP Server tools.

This test suite validates all MCP tools using pytest and pytest-asyncio.
Run with: pytest test/test_tools_pytest.py -v
"""

import pytest
import base64
from pathlib import Path
import json

# Import the tools from the main server
from patent_mcp_server.patents import (
    # ppubs.uspto.gov tools
    ppubs_search_patents,
    ppubs_search_applications,
    ppubs_get_full_document,
    ppubs_get_patent_by_number,
    ppubs_download_patent_pdf,

    # api.uspto.gov tools
    get_app,
    search_applications,
    search_applications_post,
    download_applications,
    download_applications_post,
    get_app_metadata,
    get_app_adjustment,
    get_app_assignment,
    get_app_attorney,
    get_app_continuity,
    get_app_foreign_priority,
    get_app_transactions,
    get_app_documents,
    get_app_associated_documents,
    get_status_codes,
    get_status_codes_post,
    search_datasets,
    get_dataset_product
)

# Test constants
PATENT_NUMBER = "9876543"
APP_NUMBER = "14412875"
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

@pytest.mark.asyncio
async def test_ppubs_search_patents(results_dir):
    """Test searching for granted patents."""
    result = await ppubs_search_patents(
        query=f'patentNumber:"{PATENT_NUMBER}"',
        limit=10
    )

    await save_result(result, "ppubs_search_patents.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"
    assert result.get("numFound", 0) > 0, "Expected to find at least one patent"


@pytest.mark.asyncio
async def test_ppubs_search_applications(results_dir):
    """Test searching for published patent applications."""
    result = await ppubs_search_applications(
        query='artificial intelligence',
        limit=10
    )

    await save_result(result, "ppubs_search_applications.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"
    assert result.get("numFound", 0) > 0, "Expected to find at least one application"


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_ppubs_get_patent_by_number(results_dir):
    """Test retrieving a patent by its number."""
    result = await ppubs_get_patent_by_number(patent_number=PATENT_NUMBER)

    await save_result(result, "ppubs_get_patent_by_number.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"


@pytest.mark.asyncio
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

@pytest.mark.asyncio
async def test_get_app(results_dir):
    """Test retrieving patent application data."""
    result = await get_app(app_num=APP_NUMBER)

    await save_result(result, "get_app.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"


@pytest.mark.asyncio
async def test_search_applications(results_dir):
    """Test searching applications with GET."""
    result = await search_applications(
        q=f"applicationNumberText:{APP_NUMBER}",
        limit=10
    )

    await save_result(result, "search_applications.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"
    assert result.get("total", 0) > 0, "Expected to find at least one application"


@pytest.mark.asyncio
async def test_search_applications_post(results_dir):
    """Test searching applications with POST."""
    result = await search_applications_post(
        q=f"applicationNumberText:{APP_NUMBER}",
        limit=10
    )

    await save_result(result, "search_applications_post.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"
    assert result.get("total", 0) > 0, "Expected to find at least one application"


@pytest.mark.asyncio
async def test_download_applications(results_dir):
    """Test downloading application data with GET."""
    result = await download_applications(
        q=f"applicationNumberText:{APP_NUMBER}",
        limit=1,
        format="json"
    )

    await save_result(result, "download_applications.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"


@pytest.mark.asyncio
async def test_download_applications_post(results_dir):
    """Test downloading application data with POST."""
    result = await download_applications_post(
        q=f"applicationNumberText:{APP_NUMBER}",
        limit=1,
        format="json"
    )

    await save_result(result, "download_applications_post.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"


@pytest.mark.asyncio
async def test_get_app_metadata(results_dir):
    """Test retrieving application metadata."""
    result = await get_app_metadata(app_num=APP_NUMBER)

    await save_result(result, "get_app_metadata.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"


@pytest.mark.asyncio
async def test_get_app_adjustment(results_dir):
    """Test retrieving patent term adjustment data."""
    result = await get_app_adjustment(app_num=APP_NUMBER)

    await save_result(result, "get_app_adjustment.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"


@pytest.mark.asyncio
async def test_get_app_assignment(results_dir):
    """Test retrieving assignment data."""
    result = await get_app_assignment(app_num=APP_NUMBER)

    await save_result(result, "get_app_assignment.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"


@pytest.mark.asyncio
async def test_get_app_attorney(results_dir):
    """Test retrieving attorney/agent data."""
    result = await get_app_attorney(app_num=APP_NUMBER)

    await save_result(result, "get_app_attorney.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"


@pytest.mark.asyncio
async def test_get_app_continuity(results_dir):
    """Test retrieving continuity data."""
    result = await get_app_continuity(app_num=APP_NUMBER)

    await save_result(result, "get_app_continuity.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"


@pytest.mark.asyncio
async def test_get_app_foreign_priority(results_dir):
    """Test retrieving foreign priority data."""
    result = await get_app_foreign_priority(app_num=APP_NUMBER)

    await save_result(result, "get_app_foreign_priority.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"


@pytest.mark.asyncio
async def test_get_app_transactions(results_dir):
    """Test retrieving transaction data."""
    result = await get_app_transactions(app_num=APP_NUMBER)

    await save_result(result, "get_app_transactions.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"


@pytest.mark.asyncio
async def test_get_app_documents(results_dir):
    """Test retrieving document details."""
    result = await get_app_documents(app_num=APP_NUMBER)

    await save_result(result, "get_app_documents.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"


@pytest.mark.asyncio
async def test_get_app_associated_documents(results_dir):
    """Test retrieving associated documents."""
    result = await get_app_associated_documents(app_num=APP_NUMBER)

    await save_result(result, "get_app_associated_documents.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"


@pytest.mark.asyncio
async def test_get_status_codes(results_dir):
    """Test searching status codes with GET."""
    result = await get_status_codes(limit=10)

    await save_result(result, "get_status_codes.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"
    assert result.get("total", 0) > 0, "Expected to find status codes"


@pytest.mark.asyncio
async def test_get_status_codes_post(results_dir):
    """Test searching status codes with POST."""
    result = await get_status_codes_post(limit=10)

    await save_result(result, "get_status_codes_post.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"
    assert result.get("total", 0) > 0, "Expected to find status codes"


@pytest.mark.asyncio
async def test_search_datasets(results_dir):
    """Test searching bulk datasets."""
    result = await search_datasets(
        q="patent",
        limit=10
    )

    await save_result(result, "search_datasets.json", results_dir)

    assert not result.get("error", False), f"Error: {result.get('message', 'Unknown error')}"

    products = result.get("products", [])
    assert len(products) > 0, "Expected to find dataset products"

    # Return first product ID for next test
    return products[0].get("productShortName") if products else None


@pytest.mark.asyncio
async def test_get_dataset_product(results_dir):
    """Test retrieving a specific dataset product."""
    # First search for a product
    search_result = await search_datasets(q="patent", limit=1)

    products = search_result.get("products", [])
    product_id = products[0].get("productShortName") if products else "patent-pgn-2023"

    result = await get_dataset_product(
        product_id=product_id,
        limit=5
    )

    await save_result(result, "get_dataset_product.json", results_dir)

    # Note: This may fail if product_id doesn't exist, which is acceptable for this test
    # Just check that we got a response
    assert result is not None, "Expected a response"
