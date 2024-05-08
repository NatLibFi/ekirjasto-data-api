from unittest.mock import MagicMock
from config import settings

mock_event_response = {
    "hits": {"total": {"value": 7, "relation": "eq"}, "hits": []},
    "aggregations": {
        "identifier": {
            "doc_count_error_upper_bound": 0,
            "sum_other_doc_count": 0,
            "buckets": [
                {
                    "key": "111",
                    "doc_count": 3,
                },
                {
                    "key": "222",
                    "doc_count": 2,
                },
                {
                    "key": "333",
                    "doc_count": 1,
                },
            ],
        }
    },
}


mock_works_response = {
    "hits": {
        "total": {"value": 3, "relation": "eq"},
        "hits": [
            {
                "_source": {
                    "identifiers": [
                        {
                            "type": "ISBN",
                            "identifier": "111",
                        }
                    ],
                    "title": "Book 1",
                    "author": "Author 1",
                }
            },
            {
                "_source": {
                    "identifiers": [
                        {
                            "type": "ISBN",
                            "identifier": "222",
                        }
                    ],
                    "title": "Book 2",
                    "author": "Author 2",
                }
            },
            {
                "_source": {
                    "identifiers": [
                        {
                            "type": "ISBN",
                            "identifier": "333",
                        }
                    ],
                    "title": "Book 3",
                    "author": "Author 2",
                }
            },
        ],
    }
}


def mock_search_side_effect(*args, **kwargs):
    if kwargs["index"] == settings.OPENSEARCH_EVENT_INDEX:
        return mock_event_response
    elif kwargs["index"] == settings.OPENSEARCH_WORK_INDEX:
        return mock_works_response
    else:
        raise ValueError("Unexpected index")


# Create and configure the mock
mock_os_client = MagicMock()
mock_os_client.search.side_effect = mock_search_side_effect


def override_get_os_client():
    """
    Override for get_opensearch_client function to return the mock client.
    """
    try:
        yield mock_os_client
    finally:
        pass
