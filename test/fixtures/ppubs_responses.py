"""Mock responses for ppubs.uspto.gov API."""
import base64

# Mock Session Response
MOCK_SESSION_RESPONSE = {
    "userCase": {
        "caseId": "test-case-123456",
        "userId": "test-user",
        "queries": [],
        "searchId": 1
    },
    "settings": {
        "defaultOperator": "OR",
        "expandPlurals": True,
        "britishEquivalents": True
    }
}

# Mock Search Count Response
MOCK_COUNTS_RESPONSE = {
    "numFound": 1,
    "status": "success"
}

# Mock Patent Search Response
MOCK_SEARCH_RESPONSE = {
    "numFound": 1,
    "start": 0,
    "docs": [
        {
            "guid": "US-9876543-B2",
            "patentNumber": "9876543",
            "type": "USPAT",
            "title": "System and Method for Testing Patent Search",
            "abstract": "A comprehensive system for testing patent search capabilities including full-text search, document retrieval, and PDF generation...",
            "inventors": ["John Doe", "Jane Smith"],
            "assignee": "Test Corporation",
            "date_publ": "2018-01-02",
            "imageLocation": "US/09/876/543",
            "pageCount": 10,
            "documentStructure": {
                "image_location": "US/09/876/543",
                "page_count": 10
            },
            "claims": [
                "1. A method for testing patent search comprising...",
                "2. The method of claim 1, further comprising..."
            ]
        }
    ],
    "patents": [
        {
            "guid": "US-9876543-B2",
            "patentNumber": "9876543",
            "type": "USPAT",
            "title": "System and Method for Testing Patent Search",
            "abstract": "A comprehensive system for testing patent search capabilities including full-text search, document retrieval, and PDF generation...",
            "inventors": ["John Doe", "Jane Smith"],
            "assignee": "Test Corporation",
            "date_publ": "2018-01-02",
            "imageLocation": "US/09/876/543",
            "pageCount": 10,
            "documentStructure": {
                "image_location": "US/09/876/543",
                "page_count": 10
            }
        }
    ]
}

# Mock Application Search Response
MOCK_APPLICATION_SEARCH_RESPONSE = {
    "numFound": 1,
    "start": 0,
    "docs": [
        {
            "guid": "US-20180000001-A1",
            "publicationNumber": "20180000001",
            "type": "US-PGPUB",
            "title": "Test Patent Application",
            "abstract": "Test application abstract...",
            "inventors": ["Alice Johnson"],
            "assignee": "Test Corp",
            "date_publ": "2018-01-01"
        }
    ],
    "patents": [
        {
            "guid": "US-20180000001-A1",
            "publicationNumber": "20180000001",
            "type": "US-PGPUB",
            "title": "Test Patent Application",
            "abstract": "Test application abstract...",
            "inventors": ["Alice Johnson"],
            "assignee": "Test Corp",
            "date_publ": "2018-01-01"
        }
    ]
}

# Mock Full Document Response
MOCK_DOCUMENT_RESPONSE = {
    "guid": "US-9876543-B2",
    "patentNumber": "9876543",
    "type": "USPAT",
    "title": "System and Method for Testing Patent Search",
    "abstract": "A comprehensive system for testing patent search capabilities including full-text search, document retrieval, and PDF generation...",
    "inventors": ["John Doe", "Jane Smith"],
    "assignee": "Test Corporation",
    "date_publ": "2018-01-02",
    "sections": {
        "abstract": "Detailed abstract text describing the invention in comprehensive detail...",
        "claims": [
            "1. A method for testing patent search comprising: a) establishing a session; b) executing a search query; c) retrieving results; and d) validating responses.",
            "2. The method of claim 1, further comprising: e) downloading PDF documents; and f) verifying content integrity.",
            "3. The method of claim 1, wherein the search query includes boolean operators and field-specific searches.",
            "4. The method of claim 2, wherein the PDF documents are base64-encoded.",
            "5. A system for implementing the method of claim 1."
        ],
        "description": "DETAILED DESCRIPTION OF THE INVENTION\n\nThe present invention relates to a comprehensive system for testing patent search capabilities...",
        "background": "BACKGROUND OF THE INVENTION\n\nField of the Invention\n\nThe present invention relates to software testing...",
        "summary": "SUMMARY OF THE INVENTION\n\nIt is an object of the invention to provide a testing system...",
        "drawings": []
    },
    "imageLocation": "US/09/876/543",
    "pageCount": 10,
    "documentStructure": {
        "image_location": "US/09/876/543",
        "page_count": 10
    }
}

