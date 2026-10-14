"""Unit tests for file-wrapper XML text extraction and
odp_download_document(format="text").

The XML snippets keep the structure of real papers downloaded from
/api/v1/download/applications/{app}/{id}/xmlarchive on 2026-10-14
(18402543 CTFR and CLM, 13806514 REM and CLM, 16123456 IDS), cut to a few
elements each.
"""

import base64
import io
import tarfile
from unittest.mock import AsyncMock, patch

import pytest

from patent_mcp_server.constants import Defaults
from patent_mcp_server.patents import odp_download_document
from patent_mcp_server.util.document_text import (
    DocumentTextError, xml_from_archive, xml_to_text,
)

DOWNLOAD = "patent_mcp_server.patents.api_client.download_file"

ST96_NS = (
    'xmlns:uspat="urn:us:gov:doc:uspto:patent" '
    'xmlns:uscom="urn:us:gov:doc:uspto:common" '
    'xmlns:com="http://www.wipo.int/standards/XMLSchema/ST96/Common"'
)

OFFICE_ACTION_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<uspat:OutgoingDocument {ST96_NS}>
  <uspat:DocumentMetadata com:id="id-002">
    <uscom:DocumentCode>CTFR</uscom:DocumentCode>
    <uscom:ApplicationNumberText>18/402,543</uscom:ApplicationNumberText>
  </uspat:DocumentMetadata>
<uscom:P com:pNumber="1"><?PageStart number='1'?><uscom:BoundaryDataReference com:idref="bd-001" /><com:B>DETAILED ACTION</com:B></uscom:P>
<uscom:P com:pNumber="4"></uscom:P>
<uscom:FormParagraph><uscom:FormParagraphNumber>07-03-aia</uscom:FormParagraphNumber><uscom:P com:pNumber="6">The present application, filed on or after March 16, 2013, is being  examined under the first inventor to file provisions of the AIA.</uscom:P>
</uscom:FormParagraph>
<uscom:P com:pNumber="9">Claims 1, 3-4, and 7-8 are rejected under 35 U.S.C. 102(a)(1) as being anticipated by Zhao.</uscom:P>
<uscom:BoundaryDataBag><uscom:BoundaryData com:id="bd-001"><uscom:HeaderText>Application/Control Number: 18/402,543</uscom:HeaderText></uscom:BoundaryData></uscom:BoundaryDataBag>
</uspat:OutgoingDocument>
""".encode()

CLAIMS_XML = f"""<?xml version="1.0" encoding="utf-8"?>
<uspat:ClaimsDocument {ST96_NS} xmlns:pat="http://www.wipo.int/standards/XMLSchema/ST96/Patent">
<uspat:DocumentMetadata><uscom:DocumentCode>CLM</uscom:DocumentCode></uspat:DocumentMetadata>
<uspat:Claim com:id="CLM-00001"><pat:ClaimNumber>1</pat:ClaimNumber><uspat:ClaimStatusCategory>Currently amended</uspat:ClaimStatusCategory><uspat:ClaimText>Claim 1 (currently amended): A housing comprising:</uspat:ClaimText><uspat:ClaimText>wherein<com:Del>, in the assembled state, </com:Del>the parts form a space,</uspat:ClaimText><uspat:ClaimText><com:Ins>wherein the deformable means com</com:Ins><uscom:OCRConfidenceData uscom:ocrConfidenceCode="5"><com:Ins>p</com:Ins></uscom:OCRConfidenceData><com:Ins>rise two side webs</com:Ins><uscom:OCRConfidenceData uscom:ocrConfidenceCode="5"><com:Ins>,</com:Ins></uscom:OCRConfidenceData></uspat:ClaimText></uspat:Claim>
</uspat:ClaimsDocument>
""".encode()

OLD_REMARKS_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<pat:IncomingDocument xmlns:pat="urn:us:gov:doc:uspto:patent" xmlns="urn:us:gov:doc:uspto:patent">
<pat:DocumentCode>REM</pat:DocumentCode><pat:DocumentHeaderDetails><pat:ApplicationHeaderDetails><pat:ApplicationNumber>13806514</pat:ApplicationNumber></pat:ApplicationHeaderDetails></pat:DocumentHeaderDetails>
<pat:MailRoomDate>2016-12-05</pat:MailRoomDate>
<pat:Heading pat:id="h-1">REMARKS</pat:Heading>
<pat:P pat:id="p-1">the rejection pursuant to 35 U.S.C. <pat:OCRConfidenceData pat:levelNumber="5">\xc2\xa7</pat:OCRConfidenceData> 112 was withdrawn.</pat:P>
</pat:IncomingDocument>
"""

