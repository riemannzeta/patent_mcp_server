#!/usr/bin/env python3
import asyncio
import json
import logging
import sys
import os
import base64
from pathlib import Path
from datetime import datetime

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

async def test_get_app():
    logger.info("Testing get_app...")
    
    # Test with the application number
    start_time = datetime.now()
    result = await get_app(app_num=APP_NUMBER)
    duration = (datetime.now() - start_time).total_seconds()
    
    logger.info(f"get_app completed in {duration:.2f} seconds")
    
    # Save result
    await save_result(result, "get_app.json")
    
    # Log result summary
    if result.get("error", False):
        logger.error(f"Error: {result.get('message', 'Unknown error')}")
        return False
    
    logger.info(f"Successfully retrieved application {APP_NUMBER}")
    return True

async def test_search_applications():
    logger.info("Testing search_applications...")
    
    # Test with a simple search query
    start_time = datetime.now()
    result = await search_applications(
        q=f"applicationNumberText:{APP_NUMBER}",
        limit=10
    )
    duration = (datetime.now() - start_time).total_seconds()
    
    logger.info(f"search_applications completed in {duration:.2f} seconds")
    
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

async def test_search_applications_post():
    logger.info("Testing search_applications_post...")
    
    # Test with a simple search query
    start_time = datetime.now()
    result = await search_applications_post(
        q=f"applicationNumberText:{APP_NUMBER}",
        limit=10
    )
    duration = (datetime.now() - start_time).total_seconds()
    
    logger.info(f"search_applications_post completed in {duration:.2f} seconds")
    
    # Save result
    await save_result(result, "search_applications_post.json")
    
    # Log result summary
    if result.get("error", False):
        logger.error(f"Error: {result.get('message', 'Unknown error')}")
        return False
    
    results = result.get("results", [])
    total = result.get("total", 0)
    logger.info(f"Found {total} applications")
    return total > 0

async def test_download_applications():
    logger.info("Testing download_applications...")
    
    # Test with a simple search query
    start_time = datetime.now()
    result = await download_applications(
        q=f"applicationNumberText:{APP_NUMBER}",
        limit=1,
        format="json"
    )
    duration = (datetime.now() - start_time).total_seconds()
    
    logger.info(f"download_applications completed in {duration:.2f} seconds")
    
    # Save result
    await save_result(result, "download_applications.json")
    
    # Log result summary
    if result.get("error", False):
        logger.error(f"Error: {result.get('message', 'Unknown error')}")
        return False
    
    logger.info(f"Successfully downloaded application data")
    return True

async def test_download_applications_post():
    logger.info("Testing download_applications_post...")
    
    # Test with a simple search query
    start_time = datetime.now()
    result = await download_applications_post(
        q=f"applicationNumberText:{APP_NUMBER}",
        limit=1,
        format="json"
    )
    duration = (datetime.now() - start_time).total_seconds()
    
    logger.info(f"download_applications_post completed in {duration:.2f} seconds")
    
    # Save result
    await save_result(result, "download_applications_post.json")
    
    # Log result summary
    if result.get("error", False):
        logger.error(f"Error: {result.get('message', 'Unknown error')}")
        return False
    
    logger.info(f"Successfully downloaded application data via POST")
    return True

async def test_get_app_metadata():
    logger.info("Testing get_app_metadata...")
    
    # Test with the application number
    start_time = datetime.now()
    result = await get_app_metadata(app_num=APP_NUMBER)
    duration = (datetime.now() - start_time).total_seconds()
    
    logger.info(f"get_app_metadata completed in {duration:.2f} seconds")
    
    # Save result
    await save_result(result, "get_app_metadata.json")
    
    # Log result summary
    if result.get("error", False):
        logger.error(f"Error: {result.get('message', 'Unknown error')}")
        return False
    
    logger.info(f"Successfully retrieved metadata for application {APP_NUMBER}")
    return True

async def test_get_app_adjustment():
    logger.info("Testing get_app_adjustment...")
    
    # Test with the application number
    start_time = datetime.now()
    result = await get_app_adjustment(app_num=APP_NUMBER)
    duration = (datetime.now() - start_time).total_seconds()
    
    logger.info(f"get_app_adjustment completed in {duration:.2f} seconds")
    
    # Save result
    await save_result(result, "get_app_adjustment.json")
    
    # Log result summary
    if result.get("error", False):
        logger.error(f"Error: {result.get('message', 'Unknown error')}")
        return False
    
    logger.info(f"Successfully retrieved adjustment data for application {APP_NUMBER}")
    return True

