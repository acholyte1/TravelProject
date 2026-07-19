import unittest
from unittest.mock import patch

from app import app


class FakeCursor:
    def __init__(self, fetchone_results=None, fetchall_results=None):
        self.fetchone_results = list(fetchone_results or [])
        self.fetchall_results = list(fetchall_results or [])
        self.executions = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, query, params=None):
        self.executions.append((" ".join(query.split()), params))

    def fetchone(self):
        return self.fetchone_results.pop(0)

    def fetchall(self):
        return self.fetchall_results.pop(0)


class FakeConnection:
    def __init__(self, cursor):
        self.test_cursor = cursor
        self.committed = False
        self.closed = False

    def cursor(self, *args, **kwargs):
        return self.test_cursor

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


class LocationRoutesTest(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_location_list_searches_both_names_and_displays_fallback_name(self):
        cursor = FakeCursor(
            fetchall_results=[
                [],
                [],
                [{"location_id": 1, "location_name": "서울"}],
            ]
        )
        connection = FakeConnection(cursor)

        with patch("app.get_connection", return_value=connection):
            response = self.client.get("/locations?location_name=Seoul")

        query, params = cursor.executions[2]
        self.assertEqual(response.status_code, 200)
        self.assertIn("c.location_name LIKE %s OR c.location_name_ko LIKE %s", query)
        self.assertIn(
            "COALESCE(NULLIF(c.location_name_ko, ''), c.location_name) AS location_name",
            query,
        )
        self.assertEqual(params, ["%Seoul%", "%Seoul%"])
        self.assertIn("서울".encode(), response.data)

    def test_add_location_saves_optional_korean_name(self):
        cursor = FakeCursor(fetchone_results=[{"country_id": 1}])
        connection = FakeConnection(cursor)

        with patch("app.get_connection", return_value=connection):
            response = self.client.post(
                "/locations/add",
                data={
                    "country_id": "1",
                    "location_name": "Seoul",
                    "location_name_ko": "서울",
                    "visit_status": "TRIP",
                    "visit_count": "2",
                    "region_id": "1",
                },
            )

        query, params = cursor.executions[1]
        self.assertEqual(response.status_code, 302)
        self.assertIn("location_name_ko", query)
        self.assertEqual(params, (1, "Seoul", "서울", "TRIP", 2, "1"))
        self.assertTrue(connection.committed)

    def test_edit_location_loads_and_updates_korean_name(self):
        location = {
            "location_id": 1,
            "country_id": 1,
            "location_name": "Seoul",
            "location_name_ko": "서울",
            "visit_status": "TRIP",
            "visit_count": 2,
            "region_id": 1,
        }
        cursor = FakeCursor(fetchone_results=[location, {"country_id": 1}])
        connection = FakeConnection(cursor)

        with patch("app.get_connection", return_value=connection):
            response = self.client.post(
                "/locations/1/edit",
                data={
                    "country_id": "1",
                    "location_name": "Busan",
                    "location_name_ko": "부산",
                    "visit_status": "STAY",
                    "visit_count": "3",
                    "region_id": "1",
                },
            )

        select_query, _ = cursor.executions[0]
        update_query, params = cursor.executions[2]
        self.assertEqual(response.status_code, 302)
        self.assertIn("location_name_ko", select_query)
        self.assertIn("location_name_ko = %s", update_query)
        self.assertEqual(params, (1, "Busan", "부산", "STAY", 3, "1", 1))
        self.assertTrue(connection.committed)


if __name__ == "__main__":
    unittest.main()
