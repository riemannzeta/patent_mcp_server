"""
Plain text from ODP file-wrapper XML archives.

ODP serves a document's XML at
``/api/v1/download/applications/{app}/{documentIdentifier}/xmlarchive``
as a tar holding one XML file (and, for applicant papers, an ``_svg.zip``
of page images). Verified live 2026-10-14 on CTNF, CTFR, NOA, REM, CLM,
IDS, PET.PCT and PETDEC papers from 2011 to 2026, which use four schemas:

- ST96 ``OutgoingDocument`` (USPTO papers: office actions, notices,
  petition decisions): ``uscom:P`` paragraphs, page headers in
  ``uscom:BoundaryDataBag``.
- ST96 ``IncomingDocument`` / ``ClaimsDocument`` (applicant papers since
  ~2018): ``uscom:P``, ``uspat:ClaimText``, ``com:Ins``/``com:Del`` for
  claim amendments, ``uscom:OCRConfidenceData`` wrapping low-confidence
  OCR characters inline.
- The older ``pat:`` IncomingDocument (2016): ``pat:P``, ``pat:Heading``.
- Red-book style ``us-patent-application`` claims (2012): ``claim-text``.

Rather than one parser per schema, the extractor works on local tag names:
a few block names start paragraphs, a few container names hold metadata
or page furniture and are skipped, and everything else is inline text.
"""

import io
import re
import tarfile
import xml.etree.ElementTree as ET
from typing import List, Optional, Tuple

# Local names (lower case, hyphens removed) that start a new paragraph.
_BLOCKS = frozenset({"p", "heading", "claim", "claimtext", "tablerow", "li"})
# Table cells are separated within their row.
_CELLS = frozenset({"tabledatacell", "tableheadercell", "entry"})
# Metadata, page headers and footers, images and form-paragraph codes:
# nothing a reader of the paper's body needs.
_SKIP = frozenset({
    "documentmetadata", "documentheaderdetails", "documentcode",
    "mailroomdate", "boundarydatabag", "boundarydata", "headertext",
    "image", "patentimage", "formparagraphnumber", "formparagraphcategory",
    "relatedformparagraph", "claimnumber", "claimstatuscategory",
    "usbibliographicdataapplication", "formpageheader", "formpagefooter",
})

DEL_OPEN, DEL_CLOSE = "~~", "~~"
INS_OPEN, INS_CLOSE = "++", "++"

_SPACES = re.compile(r"[ \t\r\n\u00a0]+")
_INTERNAL_SUBSET = re.compile(rb"<!DOCTYPE[^>\[]*\[")

# XML archives are a few hundred KB at most; anything far larger is not
# a single paper's text.
MAX_XML_BYTES = 20_000_000


class DocumentTextError(ValueError):
    """The archive or its XML could not be turned into text."""


def _local(tag) -> str:
    if not isinstance(tag, str):  # comments and processing instructions
        return ""
    return tag.rsplit("}", 1)[-1].replace("-", "").lower()


class _Collector:
    def __init__(self):
        self.paragraphs: List[List[Tuple[str, Optional[str]]]] = []
        self.current: List[Tuple[str, Optional[str]]] = []
        self.cell_index = 0

    def flush(self):
        if self.current:
            self.paragraphs.append(self.current)
        self.current = []

    def add(self, text: Optional[str], mark: Optional[str]):
        if text:
            self.current.append((text, mark))

    def walk(self, el: ET.Element, mark: Optional[str]):
        name = _local(el.tag)
        if name in _SKIP:
            return
        if name == "del":
            mark = "del"
        elif name == "ins":
            mark = "ins"
        block = name in _BLOCKS
        if block:
            self.flush()
        if name == "tablerow":
            self.cell_index = 0
        if name in _CELLS:
            if self.cell_index:
                self.add(" | ", None)
            self.cell_index += 1
        if isinstance(el.tag, str):
            self.add(el.text, mark)
        for child in el:
            self.walk(child, mark)
            self.add(child.tail, mark)
        if block:
            self.flush()


def _render(segments: List[Tuple[str, Optional[str]]]) -> str:
    # Merge neighbors with the same mark first: OCR confidence wrappers
    # split one inserted phrase into several <Ins> runs.
    merged: List[List] = []
    for text, mark in segments:
        if merged and merged[-1][1] == mark:
            merged[-1][0] += text
        else:
            merged.append([text, mark])

    out = []
    for text, mark in merged:
        text = _SPACES.sub(" ", text)
        if mark is None:
            out.append(text)
            continue
        core = text.strip()
        if not core:
            out.append(text)
            continue
        opener, closer = (DEL_OPEN, DEL_CLOSE) if mark == "del" else (INS_OPEN, INS_CLOSE)
        # Keep surrounding spaces outside the markers.
        lead = " " if text[:1] == " " else ""
        trail = " " if text[-1:] == " " else ""
        out.append(f"{lead}{opener}{core}{closer}{trail}")
    return _SPACES.sub(" ", "".join(out)).strip()


def xml_to_text(xml_bytes: bytes) -> str:
    """Body text of one file-wrapper XML paper, paragraphs separated by
    blank lines. Claim deletions come out as ~~text~~ and insertions as
    ++text++.

    Raises:
        DocumentTextError: If the XML is malformed or declares a DTD
    """
    # Older claim papers name an external DTD (<!DOCTYPE us-patent-application
    # SYSTEM "PATI-v1.0.3-2011-06-23.dtd">), which expat does not fetch.
    # Entity declarations are another matter: refusing them rules out
    # entity-expansion attacks without a dependency on defusedxml.
    if b"<!ENTITY" in xml_bytes or _INTERNAL_SUBSET.search(xml_bytes[:4096]):
        raise DocumentTextError("XML declares entities; refusing to parse it")
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        raise DocumentTextError(f"XML could not be parsed: {e}") from e

    collector = _Collector()
    collector.walk(root, None)
    collector.flush()
    paragraphs = (_render(p) for p in collector.paragraphs)
    return "\n\n".join(p for p in paragraphs if p)


def xml_from_archive(archive: bytes) -> Tuple[str, bytes]:
    """The XML member of an ODP xmlarchive tar, as (name, bytes).

    Raises:
        DocumentTextError: If the archive is not a tar or holds no XML file
    """
    try:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:*") as tar:
            for member in tar.getmembers():
                if not member.isfile() or not member.name.lower().endswith(".xml"):
                    continue
                if member.size > MAX_XML_BYTES:
                    raise DocumentTextError(f"XML member is {member.size:,} bytes; too large")
                handle = tar.extractfile(member)
                if handle is None:
                    continue
                return member.name.rsplit("/", 1)[-1], handle.read()
    except tarfile.TarError as e:
        raise DocumentTextError(f"Download is not a tar archive: {e}") from e
    raise DocumentTextError("Archive holds no XML file")