async def test_get_app_assignment():
    logger.info("Testing get_app_assignment...")
    
    # Test with the application number
    start_time = datetime.now()
    result = await get_app_assignment(app_num=APP_NUMBER)
    duration = (datetime.now() - start_time).total_seconds()
    
    logger.info(f"get_app_assignment completed in {duration:.2f} seconds")
    
    # Save result
    await save_result(result, "get_app_assignment.json")
    
    # Log result summary
    if result.get("error", False):
        logger.error(f"Error: {result.get('message', 'Unknown error')}")
        return False
    
    logger.info(f"Successfully retrieved assignment data for application {APP_NUMBER}")
    return True

async def test_get_app_attorney():
    logger.info("Testing get_app_attorney...")
    
    # Test with the application number
    start_time = datetime.now()
    result = await get_app_attorney(app_num=APP_NUMBER)
    duration = (datetime.now() - start_time).total_seconds()
    
    logger.info(f"get_app_attorney completed in {duration:.2f} seconds")
    
    # Save result
    await save_result(result, "get_app_attorney.json")
    
    # Log result summary
    if result.get("error", False):
        logger.error(f"Error: {result.get('message', 'Unknown error')}")
        return False
    
    logger.info(f"Successfully retrieved attorney data for application {APP_NUMBER}")
    return True

async def test_get_app_continuity():
    logger.info("Testing get_app_continuity...")
    
    # Test with the application number
    start_time = datetime.now()
    result = await get_app_continuity(app_num=APP_NUMBER)
    duration = (datetime.now() - start_time).total_seconds()
    
    logger.info(f"get_app_continuity completed in {duration:.2f} seconds")
    
    # Save result
    await save_result(result, "get_app_continuity.json")
    
    # Log result summary
    if result.get("error", False):
        logger.error(f"Error: {result.get('message', 'Unknown error')}")
        return False
    
    logger.info(f"Successfully retrieved continuity data for application {APP_NUMBER}")
    return True

async def test_get_app_foreign_priority():
    logger.info("Testing get_app_foreign_priority...")
    
    # Test with the application number
    start_time = datetime.now()
    result = await get_app_foreign_priority(app_num=APP_NUMBER)
    duration = (datetime.now() - start_time).total_seconds()
    
    logger.info(f"get_app_foreign_priority completed in {duration:.2f} seconds")
    
    # Save result
    await save_result(result, "get_app_foreign_priority.json")
    
    # Log result summary
    if result.get("error", False):
        logger.error(f"Error: {result.get('message', 'Unknown error')}")
        return False
    
    logger.info(f"Successfully retrieved foreign priority data for application {APP_NUMBER}")
    return True

async def test_get_app_transactions():
    logger.info("Testing get_app_transactions...")
    
    # Test with the application number
    start_time = datetime.now()
    result = await get_app_transactions(app_num=APP_NUMBER)
    duration = (datetime.now() - start_time).total_seconds()
    
    logger.info(f"get_app_transactions completed in {duration:.2f} seconds")
    
    # Save result
    await save_result(result, "get_app_transactions.json")
    
    # Log result summary
    if result.get("error", False):
        logger.error(f"Error: {result.get('message', 'Unknown error')}")
        return False
    
    logger.info(f"Successfully retrieved transaction data for application {APP_NUMBER}")
    return True

async def test_get_app_documents():
    logger.info("Testing get_app_documents...")
    
    # Test with the application number
    start_time = datetime.now()
    result = await get_app_documents(app_num=APP_NUMBER)
    duration = (datetime.now() - start_time).total_seconds()
    
    logger.info(f"get_app_documents completed in {duration:.2f} seconds")
    
    # Save result
    await save_result(result, "get_app_documents.json")
    
    # Log result summary
    if result.get("error", False):
        logger.error(f"Error: {result.get('message', 'Unknown error')}")
        return False
    
    logger.info(f"Successfully retrieved document data for application {APP_NUMBER}")
    return True

