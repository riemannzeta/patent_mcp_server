#!/usr/bin/env python3
import asyncio
import json
import logging
import sys
import os
from datetime import datetime

# Set up detailed logging
logging.basicConfig(
    #level=logging.WARNING,
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Create logger
logger = logging.getLogger('test_patents')

# Import the clients
from patent_mcp_server.uspto.ppubs_uspto_gov import PpubsClient
from patent_mcp_server.uspto.api_uspto_gov import ApiUsptoClient

# Main test function
async def test_ppubs_direct():
    logger.info("Starting USPTO Public Search direct test")
    
    # Patent number to test
    patent_number = "9876543"
    logger.info(f"Testing search for U.S. Patent No. {patent_number}")
    
    try:
        # Create client instance directly
        client = PpubsClient()
        
        # Initialize session
        await client.get_session()
        
        # First test: Get patent by number
        logger.info("TEST 1: Search for patent by number")
        start_time = datetime.now()
        
        # Use exact patent number match with specific field
        query = f'patentNumber:"{patent_number}"'
        
        # First search for the patent
        search_result = await client.run_query(
            query=query,
            sources=["USPAT"],
            limit=1
        )
        
        # Log the raw search result for debugging
        logger.info(f"Raw search result type: {type(search_result)}")
        logger.info(f"Raw search result: {json.dumps(search_result, indent=2, default=str)}")
        
        if search_result.get("error", False):
            logger.error(f"Error searching for patent: {search_result.get('message', 'Unknown error')}")
            return
        
        total_found = search_result.get("numFound", 0)
        logger.info(f"Total documents found: {total_found}")
        
        # The USPTO API returns patents in "patents" array, not "docs"
        if search_result.get("patents") and len(search_result["patents"]) > 0:
            patent = search_result["patents"][0]
            logger.info(f"Found patent: {patent.get('guid')}, Title: {patent.get('inventionTitle')}")
        elif search_result.get("docs") and len(search_result["docs"]) > 0:
            patent = search_result["docs"][0]
            logger.info(f"Found patent: {patent.get('guid')}, Title: {patent.get('inventionTitle')}")
        elif not search_result.get("patents") or len(search_result["patents"]) == 0:
            logger.info(f"Patent {patent_number} not found with plain query, trying alternate approach")
            # Let's try a different approach with the proper field syntax
            logger.info("Trying alternate query approach with pn. field")
            alt_query = f'"{patent_number}".pn.'
            search_result = await client.run_query(
                query=alt_query,
                sources=["USPAT"],
                limit=1
            )
            logger.info(f"Alternate search result: {json.dumps(search_result, indent=2, default=str)}")
            
            if not search_result.get("patents") and not search_result.get("docs"):
                logger.error(f"Still no results for patent {patent_number}")
                return
            
            # Use the result from the alternate query
            if search_result.get("patents") and len(search_result["patents"]) > 0:
                patent = search_result["patents"][0]
            else:
                patent = search_result["docs"][0]
            logger.info(f"Found patent with alternate query: {patent.get('guid')}, Title: {patent.get('inventionTitle')}")
        else:
            logger.error(f"Unexpected result structure: {search_result}")
            return
        
        # Now get the full document using the patent info from above
        logger.info(f"Found patent with GUID: {patent['guid']}, Type: {patent['type']}")
        
        # Get full document
        logger.info("Getting full document details")
        document_result = await client.get_document(patent["guid"], patent["type"])
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"Patent retrieval completed in {duration:.2f} seconds")
        
        # Save patent data to json directory
        json_filepath = os.path.join("json", f"patent_{patent_number}_data.json")
        os.makedirs(os.path.dirname(json_filepath), exist_ok=True)
        with open(json_filepath, "w") as f:
            json.dump(document_result, f, indent=2)
        logger.info(f"Full patent data saved to {json_filepath}")
        
        # Second test: Download the patent PDF if available (use imageLocation and pageCount)
        # Handle different field naming in the response
        image_location = patent.get("imageLocation", patent.get("document_structure", {}).get("image_location"))
        page_count = patent.get("pageCount", patent.get("document_structure", {}).get("page_count"))
        
        if image_location and page_count:
            logger.info("\nTEST 2: Download patent PDF")
            start_time = datetime.now()
            
            pdf_result = await client.download_image(
                patent["guid"],
                image_location,
                page_count,
                patent["type"]
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.info(f"PDF download completed in {duration:.2f} seconds")
            
            if pdf_result.get("error", False):
                logger.error(f"Error downloading PDF: {pdf_result.get('message', 'Unknown error')}")
            else:
                logger.info("PDF download successful!")
                
                # Save PDF if available
                content = pdf_result.get("content")
                success = pdf_result.get("success", False)
                
                if content and success:
                    try:
                        import base64
                        pdf_content = base64.b64decode(content)
                        filename = pdf_result.get("filename", f"patent_{patent_number}.pdf")
                        
                        # Save PDF to pdfs directory
                        pdf_filepath = os.path.join("pdfs", filename)
                        os.makedirs(os.path.dirname(pdf_filepath), exist_ok=True)
                        with open(pdf_filepath, "wb") as f:
                            f.write(pdf_content)
                        logger.info(f"PDF saved to {pdf_filepath}")
                        
                        # Log the size of the PDF
                        pdf_size = os.path.getsize(pdf_filepath) / 1024  # Size in KB
                        logger.info(f"PDF size: {pdf_size:.2f} KB")
                    except Exception as e:
                        logger.error(f"Error saving PDF: {e}")
    
    except Exception as e:
        logger.error(f"Error during test: {e}", exc_info=True)
    
    finally:
        # Close the client
        if 'client' in locals():
            await client.close()
            logger.info("Client closed")

async def test_api_uspto_direct():
    logger.info("Starting USPTO API direct test")
    
    # Appliction number to test
    app_number = "14412875"
    logger.info(f"Testing API for U.S. Patent Application No. {app_number}")

    USPTO_API_BASE = "https://api.uspto.gov"
    
    try:
        # Create client instance directly
        client = ApiUsptoClient()
        
        # Test 1: Get patent metadata
        logger.info("TEST 1: Get application metadata")
        start_time = datetime.now()

        url = f"{USPTO_API_BASE}/api/v1/patent/applications/{app_number}/meta-data"
        metadata_result = await client.make_request(url)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"Patent metadata retrieval completed in {duration:.2f} seconds")
        
        # Log basic metadata information
        if not metadata_result.get("error", False):
            logger.info(f"Patent metadata retrieved successfully")
            
            # Save metadata to json directory
            json_filepath = os.path.join("json", f"app_{app_number}_metadata.json")
            os.makedirs(os.path.dirname(json_filepath), exist_ok=True)
            with open(json_filepath, "w") as f:
                json.dump(metadata_result, f, indent=2)
            logger.info(f"Application metadata saved to {json_filepath}")
            
            # Extract and log some key information
            patent_title = metadata_result.get("patentTitle", "Unknown Title")
            filing_date = metadata_result.get("filingDate", "Unknown Filing Date")
            issue_date = metadata_result.get("issueDate", "Unknown Issue Date")
            
            logger.info(f"Patent Title: {patent_title}")
            logger.info(f"Filing Date: {filing_date}")
            logger.info(f"Issue Date: {issue_date}")
        else:
            logger.error(f"Error retrieving patent metadata: {metadata_result.get('message', 'Unknown error')}")
    
    except Exception as e:
        logger.error(f"Error during test: {e}", exc_info=True)
    
    finally:
        # Close the client
        if 'client' in locals():
            await client.close()
            logger.info("Client closed")

if __name__ == "__main__":
    # Run the tests
    try:
        logger.info("Starting direct test script")
        #asyncio.run(test_ppubs_direct())
        asyncio.run(test_api_uspto_direct())
        logger.info("Test script completed")
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)