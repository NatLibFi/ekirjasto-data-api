from fastapi import HTTPException
from sqlalchemy import create_engine, ForeignKey, String, func
from sqlalchemy.orm import (
    sessionmaker,
    relationship,
    Mapped,
    mapped_column,
    Session,
    declarative_base,
)

from config import settings
from lib.models import Reservation

engine = create_engine(
    settings.POSTGRES_URL, execution_options={"postgresql_readonly": True}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    A dependency function that yields a database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# DATABASE MODELS


class Identifier(Base):
    __tablename__ = "identifiers"

    id: Mapped[int] = mapped_column(primary_key=True)
    identifier: Mapped[str] = mapped_column(String)


class Edition(Base):
    __tablename__ = "editions"

    id: Mapped[int] = mapped_column(primary_key=True)
    permanent_work_id: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    author: Mapped[str] = mapped_column(String)
    primary_identifier_id: Mapped[int] = mapped_column(ForeignKey("identifiers.id"))


class IntegrationConfiguration(Base):
    __tablename__ = "integration_configurations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(primary_key=True)
    integration_configuration_id: Mapped[int] = mapped_column(
        ForeignKey("integration_configurations.id")
    )
    integration_configuration: Mapped["IntegrationConfiguration"] = relationship()


class LicensePool(Base):
    __tablename__ = "licensepools"

    id: Mapped[int] = mapped_column(primary_key=True)
    presentation_edition_id: Mapped[int] = mapped_column(ForeignKey("editions.id"))
    presentation: Mapped["Edition"] = relationship()
    collection_id: Mapped[int] = mapped_column(ForeignKey("collections.id"))
    collection: Mapped["Collection"] = relationship()


class Hold(Base):
    __tablename__ = "holds"

    id: Mapped[int] = mapped_column(primary_key=True)
    license_pool_id: Mapped[int] = mapped_column(ForeignKey("licensepools.id"))
    license_pool: Mapped["LicensePool"] = relationship()


class ApiToken(Base):
    __tablename__ = "apitokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String)
    label: Mapped[str] = mapped_column(String)
    collection_id: Mapped[int] = mapped_column(ForeignKey("collections.id"))
    collection: Mapped["Collection"] = relationship()


# QUERIES


def get_api_token(db: Session, token):
    """
    A function to retrieve an API token data from the database based on the provided token string.
    Used for authenticating and retrieving the associated collection

    Parameters:
    - db (Session): The database session object.
    - token (str): The token string to search for in the database.

    Returns:
    - tuple containing the ApiToken label, and associated collection_id and collection_name.
    """
    query = (
        db.query(
            ApiToken.label,
            ApiToken.collection_id,
            IntegrationConfiguration.name.label("collection_name"),
        )
        .join(Collection, ApiToken.collection_id == Collection.id)
        .join(
            IntegrationConfiguration,
            Collection.integration_configuration_id == IntegrationConfiguration.id,
        )
        .filter(ApiToken.token == token)
    )
    result = query.first()
    return result


def get_holds_with_edition_data(db: Session, collection_id: int):
    """
    Get active reservation counts with edition data for whole collection from the database

    Parameters:
    - db (Session): The database session object.
    - token (str): The token string to search for in the database.
    - collection_id (int): The ID of the collection.

    Returns:
    - list of objects with active hold count and edition data.
    """
    if not collection_id:
        raise HTTPException(status_code=404, detail="Invalid collection configuration")

    query = (
        db.query(
            func.count(Hold.id).label("active_holds"),
            Identifier.identifier,
            Edition.title,
            Edition.author,
        )
        .join(LicensePool, Hold.license_pool_id == LicensePool.id)
        .join(Edition, LicensePool.presentation_edition_id == Edition.id)
        .join(Identifier, Edition.primary_identifier_id == Identifier.id)
        .filter(LicensePool.collection_id == collection_id)
        .group_by(Identifier.identifier, Edition.title, Edition.author)
        .order_by(Identifier.identifier)
    )

    results = query.all()

    holds_with_edition_data = [
        Reservation(
            count=active_holds,
            identifier=identifier,
            title=title,
            author=author,
        )
        for active_holds, identifier, title, author in results
    ]

    return holds_with_edition_data


def get_reservations_for_identifier(db: Session, identifier: str, collection_id: int):
    """
    Get active reservation count with edition data for a given identifier and collection from the database

    Parameters:
    - db: Session object for the database
    - identifier: work's identifier (like ISBN)
    - collection_id: An integer representing the collection id

    Returns:
    - an object with active hold count and edition data.
    """
    if not collection_id:
        raise HTTPException(status_code=404, detail="Invalid collection configuration")

    query = (
        db.query(
            func.count(Hold.id).label("active_holds"),
            Identifier.identifier,
            Edition.title,
            Edition.author,
        )
        .join(LicensePool, Hold.license_pool_id == LicensePool.id)
        .join(Edition, LicensePool.presentation_edition_id == Edition.id)
        .join(Identifier, Edition.primary_identifier_id == Identifier.id)
        .filter(Identifier.identifier == identifier)
        .filter(LicensePool.collection_id == collection_id)
        .group_by(Identifier.identifier, Edition.title, Edition.author)
    )

    result = query.first()

    if not result:
        raise HTTPException(
            status_code=404, detail=f"No active holds for Identifier {identifier}"
        )

    return Reservation(
        count=result.active_holds,
        identifier=result.identifier,
        title=result.title,
        author=result.author,
    )
