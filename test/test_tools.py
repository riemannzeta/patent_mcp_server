#!/usr/bin/env python3
"""
Integration tests for USPTO Patent MCP Server tools.

These are INTEGRATION tests that make real API calls to USPTO servers.
Run directly with: python test/test_tools.py
Or with pytest: pytest test/test_tools.py -v -m integration
Skip with: pytest -m "not integration"
"""
import asyncio
import json
import logging
import sys
import os
import base64
from pathlib import Path
from datetime import datetime

import pytest

# Mark all tests in this module as integration tests (when run via pytest)
pytestmark = [pytest.mark.integration]

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Create logger
logger = logging.getLogger('test_tools')

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
    odp_get_dataset
)

# Define test parameters
PATENT_NUMBER = "9876543"
APP_NUMBER = "14412875"
RESULTS_DIR = Path("test/test_results")

# Create results directory if it doesn't exist
os.makedirs(RESULTS_DIR, exist_ok=True)

async def save_result(result, filename):
    """Save test result to a file."""
    filepath = RESULTS_DIR / filename
    with open(filepath, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    logger.info(f"Result saved to {filepath}")

async def save_pdf(result, filename):
    """Save PDF result to a file."""
    if result.get("success") and result.get("content"):
        filepath = RESULTS_DIR / filename
        pdf_content = base64.b64decode(result["content"])
        with open(filepath, 'wb') as f:
            f.write(pdf_content)
        logger.info(f"PDF saved to {filepath}")
        return True
    return False

# Test functions for each tool

async def test_ppubs_search_patents():
    logger.info("Testing ppubs_search_patents...")
    
    # Test with a simple search query
    start_time = datetime.now()
    result = await ppubs_search_patents(
        query=f'patentNumber:"{PATENT_NUMBER}"',
        limit=10
    )
    duration = (datetime.now() - start_time).total_seconds()
    
    logger.info(f"ppubs_search_patents completed in {duration:.2f} seconds")
    
    # Save result
    await save_result(result, "ppubs_search_patents.json")
    
    # Log result summary
    if result.get("error", False):
        logger.error(f"Error: {result.get('message', 'Unknown error')}")
        return False
    
    num_found = result.get("numFound", 0)
    logger.info(f"Found {num_found} patents")
    return num_found > 0

async def test_ppubs_search_applications():
    logger.info("Testing ppubs_search_applications...")
    
    # Test with a simple search query for applications
    start_time = datetime.now()
    result = await ppubs_search_applications(
        query='artificial intelligence',
        limit=10
    )
    duration = (datetime.now() - start_time).total_seconds()
    
    logger.info(f"ppubs_search_applications completed in {duration:.2f} seconds")
    
    # Save result
    await save_result(result, "ppubs_search_applications.json")
    
    # Log result summary
    if result.get("error", False):
        logger.error(f"Error: {result.get('message', 'Unknown error')}")
        return False
    
    num_found = result.get("numFound", 0)
    logger.info(f"Found {num_found} patent applications")
    return num_found > 0

async def test_ppubs_get_full_document():
    logger.info("Testing ppubs_get_full_document...")
    
    # First get a GUID and source_type by searching
    search_result = await ppubs_search_patents(
        query=f'patentNumber:"{PATENT_NUMBER}"',
        limit=1
    )
    
    if search_result.get("error", False):
        logger.error(f"Error during search: {search_result.get('message', 'Unknown error')}")
        return False
    
    # Extract GUID and source_type from search result
    patents = search_result.get("patents", search_result.get("docs", []))
    if not patents:
        logger.error(f"No patents found with number {PATENT_NUMBER}")
        return False
    
    patent = patents[0]
    guid = patent.get("guid")
    source_type = patent.get("type")
    
    logger.info(f"Found patent with GUID: {guid}, type: {source_type}")
    
    # Get full document
    start_time = datetime.now()
    result = await ppubs_get_full_document(guid=guid, source_type=source_type)
    duration = (datetime.now() - start_time).total_seconds()
    
    logger.info(f"ppubs_get_full_document completed in {duration:.2f} seconds")
    
    # Save result
    await save_result(result, "ppubs_get_full_document.json")
    
    # Log result summary
    if result.get("error", False):
        logger.error(f"Error: {result.get('message', 'Unknown error')}")
        return False
    
    logger.info(f"Successfully retrieved full document for {guid}")
    return True

async def test_ppubs_get_patent_by_number():
    logger.info("Testing ppubs_get_patent_by_number...")
    
    # Test with the specific patent number
    start_time = datetime.now()
    result = await ppubs_get_patent_by_number(patent_number=PATENT_NUMBER)
    duration = (datetime.now() - start_time).total_seconds()
    
    logger.info(f"ppubs_get_patent_by_number completed in {duration:.2f} seconds")
    
    # Save result
    await save_result(result, "ppubs_get_patent_by_number.json")
    
    # Log result summary
    if result.get("error", False):
        logger.error(f"Error: {result.get('message', 'Unknown error')}")
        return False
    
    logger.info(f"Successfully retrieved patent {PATENT_NUMBER}")
    return True

async def test_ppubs_download_patent_pdf():
    logger.info("Testing ppubs_download_patent_pdf...")
    
    # Test with the specific patent number
    start_time = datetime.now()
    result = await ppubs_download_patent_pdf(patent_number=PATENT_NUMBER)
    duration = (datetime.now() - start_time).total_seconds()
    
    logger.info(f"ppubs_download_patent_pdf completed in {duration:.2f} seconds")
    
    # Save PDF if successful
    success = await save_pdf(result, f"US-{PATENT_NUMBER}-B2.pdf")
    
    # Also save the JSON response metadata
    await save_result(result, "ppubs_download_patent_pdf.json")
    
    # Log result summary
    if result.get("error", False):
        logger.error(f"Error: {result.get('message', 'Unknown error')}")
        return False
    
    logger.info(f"Successfully downloaded PDF for patent {PATENT_NUMBER}")
    return success

async def test_odp_get_application():
    logger.info("Testing odp_get_application...")

    # Test with the application number
    start_time = datetime.now()
    result = await odp_get_application(app_num=APP_NUMBER)
    duration = (datetime.now() - start_time).total_seconds()

    logger.info(f"odp_get_application completed in {duration:.2f} seconds")

    # Save result
    await save_result(result, "get_app.json")

    # Log result summary
    if result.get("error", False):
        logger.error(f"Error: {result.get('message', 'Unknown error')}")
        return False

    logger.info(f"Successfully retrieved application {APP_NUMBER}")
    return True

async def test_odp_search_applications():
    logger.info("Testing odp_search_applications...")

    # Test with a simple search query
    start_time = datetime.now()
    result = await odp_search_applications(
        application_number=APP_NUMBER,
        limit=10
    )
    duration = (datetime.now() - start_time).total_seconds()

    logger.info(f"odp_search_applications completed in {duration:.2f} seconds")

    # Save result
    await save_result(result, "search_applications.json")

    # Log result summary
    if result.get("error", False):
        logger.error(f"Error: {result.get('message', 'Unknown error')}")
        return False

    results = result.get("results", [])
    total = result.get("total", 0)
    logger.info(f"Found {total} applications")
    return total > 0

async def test_odp_get_application_metadata():
    logger.info("Testing odp_get_application_metadata...")

    # Test with the application number
    start_time = datetime.now()
    result = await odp_get_application_metadata(app_num=APP_NUMBER)
    duration = (datetime.now() - start_time).total_seconds()

    logger.info(f"odp_get_application_metadata completed in {duration:.2f} seconds")

    # Save result
    await save_result(result, "get_app_metadata.json")

    # Log result summary
    if result.get("error", False):
        logger.error(f"Error: {result.get('message', 'Unknown error')}")
        return False

    logger.info(f"Successfully retrieved metadata for application {APP_NUMBER}")
    return True

async def test_odp_get_adjustment():
    logger.info("Testing odp_get_adjustment...")

    # Test with the application number
    start_time = datetime.now()
    result = await odp_get_adjustment(app_num=APP_NUMBER)
    duration = (datetime.now() - start_time).total_seconds()

    logger.info(f"odp_get_adjustment completed in {duration:.2f} seconds")

    # Save result
    await save_result(result, "get_app_adjustment.json")

    # Log result summary
    if result.get("error", False):
        logger.error(f"Error: {result.get('message', 'Unknown error')}")
        return False

    logger.info(f"Successfully retrieved adjustment data for application {APP_NUMBER}")
    return True

async def test_odp_get_assignment():
    logger.info("Testing odp_get_assignment...")

    # Test with the application number
    start_time = datetime.now()
    result = await odp_get_assignment(app_num=APP_NUMBER)
    duration = (datetime.now() - start_time).total_seconds()

    logger.info(f"odp_get_assignment completed in {duration:.2f} seconds")

    # Save result
    await save_result(result, "get_app_assignment.json")

    # Log result summary
    if result.get("error", False):
        logger.error(f"Error: {result.get('message', 'Unknown error')}")
        return False

    logger.info(f"Successfully retrieved assignment data for application {APP_NUMBER}")
    return True

async def test_odp_get_attorney():
    logger.info("Testing odp_get_attorney...")

    # Test with the application number
    start_time = datetime.now()
    result = await odp_get_attorney(app_num=APP_NUMBER)
    duration = (datetime.now() - start_time).total_seconds()

    logger.info(f"odp_get_attorney completed in {duration:.2f} seconds")

    # Save result
    await save_result(result, "get_app_attorney.json")

    # Log result summary
    if result.get("error", False):
        logger.error(f"Error: {result.get('message', 'Unknown error')}")
        return False

    logger.info(f"Successfully retrieved attorney data for application {APP_NUMBER}")
    return True

async def test_odp_get_continuity():
    logger.info("Testing odp_get_continuity...")

    # Test with the application number
    start_time = datetime.now()
    result = await odp_get_continuity(app_num=APP_NUMBER)
    duration = (datetime.now() - start_time).total_seconds()

    logger.info(f"odp_get_continuity completed in {duration:.2f} seconds")

    # Save result
    await save_result(result, "get_app_continuity.json")

    # Log result summary
    if result.get("error", False):
        logger.error(f"Error: {result.get('message', 'Unknown error')}")
        return False

    logger.info(f"Successfully retrieved continuity data for application {APP_NUMBER}")
    return True

async def test_odp_get_foreign_priority():
    logger.info("Testing odp_get_foreign_priority...")

    # Test with the application number
    start_time = datetime.now()
    result = await odp_get_foreign_priority(app_num=APP_NUMBER)
    duration = (datetime.now() - start_time).total_seconds()

    logger.info(f"odp_get_foreign_priority completed in {duration:.2f} seconds")

    # Save result
    await save_result(result, "get_app_foreign_priority.json")

    # Log result summary
    if result.get("error", False):
        logger.error(f"Error: {result.get('message', 'Unknown error')}")
        return False

    logger.info(f"Successfully retrieved foreign priority data for application {APP_NUMBER}")
    return True

async def test_odp_get_transactions():
    logger.info("Testing odp_get_transactions...")

    # Test with the application number
    start_time = datetime.now()
    result = await odp_get_transactions(app_num=APP_NUMBER)
    duration = (datetime.now() - start_time).total_seconds()

    logger.info(f"odp_get_transactions completed in {duration:.2f} seconds")

    # Save result
    await save_result(result, "get_app_transactions.json")

    # Log result summary
    if result.get("error", False):
        logger.error(f"Error: {result.get('message', 'Unknown error')}")
        return False

    logger.info(f"Successfully retrieved transaction data for application {APP_NUMBER}")
    return True

async def test_odp_get_documents():
    logger.info("Testing odp_get_documents...")

    # Test with the application number
    start_time = datetime.now()
    result = await odp_get_documents(app_num=APP_NUMBER)
    duration = (datetime.now() - start_time).total_seconds()

    logger.info(f"odp_get_documents completed in {duration:.2f} seconds")

    # Save result
    await save_result(result, "get_app_documents.json")

    # Log result summary
    if result.get("error", False):
        logger.error(f"Error: {result.get('message', 'Unknown error')}")
        return False

    logger.info(f"Successfully retrieved document data for application {APP_NUMBER}")
    return True

async def test_get_status_code():
    logger.info("Testing get_status_code...")

    # Test with a valid status code "30" = "Docketed New Case - Ready for Examination"
    start_time = datetime.now()
    result = await get_status_code(code="30")
    duration = (datetime.now() - start_time).total_seconds()

    logger.info(f"get_status_code completed in {duration:.2f} seconds")

    # Save result
    await save_result(result, "get_status_codes.json")

    # Log result summary
    if result.get("error", False):
        logger.error(f"Error: {result.get('error', 'Unknown error')}")
        return False

    logger.info(f"Successfully retrieved status code info: {result.get('description')}")
    return True

async def test_odp_search_datasets():
    logger.info("Testing odp_search_datasets...")

    # Test with a simple search for patent datasets
    start_time = datetime.now()
    result = await odp_search_datasets(
        query="patent",
        limit=10
    )
    duration = (datetime.now() - start_time).total_seconds()

    logger.info(f"odp_search_datasets completed in {duration:.2f} seconds")

    # Save result
    await save_result(result, "search_datasets.json")

    # Log result summary
    if result.get("error", False):
        logger.error(f"Error: {result.get('message', 'Unknown error')}")
        return False

    products = result.get("products", [])
    total = len(products)
    logger.info(f"Found {total} dataset products")

    # Save product ID for next test if possible
    if total > 0:
        # Get the first product short name for the next test
        product_id = products[0].get("productShortName", "")
        if product_id:
            logger.info(f"Found product ID for next test: {product_id}")
            return product_id

    return False

async def test_odp_get_dataset(product_id=None):
    logger.info("Testing odp_get_dataset...")

    if not product_id:
        logger.warning("No product ID provided, using a default value that may not exist")
        product_id = "patent-pgn-2023"

    # Test with the product ID
    start_time = datetime.now()
    result = await odp_get_dataset(
        product_id=product_id
    )
    duration = (datetime.now() - start_time).total_seconds()

    logger.info(f"odp_get_dataset completed in {duration:.2f} seconds")

    # Save result
    await save_result(result, "get_dataset_product.json")

    # Log result summary
    if result.get("error", False):
        logger.error(f"Error: {result.get('message', 'Unknown error')}")
        return False

    logger.info(f"Successfully retrieved product data for {product_id}")
    return True

async def run_tests():
    """Run all tool tests."""
    logger.info("=== Starting tool tests ===")

    # Create a test summary to report success/failure for each test
    test_summary = {
        "run_date": datetime.now().isoformat(),
        "tests": {}
    }

    # Test Public Patent Search (ppubs.uspto.gov) tools
    test_summary["tests"]["ppubs_search_patents"] = await test_ppubs_search_patents()
    test_summary["tests"]["ppubs_search_applications"] = await test_ppubs_search_applications()
    test_summary["tests"]["ppubs_get_full_document"] = await test_ppubs_get_full_document()
    test_summary["tests"]["ppubs_get_patent_by_number"] = await test_ppubs_get_patent_by_number()
    test_summary["tests"]["ppubs_download_patent_pdf"] = await test_ppubs_download_patent_pdf()

    # Test Open Data Portal API (api.uspto.gov) tools
    test_summary["tests"]["odp_get_application"] = await test_odp_get_application()
    test_summary["tests"]["odp_search_applications"] = await test_odp_search_applications()
    test_summary["tests"]["odp_get_application_metadata"] = await test_odp_get_application_metadata()
    test_summary["tests"]["odp_get_adjustment"] = await test_odp_get_adjustment()
    test_summary["tests"]["odp_get_assignment"] = await test_odp_get_assignment()
    test_summary["tests"]["odp_get_attorney"] = await test_odp_get_attorney()
    test_summary["tests"]["odp_get_continuity"] = await test_odp_get_continuity()
    test_summary["tests"]["odp_get_foreign_priority"] = await test_odp_get_foreign_priority()
    test_summary["tests"]["odp_get_transactions"] = await test_odp_get_transactions()
    test_summary["tests"]["odp_get_documents"] = await test_odp_get_documents()
    test_summary["tests"]["get_status_code"] = await test_get_status_code()

    # Test datasets tools
    product_id = await test_odp_search_datasets()
    test_summary["tests"]["odp_search_datasets"] = bool(product_id)
    test_summary["tests"]["odp_get_dataset"] = await test_odp_get_dataset(product_id)
    
    # Save test summary
    await save_result(test_summary, "test_summary.json")
    
    # Calculate success rate
    total_tests = len(test_summary["tests"])
    successful_tests = sum(1 for result in test_summary["tests"].values() if result)
    success_rate = successful_tests / total_tests * 100 if total_tests > 0 else 0
    
    logger.info(f"=== Test Summary ===")
    logger.info(f"Total tests: {total_tests}")
    logger.info(f"Successful tests: {successful_tests}")
    logger.info(f"Success rate: {success_rate:.2f}%")
    logger.info("=== Tests completed ===")

if __name__ == "__main__":
    try:
        logger.info("Starting tool tests")
        asyncio.run(run_tests())
        logger.info("Tool tests completed")
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)