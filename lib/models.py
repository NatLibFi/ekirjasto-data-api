from pydantic import BaseModel


class Reservation(BaseModel):
    count: int
    identifier: str
    title: str
    author: str


class TokenData(BaseModel):
    id: int
    label: str
    token: str
    collection_id: int
    collection_name: str
