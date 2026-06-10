"""Mock responses for trademark assignment search (ODP and legacy XML)."""

# ODP-style JSON bag
MOCK_TM_ASSIGNMENT_ODP_RESPONSE = {
    "count": 1,
    "trademarkAssignmentDataBag": [
        {
            "reelNumber": "1234",
            "frameNumber": "0567",
            "conveyanceText": "ASSIGNS THE ENTIRE INTEREST",
            "recordedDate": "2015-06-01",
            "assignors": [{"name": "Old Owner Corp"}],
            "assignees": [{"name": "New Owner LLC"}],
            "registrationNumber": "3500027",
        }
    ],
}

# Legacy assignment-api.uspto.gov Solr-style XML
MOCK_TM_ASSIGNMENT_LEGACY_XML = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <lst name="responseHeader">
    <int name="status">0</int>
  </lst>
  <result name="response" numFound="2" start="0">
    <doc>
      <str name="reelNo">1234</str>
      <str name="frameNo">0567</str>
      <str name="conveyanceText">ASSIGNS THE ENTIRE INTEREST</str>
      <date name="recordedDate">2015-06-01T00:00:00Z</date>
      <arr name="assignorName"><str>Old Owner Corp</str></arr>
      <arr name="assigneeName"><str>New Owner LLC</str></arr>
    </doc>
    <doc>
      <str name="reelNo">5678</str>
      <str name="frameNo">0890</str>
      <str name="conveyanceText">SECURITY INTEREST</str>
      <arr name="assignorName"><str>New Owner LLC</str></arr>
      <arr name="assigneeName"><str>Bank of Testing</str></arr>
    </doc>
  </result>
</response>
"""
