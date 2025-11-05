"""Mock responses for api.uspto.gov API."""

# Mock Application Response (get_app)
MOCK_APP_RESPONSE = {
    "applicationNumberText": "14412875",
    "applicationType": "utility",
    "applicationMetaData": {
        "inventionTitle": "Test Patent Application",
        "filingDate": "2014-06-18",
        "applicationStatus": "patented",
        "patentNumber": "9876543"
    },
    "inventorNameArrayText": ["John Doe", "Jane Smith"],
    "assigneeEntityName": "Test Corporation",
    "groupArtUnitNumber": "2100"
}

# Mock Search Applications Response
MOCK_SEARCH_APPS_RESPONSE = {
    "total": 1,
    "totalPages": 1,
    "currentPage": 1,
    "items": [
        {
            "applicationNumberText": "14412875",
            "applicationType": "utility",
            "applicationMetaData": {
                "inventionTitle": "Test Application",
                "filingDate": "2014-06-18",
                "applicationStatus": "patented"
            },
            "inventorNameArrayText": ["John Doe"],
            "assigneeEntityName": "Test Corp"
        }
    ]
}

# Mock Application Metadata Response
MOCK_APP_METADATA_RESPONSE = {
    "applicationNumberText": "14412875",
    "inventionTitle": "Test Patent Application",
    "filingDate": "2014-06-18",
    "publicationDate": "2015-12-24",
    "patentNumber": "9876543",
    "patentIssueDate": "2018-01-02",
    "applicationStatus": "patented",
    "applicationType": "utility"
}

# Mock Patent Term Adjustment Response
MOCK_ADJUSTMENT_RESPONSE = {
    "applicationNumberText": "14412875",
    "ptaAdjustment": {
        "totalDays": 123,
        "aDelayDays": 0,
        "bDelayDays": 45,
        "cDelayDays": 78,
        "overlappingDays": 0,
        "nonOverlappingDays": 123
    },
    "calculationDate": "2018-01-02"
}

# Mock Assignment Response
MOCK_ASSIGNMENT_RESPONSE = {
    "applicationNumberText": "14412875",
    "assignments": [
        {
            "assignmentId": "123456",
            "conveyanceText": "ASSIGNMENT OF ASSIGNORS INTEREST",
            "recordedDate": "2014-07-15",
            "executionDate": "2014-06-20",
            "assignors": ["John Doe", "Jane Smith"],
            "assignees": ["Test Corporation"],
            "correspondenceAddress": {
                "name": "Patent Attorney",
                "address1": "123 Main St",
                "city": "San Francisco",
                "state": "CA",
                "postalCode": "94105"
            }
        }
    ]
}

# Mock Attorney Response
MOCK_ATTORNEY_RESPONSE = {
    "applicationNumberText": "14412875",
    "attorneys": [
        {
            "registrationNumber": "12345",
            "name": "John Attorney",
            "type": "LEAD"
        },
        {
            "registrationNumber": "67890",
            "name": "Jane Agent",
            "type": "ASSOCIATE"
        }
    ],
    "correspondenceAddress": {
        "name": "Law Firm LLP",
        "address1": "456 Legal Ave",
        "city": "New York",
        "state": "NY",
        "postalCode": "10001"
    }
}

# Mock Continuity Response
MOCK_CONTINUITY_RESPONSE = {
    "applicationNumberText": "14412875",
    "parentContinuity": [
        {
            "applicationNumberText": "13123456",
            "filingDate": "2011-05-15",
            "relationshipType": "continuation-in-part",
            "applicationStatus": "abandoned"
        }
    ],
    "childContinuity": [
        {
            "applicationNumberText": "15234567",
            "filingDate": "2016-08-20",
            "relationshipType": "continuation",
            "applicationStatus": "pending"
        }
    ]
}

# Mock Foreign Priority Response
MOCK_FOREIGN_PRIORITY_RESPONSE = {
    "applicationNumberText": "14412875",
    "foreignPriority": [
        {
            "country": "JP",
            "applicationNumber": "2013-123456",
            "filingDate": "2013-06-18",
            "priorityClaimed": True
        },
        {
            "country": "EP",
            "applicationNumber": "13789012",
            "filingDate": "2013-06-20",
            "priorityClaimed": True
        }
    ]
}

# Mock Transactions Response
MOCK_TRANSACTIONS_RESPONSE = {
    "applicationNumberText": "14412875",
    "transactions": [
        {
            "code": "WFEE",
            "description": "Filing Fee Paid",
            "date": "2014-06-18"
        },
        {
            "code": "PUB",
            "description": "Published Application",
            "date": "2015-12-24"
        },
        {
            "code": "ISSUE",
            "description": "Patent Issued",
            "date": "2018-01-02"
        }
    ]
}

