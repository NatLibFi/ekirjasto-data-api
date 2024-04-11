from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text

from lib.database import (
    ApiToken,
    Base,
    Collection,
    Edition,
    Hold,
    Identifier,
    IntegrationConfiguration,
    LicensePool,
)

TEST_TOKENS = [
    {
        "id": 1,
        "collection_id": 1,
        "label": "test token label",
        "token": "testtoken1",
    },
    {
        "id": 2,
        "collection_id": 2,
        "label": "test token label 2",
        "token": "testtoken2",
    },
    {
        "id": 3,
        "collection_id": 3,
        "label": "test token label 3",
        "token": "testtoken3",
    },
]

TEST_IDENTIFIERS = [
    {
        "id": 1,
        "identifier": "test identifier A",
    },
    {
        "id": 2,
        "identifier": "test identifier B",
    },
    {
        "id": 3,
        "identifier": "test identifier C",
    },
]

TEST_EDITIONS = [
    {
        "id": 1,
        "permanent_work_id": 1,
        "title": "Test book A Collection 1",
        "author": "test author 1",
        "primary_identifier_id": 1,
    },
    {
        "id": 2,
        "permanent_work_id": 2,
        "title": "Test book B Collection 2",
        "author": "test author 2",
        "primary_identifier_id": 2,
    },
    {
        "id": 3,
        "permanent_work_id": 3,
        "title": "Test book C Collection 2",
        "author": "test author 2",  # Same author as book B
        "primary_identifier_id": 3,
    },
]

TEST_INTEGRATION_CONFIGURATIONS = [
    {
        "id": 1,
        "name": "Test Collection Name 1",
    },
    {
        "id": 2,
        "name": "Test Collection Name 2",
    },
    {
        "id": 3,
        "name": "Test Collection Name 3",
    },
]

TEST_COLLECTIONS = [
    {
        "id": 1,
        "integration_configuration_id": 1,
    },
    {
        "id": 2,
        "integration_configuration_id": 2,
    },
    {
        "id": 3,
        "integration_configuration_id": 3,
    },
]

TEST_LICENSE_POOLS = [
    {
        "id": 1,
        "collection_id": 1,
        "presentation_edition_id": 1,
    },
    {
        "id": 2,
        "collection_id": 2,
        "presentation_edition_id": 2,
    },
    {
        "id": 3,
        "collection_id": 2,
        "presentation_edition_id": 3,
    },
]

TEST_HOLDS = [
    {
        "id": 1,
        "license_pool_id": 1,
    },
    {
        "id": 2,
        "license_pool_id": 1,
    },
    {
        "id": 3,
        "license_pool_id": 2,
    },
    {
        "id": 4,
        "license_pool_id": 3,
    },
]

# Create an in-memory SQLite database for testing
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

Base.metadata.create_all(
    bind=engine,
    tables=[
        ApiToken.__table__,
        Identifier.__table__,
        Edition.__table__,
        IntegrationConfiguration.__table__,
        Collection.__table__,
        LicensePool.__table__,
        Hold.__table__,
    ],
)

TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
test_db = TestSessionLocal()

# Populate the SQLite database with test data
for item in TEST_TOKENS:
    clause = text(
        "INSERT INTO apitokens (id, token, label, collection_id) VALUES (:id, :token, :label, :collection_id)"
    ).bindparams(
        id=item["id"],
        token=item["token"],
        label=item["label"],
        collection_id=item["collection_id"],
    )
    test_db.execute(clause)

for items in TEST_IDENTIFIERS:
    clause = text(
        "INSERT INTO identifiers (id, identifier) VALUES (:id, :identifier)"
    ).bindparams(
        id=items["id"],
        identifier=items["identifier"],
    )
    test_db.execute(clause)

for items in TEST_EDITIONS:
    clause = text(
        "INSERT INTO editions (id, permanent_work_id, title, author, primary_identifier_id) VALUES (:id, :permanent_work_id, :title, :author, :primary_identifier_id)"
    ).bindparams(
        id=items["id"],
        permanent_work_id=items["permanent_work_id"],
        title=items["title"],
        author=items["author"],
        primary_identifier_id=items["primary_identifier_id"],
    )
    test_db.execute(clause)

for items in TEST_INTEGRATION_CONFIGURATIONS:
    clause = text(
        "INSERT INTO integration_configurations (id, name) VALUES (:id, :name)"
    ).bindparams(
        id=items["id"],
        name=items["name"],
    )
    test_db.execute(clause)

for items in TEST_COLLECTIONS:
    clause = text(
        "INSERT INTO collections (id, integration_configuration_id) VALUES (:id, :integration_configuration_id)"
    ).bindparams(
        id=items["id"],
        integration_configuration_id=items["integration_configuration_id"],
    )
    test_db.execute(clause)

for items in TEST_LICENSE_POOLS:
    clause = text(
        "INSERT INTO licensepools (id, collection_id, presentation_edition_id) VALUES (:id, :collection_id, :presentation_edition_id)"
    ).bindparams(
        id=items["id"],
        collection_id=items["collection_id"],
        presentation_edition_id=items["presentation_edition_id"],
    )
    test_db.execute(clause)

for items in TEST_HOLDS:
    clause = text(
        "INSERT INTO holds (id, license_pool_id) VALUES (:id, :license_pool_id)"
    ).bindparams(
        id=items["id"],
        license_pool_id=items["license_pool_id"],
    )
    test_db.execute(clause)

test_db.commit()


def override_get_db():
    """
    Override for get_db function to return the SQLite session for testing.
    """
    try:
        yield test_db
    finally:
        test_db.close()
