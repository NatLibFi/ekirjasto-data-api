import datetime
from fastapi import HTTPException
from opensearchpy import OpenSearch

from config import settings
from lib.models import Reservation


use_ssl = settings.OPENSEARCH_URL.startswith("https://")


def get_os_client():
    """
    A dependency function that yields an OpenSearch client.
    """
    os_client = OpenSearch(
        settings.OPENSEARCH_URL, use_ssl=use_ssl, timeout=20, maxsize=25
    )
    try:
        yield os_client
    finally:
        os_client.close()


def field(hit, field, default=""):
    return hit.get("_source", {}).get(field, default)


def get_reservation_events(
    os_client: OpenSearch,
    collection_name: str,
    from_date: datetime.date | None = None,
    to_date: datetime.date | None = None,
):
    """
    Retrieves reservation events from OpenSearch on a given (or not given) date frame

    Parameters:
    - os_client: OpenSearch client
    - collection_name: (str): the name of the collection to filter by
        (NOTE: events unfortunately don't have collection ids so we use name here)
    - from_date (datetime.date, optional): the start date for filtering
    - to_date (datetime.date, optional): the end date for filtering

    Returns:
    - Reservations: List of reservation events
    """

    if not collection_name:
        raise HTTPException(status_code=404, detail="Invalid collection configuration")

    # 1) Fetch identifier counts from hold events as aggregations

    event_must: list = [
        {"term": {"type": "circulation_manager_hold_place"}},
        {"term": {"collection": collection_name}},
    ]

    if from_date or to_date:
        range = {}
        if from_date:
            range["gte"] = from_date
        if to_date:
            range["lte"] = to_date
        event_must.append({"range": {"start": range}})

    event_query = {
        "size": 0,
        "query": {"bool": {"must": event_must}},
        "aggs": {"identifier": {"terms": {"field": "identifier", "size": 1000000}}},
    }

    event_result = os_client.search(
        index=settings.OPENSEARCH_EVENT_INDEX, body=event_query
    )

    identifier_buckets = event_result["aggregations"]["identifier"]["buckets"]
    identifiers = [bucket["key"] for bucket in identifier_buckets]

    # 2) Fetch work data for each identifier from works index

    source_fields = [
        "identifiers",
        "title",
        "author",
    ]
    BATCH_SIZE = 10000
    works_map = {}

    while len(identifiers) > 0:
        identifiers_to_fetch = identifiers[:BATCH_SIZE]
        identifiers = identifiers[BATCH_SIZE:]
        work_query = {
            "size": BATCH_SIZE,
            "_source": source_fields,
            "query": {
                "nested": {
                    "path": "identifiers",
                    "query": {
                        "terms": {"identifiers.identifier": identifiers_to_fetch}
                    },
                }
            },
        }
        work_result = os_client.search(
            index=settings.OPENSEARCH_WORK_INDEX, body=work_query
        )

        for hit in work_result.get("hits", {}).get("hits", []):
            for identifier in hit.get("_source", {}).get("identifiers", []):
                works_map[identifier["identifier"]] = hit["_source"]

    # 3) Combine identifier counts with work data

    def make_reservation_info(bucket):
        work = works_map.get(bucket.get("key"), {})
        return Reservation(
            identifier=bucket.get("key"),
            title=work.get("title", ""),
            author=work.get("author", ""),
            count=bucket.get("doc_count"),
        )

    data = [make_reservation_info(bucket) for bucket in identifier_buckets]

    return data