# Mock Documents Response
MOCK_DOCUMENTS_RESPONSE = {
    "applicationNumberText": "14412875",
    "documents": [
        {
            "mailRoomDate": "2014-06-18",
            "documentCode": "A",
            "description": "Application",
            "pageCount": 25
        },
        {
            "mailRoomDate": "2015-03-15",
            "documentCode": "CTNF",
            "description": "Office Action",
            "pageCount": 12
        },
        {
            "mailRoomDate": "2015-09-15",
            "documentCode": "R.92",
            "description": "Response to Office Action",
            "pageCount": 18
        }
    ]
}

# Mock Associated Documents Response
MOCK_ASSOCIATED_DOCS_RESPONSE = {
    "applicationNumberText": "14412875",
    "associatedDocuments": [
        {
            "documentId": "DOC123",
            "documentType": "IDS",
            "description": "Information Disclosure Statement",
            "filingDate": "2014-07-01"
        },
        {
            "documentId": "DOC456",
            "documentType": "ADS",
            "description": "Application Data Sheet",
            "filingDate": "2014-06-18"
        }
    ]
}

# Mock Status Codes Response
MOCK_STATUS_CODES_RESPONSE = {
    "total": 3,
    "items": [
        {
            "code": "01",
            "description": "Application Received",
            "category": "filing"
        },
        {
            "code": "30",
            "description": "Office Action Mailed",
            "category": "prosecution"
        },
        {
            "code": "150",
            "description": "Patent Issued",
            "category": "disposition"
        }
    ]
}

# Mock Datasets Search Response
MOCK_DATASETS_RESPONSE = {
    "products": [
        {
            "productShortName": "patent-pgn-2023",
            "productTitle": "Patent Grant Full Text Data 2023",
            "productDescription": "Full text of granted patents for 2023",
            "category": "patents",
            "datasetName": "Patent Grant Full Text",
            "files": [
                {
                    "fileName": "ipg230103.zip",
                    "fileUrl": "https://example.com/ipg230103.zip",
                    "fileSize": "50MB",
                    "dataDate": "2023-01-03"
                }
            ]
        }
    ],
    "total": 1
}

# Mock Dataset Product Response
MOCK_DATASET_PRODUCT_RESPONSE = {
    "productShortName": "patent-pgn-2023",
    "productTitle": "Patent Grant Full Text Data 2023",
    "productDescription": "Full text of granted patents for 2023",
    "category": "patents",
    "datasetName": "Patent Grant Full Text",
    "files": [
        {
            "fileName": "ipg230103.zip",
            "fileUrl": "https://example.com/ipg230103.zip",
            "fileSize": "50MB",
            "dataDate": "2023-01-03"
        },
        {
            "fileName": "ipg230110.zip",
            "fileUrl": "https://example.com/ipg230110.zip",
            "fileSize": "48MB",
            "dataDate": "2023-01-10"
        }
    ],
    "totalFiles": 2
}

# Mock Error Responses
MOCK_ERROR_NOT_FOUND = {
    "error": {
        "message": "Application not found",
        "code": "NOT_FOUND",
        "status": 404
    }
}

MOCK_ERROR_INVALID_APP_NUMBER = {
    "error": {
        "message": "Invalid application number format",
        "code": "INVALID_INPUT",
        "status": 400
    }
}

MOCK_ERROR_UNAUTHORIZED = {
    "error": {
        "message": "API key is missing or invalid",
        "code": "UNAUTHORIZED",
        "status": 401
    }
}

MOCK_ERROR_RATE_LIMITED = {
    "error": {
        "message": "Rate limit exceeded",
        "code": "RATE_LIMITED",
        "status": 429,
        "retryAfter": 60
    }
}

MOCK_ERROR_SERVER_ERROR = {
    "error": {
        "message": "Internal server error",
        "code": "SERVER_ERROR",
        "status": 500
    }
}

# Mock Empty Responses
MOCK_EMPTY_SEARCH_RESPONSE = {
    "total": 0,
    "items": []
}

MOCK_EMPTY_DOCUMENTS_RESPONSE = {
    "applicationNumberText": "14412875",
    "documents": []
}

# Helper function to create mock search response with multiple results
def create_mock_search_response(count: int, offset: int = 0) -> dict:
    """Create a mock search response with specified number of results.

    Args:
        count: Number of results to include
        offset: Starting offset

    Returns:
        Mock search response dictionary
    """
    items = []
    for i in range(count):
        app_num = str(14412875 + i + offset)
        items.append({
            "applicationNumberText": app_num,
            "applicationType": "utility",
            "applicationMetaData": {
                "inventionTitle": f"Test Application {i+1}",
                "filingDate": "2014-06-18",
                "applicationStatus": "pending"
            },
            "inventorNameArrayText": ["Test Inventor"],
            "assigneeEntityName": "Test Corp"
        })

    return {
        "total": count,
        "totalPages": (count // 25) + 1,
        "currentPage": (offset // 25) + 1,
        "items": items
    }