RED_BOOK_CLAIMS_XML = b"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE us-patent-application SYSTEM "PATI-v1.0.3-2011-06-23.dtd">
<us-patent-application lang="EN">
  <us-bibliographic-data-application><application-reference><document-id><doc-number>13806514</doc-number></document-id></application-reference></us-bibliographic-data-application>
  <claims id="CLM-00000">
    <claim id="CLM-00001" num="1"><claim-text><claim-ref idref="CLM-00001">1.</claim-ref> A device for fluid power recuperation.</claim-text></claim>
    <claim id="CLM-00002" num="2"><claim-text>2. The device according to claim 1.</claim-text></claim>
  </claims>
</us-patent-application>
"""

IDS_TABLE_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<uspat:IncomingDocument {ST96_NS}>
<uscom:DataTable><uscom:TableRow>
  <uscom:TableHeaderCell>Cite No</uscom:TableHeaderCell>
  <uscom:TableHeaderCell>Document Number</uscom:TableHeaderCell>
</uscom:TableRow><uscom:TableRow>
  <uscom:TableDataCell></uscom:TableDataCell>
  <uscom:TableDataCell>US-2015/0242760</uscom:TableDataCell>
</uscom:TableRow></uscom:DataTable>
</uspat:IncomingDocument>
""".encode()


def _tar(members):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for name, data in members:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def _download_ok(archive: bytes):
    return {
        "success": True,
        "content_type": "application/octet-stream",
        "size_bytes": len(archive),
        "content": base64.b64encode(archive).decode("ascii"),
    }


# ---------------------------------------------------------------------------
# xml_to_text
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_office_action_body_without_metadata_or_page_headers():
    text = xml_to_text(OFFICE_ACTION_XML)
    assert text.split("\n\n") == [
        "DETAILED ACTION",
        "The present application, filed on or after March 16, 2013, is being "
        "examined under the first inventor to file provisions of the AIA.",
        "Claims 1, 3-4, and 7-8 are rejected under 35 U.S.C. 102(a)(1) as being "
        "anticipated by Zhao.",
    ]
    assert "18/402,543" not in text
    assert "07-03-aia" not in text
    assert "CTFR" not in text


@pytest.mark.unit
def test_claim_amendments_keep_their_markup():
    text = xml_to_text(CLAIMS_XML)
    assert text.split("\n\n") == [
        "Claim 1 (currently amended): A housing comprising:",
        "wherein~~, in the assembled state,~~ the parts form a space,",
        # The OCR wrappers split the insertion; it comes out as one run.
        "++wherein the deformable means comprise two side webs,++",
    ]


@pytest.mark.unit
def test_older_pat_schema_keeps_inline_ocr_text():
    text = xml_to_text(OLD_REMARKS_XML)
    assert text == "REMARKS\n\nthe rejection pursuant to 35 U.S.C. § 112 was withdrawn."


@pytest.mark.unit
def test_red_book_claims_with_external_dtd():
    text = xml_to_text(RED_BOOK_CLAIMS_XML)
    assert text == "1. A device for fluid power recuperation.\n\n2. The device according to claim 1."


@pytest.mark.unit
def test_table_rows_separate_cells():
    text = xml_to_text(IDS_TABLE_XML)
    assert text == "Cite No | Document Number\n\n| US-2015/0242760"


@pytest.mark.unit
@pytest.mark.parametrize("xml", [
    b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa">]><x>&a;</x>',
    b'<?xml version="1.0"?><!DOCTYPE x [<!ELEMENT x ANY>]><x/>',
    b"<x><unclosed></x>",
])
def test_refuses_entities_and_malformed_xml(xml):
    with pytest.raises(DocumentTextError):
        xml_to_text(xml)


