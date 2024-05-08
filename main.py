import datetime
from fastapi import FastAPI, Depends, HTTPException, Query, Request, Security
from fastapi.security import APIKeyHeader
from opensearchpy import OpenSearch
from sqlalchemy.orm import Session

from config import settings
from lib.database import (
    get_api_token,
    get_db,
    get_holds_with_edition_data,
    get_reservations_for_identifier,
)
from lib.models import Reservation, TokenData
from lib.opensearch import get_os_client, get_reservation_events

app = FastAPI(
    title="E-kirjasto Data API",
    root_path=settings.ROOT_PATH,
    version="1.0.1",
)


# AUTHENTICATION

api_key_header = APIKeyHeader(name="Token")


def get_token_data(
    db: Session = Depends(get_db), api_key: str = Security(api_key_header)
):
    """
    A dependency function to get token data from the database using the provided API key.
    NOTE: A route gets authenticated when it depends on this function

    Parameters (given by dependencies):
    - db (Session): The database session to query.
    - api_key (str): The API key provided for authentication.

    Returns:
    - The token data associated with the provided API key.
    """
    token_data = get_api_token(db, api_key)
    if not token_data:
        raise HTTPException(status_code=404, detail="Invalid api token")
    return token_data


# ROUTES


@app.get("/")
def read_root(request: Request):
    return {
        "name": app.title,
        "documentation": f"{request.scope.get('root_path')}{app.docs_url}",
    }


@app.get("/active-reservations")
def read_active_reservations(
    db: Session = Depends(get_db), token_data: TokenData = Depends(get_token_data)
) -> list[Reservation]:
    result = get_holds_with_edition_data(db=db, collection_id=token_data.collection_id)
    return result


@app.get("/active-reservations/{id}")
def read_active_reservations_for_license_pool(
    id: str,
    db: Session = Depends(get_db),
    token_data: TokenData = Depends(get_token_data),
) -> Reservation:
    result = get_reservations_for_identifier(
        db=db, identifier=id, collection_id=token_data.collection_id
    )
    return result


@app.get("/reservation-history")
def read_reservation_history(
    os_client: OpenSearch = Depends(get_os_client),
    from_date: datetime.date | None = Query(
        default=None,
        alias="from",
        description="Format: YYYY-MM-DD",
    ),
    to_date: datetime.date | None = Query(
        default=None,
        alias="to",
        description="Format: YYYY-MM-DD",
    ),
    token_data: TokenData = Depends(get_token_data),
) -> list[Reservation]:
    return get_reservation_events(
        os_client=os_client,
        collection_name=token_data.collection_name,
        from_date=from_date,
        to_date=to_date,
    )
