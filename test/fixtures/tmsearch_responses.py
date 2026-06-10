"""Mock responses for the tmsearch.uspto.gov internal search API.

The live envelope (verified 2026-06-10) is a non-standard Elasticsearch
shape: hits.totalValue (int) and hit "source"/"id" (no underscores).
"""

# Live envelope shape from POST /prod-stage-v1-0-0/tmsearch
MOCK_TMSEARCH_RESPONSE = {
    "took": 12,
    "timedOut": False,
    "shardsTotal": 5,
    "shardsSuccessful": 5,
    "hits": {
        "totalValue": 2,
        "totalRelation": "eq",
        "maxScore": 16.35,
        "hits": [
            {
                "index": "tmsearch-index",
                "type": "_doc",
                "id": "78787878",
                "score": 16.35,
                "source": {
                    "id": "78787878",
                    "wordmark": "TESTMARK",
                    "ownerName": ["Test Trademark Owner LLC (CORPORATION; DELAWARE, USA)"],
                    "ownerFullText": "Test Trademark Owner LLC",
                    "registrationId": "3500027",
                    "internationalClass": ["IC 009"],
                    "alive": True,
                    "markType": "TRADEMARK",
                    "registrationDate": "2008-09-09",
                    "statusCode": "700",
                    "statusDescription": "REGISTERED",
                },
            },
            {
                "index": "tmsearch-index",
                "type": "_doc",
                "id": "87654321",
                "score": 12.01,
                "source": {
                    "id": "87654321",
                    "wordmark": "TESTMARK PRO",
                    "ownerFullText": "Another Owner Inc",
                    "internationalClass": ["IC 009", "IC 042"],
                    "alive": False,
                    "markType": "TRADEMARK",
                    "abandonDate": "2019-03-04",
                },
            },
        ],
    },
}

# Standard ES7 envelope (fallback handling: total object + _source)
MOCK_TMSEARCH_ES7_RESPONSE = {
    "took": 12,
    "hits": {
        "total": {"value": 1, "relation": "eq"},
        "hits": [
            {
                "_id": "78787878",
                "_source": {"id": "78787878", "wordmark": "TESTMARK", "alive": True},
            }
        ],
    },
}

# Older envelope style with total as a plain int
MOCK_TMSEARCH_RESPONSE_INT_TOTAL = {
    "hits": {
        "total": 1,
        "hits": [
            {"_source": {"id": "78787878", "wordmark": "TESTMARK", "alive": True}}
        ],
    }
}

MOCK_TMSEARCH_EMPTY_RESPONSE = {
    "took": 3,
    "hits": {"totalValue": 0, "totalRelation": "eq", "hits": []},
}