async def test_get_app_associated_documents():
    logger.info("Testing get_app_associated_documents...")
    
    # Test with the application number
    start_time = datetime.now()
    result = await get_app_associated_documents(app_num=APP_NUMBER)
    duration = (datetime.now() - start_time).total_seconds()
    
    logger.info(f"get_app_associated_documents completed in {duration:.2f} seconds")
    
    # Save result
    await save_result(result, "get_app_associated_documents.json")
    
    # Log result summary
    if result.get("error", False):
        logger.error(f"Error: {result.get('message', 'Unknown error')}")
        return False
    
    logger.info(f"Successfully retrieved associated documents for application {APP_NUMBER}")
    return True

async def test_get_status_codes():
    logger.info("Testing get_status_codes...")
    
    # Test with a simple search
    start_time = datetime.now()
    result = await get_status_codes(
        limit=10
    )
    duration = (datetime.now() - start_time).total_seconds()
    
    logger.info(f"get_status_codes completed in {duration:.2f} seconds")
    
    # Save result
    await save_result(result, "get_status_codes.json")
    
    # Log result summary
    if result.get("error", False):
        logger.error(f"Error: {result.get('message', 'Unknown error')}")
        return False
    
    results = result.get("results", [])
    total = result.get("total", 0)
    logger.info(f"Found {total} status codes")
    return total > 0

async def test_get_status_codes_post():
    logger.info("Testing get_status_codes_post...")
    
    # Test with a simple search
    start_time = datetime.now()
    result = await get_status_codes_post(
        limit=10
    )
    duration = (datetime.now() - start_time).total_seconds()
    
    logger.info(f"get_status_codes_post completed in {duration:.2f} seconds")
    
    # Save result
    await save_result(result, "get_status_codes_post.json")
    
    # Log result summary
    if result.get("error", False):
        logger.error(f"Error: {result.get('message', 'Unknown error')}")
        return False
    
    results = result.get("results", [])
    total = result.get("total", 0)
    logger.info(f"Found {total} status codes")
    return total > 0

async def test_search_datasets():
    logger.info("Testing search_datasets...")
    
    # Test with a simple search for patent datasets
    start_time = datetime.now()
    result = await search_datasets(
        q="patent",
        limit=10
    )
    duration = (datetime.now() - start_time).total_seconds()
    
    logger.info(f"search_datasets completed in {duration:.2f} seconds")
    
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

async def test_get_dataset_product(product_id=None):
    logger.info("Testing get_dataset_product...")
    
    if not product_id:
        logger.warning("No product ID provided, using a default value that may not exist")
        product_id = "patent-pgn-2023"
    
    # Test with the product ID
    start_time = datetime.now()
    result = await get_dataset_product(
        product_id=product_id,
        limit=5
    )
    duration = (datetime.now() - start_time).total_seconds()
    
    logger.info(f"get_dataset_product completed in {duration:.2f} seconds")
    
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
    test_summary["tests"]["get_app"] = await test_get_app()
    test_summary["tests"]["search_applications"] = await test_search_applications()
    test_summary["tests"]["search_applications_post"] = await test_search_applications_post()
    test_summary["tests"]["download_applications"] = await test_download_applications()
    test_summary["tests"]["download_applications_post"] = await test_download_applications_post()
    test_summary["tests"]["get_app_metadata"] = await test_get_app_metadata()
    test_summary["tests"]["get_app_adjustment"] = await test_get_app_adjustment()
    test_summary["tests"]["get_app_assignment"] = await test_get_app_assignment()
    test_summary["tests"]["get_app_attorney"] = await test_get_app_attorney()
    test_summary["tests"]["get_app_continuity"] = await test_get_app_continuity()
    test_summary["tests"]["get_app_foreign_priority"] = await test_get_app_foreign_priority()
    test_summary["tests"]["get_app_transactions"] = await test_get_app_transactions()
    test_summary["tests"]["get_app_documents"] = await test_get_app_documents()
    test_summary["tests"]["get_app_associated_documents"] = await test_get_app_associated_documents()
    test_summary["tests"]["get_status_codes"] = await test_get_status_codes()
    test_summary["tests"]["get_status_codes_post"] = await test_get_status_codes_post()
    
    # Test datasets tools
    product_id = await test_search_datasets()
    test_summary["tests"]["search_datasets"] = bool(product_id)
    test_summary["tests"]["get_dataset_product"] = await test_get_dataset_product(product_id)
    
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