# ---------------------------------------------------------------------------
# xml_from_archive
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_archive_picks_the_xml_member():
    archive = _tar([
        ("18402543/MS52/18402543.REM_svg.zip", b"PK\x03\x04"),
        ("18402543/MS52/18402543.REM.XML", b"<x/>"),
    ])
    assert xml_from_archive(archive) == ("18402543.REM.XML", b"<x/>")


@pytest.mark.unit
@pytest.mark.parametrize("archive", [
    b"not a tar",
    _tar([("a/page.zip", b"PK")]),
])
def test_archive_without_xml(archive):
    with pytest.raises(DocumentTextError):
        xml_from_archive(archive)


# ---------------------------------------------------------------------------
# odp_download_document(format="text")
# ---------------------------------------------------------------------------

@pytest.mark.unit
async def test_text_format_requests_the_xml_archive():
    archive = _tar([("18402543/MUZJ/Final Rejection.xml", OFFICE_ACTION_XML)])
    mock = AsyncMock(return_value=_download_ok(archive))
    with patch(DOWNLOAD, new=mock):
        result = await odp_download_document("18402543", "muzjazybx54x145", format="text")

    assert mock.call_args.args[0].endswith(
        "/api/v1/download/applications/18402543/MUZJAZYBX54X145/xmlarchive"
    )
    assert result["success"] is True
    assert result["source_file"] == "Final Rejection.xml"
    assert result["text"].startswith("DETAILED ACTION\n\n")
    assert result["total_chars"] == len(result["text"])
    assert result["next_offset"] is None
    assert "content" not in result


@pytest.mark.unit
async def test_pdf_stays_the_default():
    mock = AsyncMock(return_value=_download_ok(b"%PDF-1.4"))
    with patch(DOWNLOAD, new=mock):
        result = await odp_download_document("18402543", "MUZJAZYBX54X145")
    assert mock.call_args.args[0].endswith("/MUZJAZYBX54X145.pdf")
    assert result["filename"] == "18402543-MUZJAZYBX54X145.pdf"


@pytest.mark.unit
async def test_text_pages_at_paragraph_breaks():
    size = Defaults.DOCUMENT_TEXT_PAGE_CHARS
    paragraphs = [("word " * 199 + "end") for _ in range(size * 3 // 1000)]
    body = "".join(f"<uscom:P>{p}</uscom:P>" for p in paragraphs)
    xml = f"<uspat:OutgoingDocument {ST96_NS}>{body}</uspat:OutgoingDocument>".encode()
    archive = _tar([("a/b/x.xml", xml)])
    expected = "\n\n".join(paragraphs)

    pages, offset = [], 0
    with patch(DOWNLOAD, new=AsyncMock(return_value=_download_ok(archive))):
        while offset is not None:
            result = await odp_download_document("18402543", "ABC", format="text", text_offset=offset)
            assert len(result["text"]) <= size
            pages.append(result["text"])
            offset = result["next_offset"]

    assert len(pages) > 1
    assert "".join(pages) == expected
    assert all(page.endswith("\n\n") for page in pages[:-1])


@pytest.mark.unit
async def test_text_404_means_no_xml():
    missing = {"error": True, "message": "No files were found", "status_code": 404}
    with patch(DOWNLOAD, new=AsyncMock(return_value=missing)):
        result = await odp_download_document("13806514", "J3DOI1O0RXEAPX1", format="text")
    assert result["error_code"] == "NO_TEXT_AVAILABLE"
    assert 'format="pdf"' in result["message"]


@pytest.mark.unit
async def test_text_bad_archive_is_reported():
    with patch(DOWNLOAD, new=AsyncMock(return_value=_download_ok(b"<html>oops</html>"))):
        result = await odp_download_document("18402543", "ABC", format="text")
    assert result["error_code"] == "TEXT_EXTRACTION_FAILED"


@pytest.mark.unit
@pytest.mark.parametrize("kwargs", [
    {"format": "docx"},
    {"format": "text", "text_offset": -5},
])
async def test_text_validation(kwargs):
    with patch(DOWNLOAD, new=AsyncMock()) as mock:
        result = await odp_download_document("18402543", "ABC", **kwargs)
    assert result["error_code"] == "VALIDATION_ERROR"
    mock.assert_not_called()
