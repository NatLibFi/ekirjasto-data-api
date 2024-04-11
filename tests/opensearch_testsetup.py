from unittest.mock import MagicMock


mock_search_response = {
    "hits": {
        "total": {"value": 3, "relation": "eq"},
        "hits": [
            {
                "_source": {
                    "identifier": "111",
                    "title": "Book 1",
                    "author": "Author 1",
                    "start": "2024-02-01T10:00:00.148927+00:00",
                }
            },
            {
                "_source": {
                    "identifier": "111",
                    "title": "Book 1",
                    "author": "Author 1",
                    "start": "2024-03-01T06:27:16.148927+00:00",
                }
            },
            {
                "_source": {
                    "identifier": "222",
                    "title": "Book 2",
                    "author": "Author 2",
                    "start": "2024-04-01T06:27:16.148927+00:00",
                }
            },
        ],
    }
}

mock_os_client = MagicMock()
mock_os_client.search.return_value = mock_search_response


def override_get_os_client():
    """
    Override for get_opensearch_client function to return the mock client.
    """
    try:
        yield mock_os_client
    finally:
        pass
