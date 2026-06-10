"""Mock responses for the TSDR API (tsdrapi.uspto.gov)."""
import base64

# Trimmed shape of /casestatus/sn{N}/info.json
MOCK_TSDR_STATUS_RESPONSE = {
    "trademarks": [
        {
            "status": {
                "serialNumber": "78787878",
                "usRegistrationNumber": "3500027",
                "markElement": "TESTMARK",
                "status": 700,
                "statusDescription": "Registered",
                "statusDate": "2008-09-09",
                "filingDate": "2006-01-11",
                "usRegistrationDate": "2008-09-09",
                "standardCharacterClaim": True,
                "markDrawingCode": "4000",
            },
            "parties": {
                "owners": [
                    {
                        "name": "Test Trademark Owner LLC",
                        "address": {"city": "Alexandria", "state": "VA"},
                    }
                ]
            },
            "gsList": [
                {
                    "internationalClasses": ["009"],
                    "description": "Computer software for testing",
                }
            ],
        }
    ]
}

# Minimal valid PDF for binary-response tests
MOCK_TSDR_PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< >>\n%%EOF"
MOCK_TSDR_PDF_CONTENT = base64.b64encode(MOCK_TSDR_PDF_BYTES).decode("utf-8")

# Minimal PNG header bytes for image tests
MOCK_TSDR_IMAGE_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
MOCK_TSDR_IMAGE_CONTENT = base64.b64encode(MOCK_TSDR_IMAGE_BYTES).decode("utf-8")
