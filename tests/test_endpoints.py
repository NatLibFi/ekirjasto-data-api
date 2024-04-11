from fastapi.testclient import TestClient
import unittest

from main import app
from lib.database import (
    get_db,
)
from lib.opensearch import get_os_client
from tests.database_testsetup import override_get_db
from tests.opensearch_testsetup import override_get_os_client


# Patch the get_db and get_os_client functions with test versions
app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_os_client] = override_get_os_client

client = TestClient(app)


class TestAppRoot(unittest.TestCase):
    def test_root(self):
        response = client.get("/")
        assert response.status_code == 200
        assert response.json().get("name") == "E-kirjasto Data API"


class TestActiveReservations(unittest.TestCase):
    def test_active_reservations_unauthorized(self):
        response = client.get("/active-reservations")
        assert response.status_code == 403
        assert response.json().get("detail") == "Not authenticated"

    def test_active_reservations_for_collection1(self):
        """
        Collection 1 has one book with two active reservations
        """
        headers = {"Token": "testtoken1"}
        response = client.get("/active-reservations", headers=headers)

        assert response.status_code == 200

        output = response.json()
        assert len(output) == 1
        assert output[0]["count"] == 2

    def test_active_reservations_for_collection2(self):
        """
        Collection 2 has two books with one active reservation for each of them
        """

        headers = {"Token": "testtoken2"}
        response = client.get("/active-reservations", headers=headers)

        assert response.status_code == 200

        output = response.json()
        assert len(output) == 2
        assert output[0]["count"] == 1
        assert output[1]["count"] == 1

    def test_active_reservations_for_collection3(self):
        """
        Collection 3 has no active reservations
        """
        headers = {"Token": "testtoken3"}
        response = client.get("/active-reservations", headers=headers)

        assert response.status_code == 200

        output = response.json()
        assert len(output) == 0


class TestActiveReservationsForLicensePool(unittest.TestCase):
    def test_active_reservations_for_license_pool_unauthorized(self):
        response = client.get("/active-reservations/123")
        assert response.status_code == 403
        assert response.json().get("detail") == "Not authenticated"


class TestReservationHistory(unittest.TestCase):
    def test_reservation_history_unauthorized(self):
        response = client.get("/reservation-history")
        assert response.status_code == 403
        assert response.json().get("detail") == "Not authenticated"

    def test_get_reservation_history(self):
        headers = {"Token": "testtoken1"}
        response = client.get("/reservation-history", headers=headers)

        assert response.status_code == 200

        output = response.json()
        assert len(output["data"]) == 2
        # First book has two reservations
        assert output["data"][0]["count"] == 2
        # Second book has one reservation
        assert output["data"][1]["count"] == 1