# Mock PDF Request Response (Print Job ID)
MOCK_PDF_REQUEST_RESPONSE = "print-job-123456789"

# Mock PDF Status Response
MOCK_PDF_STATUS_PENDING = [
    {
        "printStatus": "PROCESSING",
        "jobId": "print-job-123456789",
        "progress": 50
    }
]

MOCK_PDF_STATUS_COMPLETED = [
    {
        "printStatus": "COMPLETED",
        "jobId": "print-job-123456789",
        "pdfName": "test-patent-9876543.pdf",
        "progress": 100
    }
]

# Mock PDF Content (Minimal valid PDF - base64 encoded)
MOCK_PDF_CONTENT = base64.b64encode(
    b"%PDF-1.4\n"
    b"1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
    b"2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n"
    b"3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n"
    b"/Contents 4 0 R\n>>\nendobj\n"
    b"4 0 obj\n<<\n/Length 44\n>>\nstream\n"
    b"BT\n/F1 12 Tf\n100 700 Td\n(Test Patent PDF) Tj\nET\n"
    b"endstream\nendobj\n"
    b"xref\n0 5\n"
    b"0000000000 65535 f\n"
    b"0000000009 00000 n\n"
    b"0000000058 00000 n\n"
    b"0000000115 00000 n\n"
    b"0000000214 00000 n\n"
    b"trailer\n<<\n/Size 5\n/Root 1 0 R\n>>\n"
    b"startxref\n306\n%%EOF"
).decode('utf-8')

# Mock Error Responses
MOCK_ERROR_INVALID_QUERY = {
    "error": {
        "message": "Invalid query syntax",
        "code": "INVALID_QUERY",
        "details": "Query contains unsupported characters or operators"
    }
}

MOCK_ERROR_SESSION_EXPIRED = {
    "error": {
        "message": "Session expired",
        "code": "SESSION_EXPIRED",
        "details": "Please create a new session"
    }
}

MOCK_ERROR_NOT_FOUND = {
    "error": {
        "message": "Document not found",
        "code": "NOT_FOUND",
        "details": "The requested patent document does not exist"
    }
}

MOCK_ERROR_RATE_LIMITED = {
    "error": {
        "message": "Rate limit exceeded",
        "code": "RATE_LIMITED",
        "details": "Too many requests. Please retry after 60 seconds"
    }
}

# Mock Empty Search Response
MOCK_EMPTY_SEARCH_RESPONSE = {
    "numFound": 0,
    "start": 0,
    "docs": [],
    "patents": []
}

# Helper function to create mock search response with multiple results
def create_mock_search_response(count: int, start: int = 0) -> dict:
    """Create a mock search response with specified number of results.

    Args:
        count: Number of results to include
        start: Starting position

    Returns:
        Mock search response dictionary
    """
    patents = []
    for i in range(count):
        patent_num = str(9876543 + i)
        patents.append({
            "guid": f"US-{patent_num}-B2",
            "patentNumber": patent_num,
            "type": "USPAT",
            "title": f"Test Patent {i+1}",
            "abstract": f"Abstract for test patent {i+1}...",
            "inventors": ["Test Inventor"],
            "assignee": "Test Corp",
            "date_publ": "2018-01-02",
            "imageLocation": f"US/{patent_num[:2]}/{patent_num[2:5]}/{patent_num[5:]}",
            "pageCount": 10
        })

    return {
        "numFound": count,
        "start": start,
        "docs": patents,
        "patents": patents
    }
