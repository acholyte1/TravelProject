import unittest
from unittest.mock import patch

from app import app


class FakeCursor:
    def __init__(self, fetchall_result=None):
        self.fetchall_result = fetchall_result or []
        self.executions = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, query, params=None):
        self.executions.append((" ".join(query.split()), params))

    def fetchall(self):
        return self.fetchall_result


class FakeConnection:
    def __init__(self, cursor):
        self.test_cursor = cursor
        self.closed = False

    def cursor(self, *args, **kwargs):
        return self.test_cursor

    def close(self):
        self.closed = True


class TravelSearchRoutesTest(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_travel_page_loads(self):
        response = self.client.get("/travel")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"/api/travel/search", response.data)

    def test_travel_search_returns_unified_items(self):
        cursor = FakeCursor(
            fetchall_result=[
                {
                    "id": 1,
                    "kind": "country",
                    "name": "Germany",
                    "country_name": "Germany",
                    "region_name": "Europe",
                    "visit_status": "TRIP",
                    "visit_count": 3,
                }
            ]
        )
        connection = FakeConnection(cursor)

        with patch("app.get_connection", return_value=connection):
            response = self.client.get(
                "/api/travel/search?q=Ger&kind=country&status=TRIP"
                "&sort=visit_count&direction=desc"
            )

        query, params = cursor.executions[0]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["total"], 1)
        self.assertIn("UNION ALL", query)
        self.assertIn("location_name_en LIKE %s", query)
        self.assertIn("COALESCE(NULLIF(l.location_name_ko, ''), l.location_name)", query)
        self.assertIn("country_name_en LIKE %s", query)
        self.assertIn("COALESCE(NULLIF(c.country_name_ko, ''), c.country_name)", query)
        self.assertIn("kind = %s", query)
        self.assertIn("visit_status = %s", query)
        self.assertIn("ORDER BY visit_count DESC", query)
        self.assertEqual(
            params, ["%Ger%", "%Ger%", "%Ger%", "%Ger%", "country", "TRIP"]
        )
        self.assertTrue(connection.closed)


if __name__ == "__main__":
    unittest.main()
