"""Mock responses for trademark assignment search (USPTO Assignment Center).

Shape captured live from
POST https://assignmentcenter.uspto.gov/ipas/search/api/v2/public/trademark/exportTradeMarkData
on 2026-06-10.
"""

# The API returns a list with one element: {"searchCriteria": [...], "data": [...]}
MOCK_TM_ASSIGNMENT_RESPONSE = [
    {
        "searchCriteria": [
            {"property": "New Owner LLC", "searchBy": "assigneeName"},
            {"property": "25", "searchBy": "rowsNeeded"},
        ],
        "data": [
            {
                "reelNumber": 1234,
                "frameNumber": "0567",
                "assignorExecutionDate": "06/01/2015",
                "correspondentName": "EXAMPLE LAW LLP",
                "domesticRepresentative": None,
                "assignors": [
                    {"name": "Old Owner Corp", "executionDate": "06/01/2015"}
                ],
                "assignees": ["New Owner LLC"],
                "noOfProperties": 1,
                "properties": [
                    {
                        "serialNumber": "78787878",
                        "registrationNumber": "3500027",
                        "markName": "EXAMPLE MARK",
                    }
                ],
            },
            {
                "reelNumber": 5678,
                "frameNumber": "0890",
                "assignorExecutionDate": "03/15/2020",
                "correspondentName": "EXAMPLE LAW LLP",
                "domesticRepresentative": None,
                "assignors": [
                    {"name": "New Owner LLC", "executionDate": "03/15/2020"}
                ],
                "assignees": ["Bank of Testing"],
                "noOfProperties": 1,
                "properties": [
                    {
                        "serialNumber": "78787878",
                        "registrationNumber": "3500027",
                        "markName": "EXAMPLE MARK",
                    }
                ],
            },
        ],
    }
]

MOCK_TM_ASSIGNMENT_EMPTY_RESPONSE = [
    {
        "searchCriteria": [
            {"property": "Nonexistent Co", "searchBy": "assigneeName"},
            {"property": "25", "searchBy": "rowsNeeded"},
        ],
        "data": [],
    }
]
