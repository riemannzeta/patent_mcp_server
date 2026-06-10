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

# Document-list XML, shape captured live from
# GET /ts/cd/casedocs/sn74612654/info on 2026-06-10 (namespace and field
# names verbatim; this endpoint serves XML only and 406es on JSON)
MOCK_TSDR_DOCUMENT_LIST_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><DocumentList xmlns="urn:us:gov:doc:uspto:trademark"><Document><SerialNumber>78787878</SerialNumber><DocumentTypeCode>OOA</DocumentTypeCode><DocumentTypeCodeDescriptionText>Offc Action Outgoing</DocumentTypeCodeDescriptionText><CategoryTypeCode>O</CategoryTypeCode><CategoryTypeCodeDescriptionText>Outgoing</CategoryTypeCodeDescriptionText><MailRoomDate>2020-01-15-05:00</MailRoomDate><ScanDateTime>2020-01-15T10:20:37.000-05:00</ScanDateTime><TotalPageQuantity>5</TotalPageQuantity><PageMediaTypeList><PageMediaTypeName>image/tiff</PageMediaTypeName></PageMediaTypeList></Document><Document><SerialNumber>78787878</SerialNumber><DocumentTypeCode>SPE</DocumentTypeCode><DocumentTypeCodeDescriptionText>Specimen</DocumentTypeCodeDescriptionText><CategoryTypeCode>I</CategoryTypeCode><CategoryTypeCodeDescriptionText>Incoming</CategoryTypeCodeDescriptionText><MailRoomDate>2019-08-01-04:00</MailRoomDate><ScanDateTime>2019-08-02T09:00:00.000-04:00</ScanDateTime><TotalPageQuantity>2</TotalPageQuantity><PageMediaTypeList><PageMediaTypeName>image/jpeg</PageMediaTypeName></PageMediaTypeList></Document></DocumentList>"""
