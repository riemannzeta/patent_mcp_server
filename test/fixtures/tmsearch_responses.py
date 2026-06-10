"""Mock responses for the tmsearch.uspto.gov internal search API."""

# Elasticsearch-style (ES7) envelope with total as an object
MOCK_TMSEARCH_RESPONSE = {
    "took": 12,
    "hits": {
        "total": {"value": 2, "relation": "eq"},
        "hits": [
            {
                "_id": "78787878",
                "_source": {
                    "id": "78787878",
                    "wordmark": "TESTMARK",
                    "ownerFullText": "Test Trademark Owner LLC",
                    "registrationId": "3500027",
                    "internationalClasses": ["009"],
                    "alive": True,
                    "markType": "TRADEMARK",
                    "registrationDate": "2008-09-09",
                },
            },
            {
                "_id": "87654321",
                "_source": {
                    "id": "87654321",
                    "wordmark": "TESTMARK PRO",
                    "ownerFullText": "Another Owner Inc",
                    "internationalClasses": ["009", "042"],
                    "alive": False,
                    "markType": "TRADEMARK",
                    "abandonDate": "2019-03-04",
                },
            },
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
    "hits": {"total": {"value": 0, "relation": "eq"}, "hits": []},
}
