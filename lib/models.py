from pydantic import BaseModel


class LibMeta(BaseModel):
    collection: str
    page: int
    page_size: int
    total: int


class Reservation(BaseModel):
    count: int
    identifier: str
    title: str
    author: str


class Reservations(BaseModel):
    meta: LibMeta
    data: list[Reservation]


class TokenData(BaseModel):
    id: int
    label: str
    token: str
    collection_id: int
    collection_name: str
