import datetime
from collections import Counter
from fastapi import HTTPException
from opensearchpy import OpenSearch

from config import settings
from lib.models import LibMeta, Reservation, Reservations


def get_opensearch_client():
    use_ssl = settings.OPENSEARCH_URL.startswith("https://")
    return OpenSearch(settings.OPENSEARCH_URL, use_ssl=use_ssl, timeout=20, maxsize=25)


def field(hit, field, default=""):
    return hit.get("_source", {}).get(field, default)


def get_reservation_events(
    collection_name: str,
    page: int,
    size: int,
    from_date: datetime.date | None = None,
    to_date: datetime.date | None = None,
):
    """
    Retrieves reservation events from OpenSearch on a given (or not given) date frame

    Parameters:
    - collection_name: (str): the name of the collection to filter by
        (NOTE: events unfortunately don't have collection ids so we use name here)
    - page (int): the page number to retrieve
    - size (int): the number of items per page
    - from_date (datetime.date, optional): the start date for filtering
    - to_date (datetime.date, optional): the end date for filtering

    Returns:
    - Reservations: List of reservation events
    """

    if not collection_name:
        raise HTTPException(status_code=404, detail="Invalid collection configuration")

    must: list = [
        {"term": {"type": "circulation_manager_hold_place"}},
        {"term": {"collection": collection_name}},
    ]

    if from_date or to_date:
        range = {}
        if from_date:
            range["gte"] = from_date
        if to_date:
            range["lte"] = to_date
        must.append({"range": {"start": range}})

    os_client = get_opensearch_client()
    query = {
        "size": size,
        "from": (page - 1) * size,
        "query": {"bool": {"must": must}},
    }

    result = os_client.search(index=settings.OPENSEARCH_EVENT_INDEX, body=query)
    total = result.get("hits", {}).get("total", {}).get("value", 0)
    hits = result.get("hits", {}).get("hits", [])

    # Extract identifiers from hits and count their occurrences
    identifiers = (field(hit, "identifier") for hit in hits)
    identifier_counts = Counter(identifiers)

    data = [
        Reservation(
            identifier=identifier,
            title=field(hit, "title"),
            author=field(hit, "author"),
            count=identifier_counts[identifier],
        )
        for hit in hits
        for identifier in identifier_counts
        if identifier == field(hit, "identifier")
    ]

    meta = LibMeta(collection=collection_name, page=page, page_size=size, total=total)

    return Reservations(
        meta=meta,
        data=data,
    )
