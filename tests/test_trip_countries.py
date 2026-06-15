import unittest
from datetime import date
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
        return self.fetchone_results.pop(0) if self.fetchone_results else None

    def fetchall(self):
        return self.fetchall_results.pop(0) if self.fetchall_results else []


class FakeConnection:
    def __init__(self, cursor):
        self.test_cursor = cursor
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self, *args, **kwargs):
        return self.test_cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


class TripCountryRoutesTest(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.trip = {
            "trip_id": 7,
            "trip_name": "Summer Trip",
            "trip_memo": "First memo",
            "in_date": date(2026, 6, 1),
            "out_date": date(2026, 6, 10),
            "stayed_day": 9,
        }

    def test_detail_shows_trip_and_joined_country_list(self):
        cursor = FakeCursor(
            fetchone_results=[self.trip],
            fetchall_results=[
                [{"country_id": 3, "country_name": "Korea"}],
                [
                    {
                        "trip_country_id": 11,
                        "country_id": 3,
                        "country_name": "Korea",
                        "in_date": date(2026, 6, 1),
                        "out_date": date(2026, 6, 5),
                        "stayed_day": 4,
                    }
                ],
            ],
        )
        connection = FakeConnection(cursor)

        with patch("app.get_connection", return_value=connection):
            response = self.client.get("/trips/7")

        query, params = cursor.executions[2]
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Summer Trip", response.data)
        self.assertIn(b"First memo", response.data)
        self.assertIn(b"Korea", response.data)
        self.assertIn("FROM trip_country_list tc", query)
        self.assertIn("INNER JOIN country_list c", query)
        self.assertEqual(params, (7,))

    def test_detail_adds_country_and_calculates_stayed_day(self):
        cursor = FakeCursor(fetchone_results=[self.trip, {"country_id": 3}])
        connection = FakeConnection(cursor)

        with patch("app.get_connection", return_value=connection):
            response = self.client.post(
                "/trips/7",
                data={
                    "action": "add",
                    "country_id": "3",
                    "in_date": "2026-06-01",
                    "out_date": "2026-06-05",
                },
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/trips/7")
        self.assertEqual(
            cursor.executions[2][1],
            (7, 3, date(2026, 6, 1), date(2026, 6, 5), 4),
        )
        self.assertTrue(connection.committed)

    def test_detail_edits_country_and_recalculates_stayed_day(self):
        cursor = FakeCursor(
            fetchone_results=[
                self.trip,
                {"trip_country_id": 11},
                {"country_id": 4},
            ]
        )
        connection = FakeConnection(cursor)

        with patch("app.get_connection", return_value=connection):
            response = self.client.post(
                "/trips/7",
                data={
                    "action": "edit",
                    "trip_country_id": "11",
                    "country_id": "4",
                    "in_date": "2026-07-10",
                    "out_date": "2026-07-13",
                },
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/trips/7")
        self.assertEqual(
            cursor.executions[3][1],
            (4, date(2026, 7, 10), date(2026, 7, 13), 3, 11, 7),
        )
        self.assertTrue(connection.committed)

    def test_detail_rejects_reversed_country_dates(self):
        cursor = FakeCursor(
            fetchone_results=[self.trip],
            fetchall_results=[[], []],
        )
        connection = FakeConnection(cursor)

        with patch("app.get_connection", return_value=connection):
            response = self.client.post(
                "/trips/7",
                data={
                    "action": "add",
                    "country_id": "3",
                    "in_date": "2026-06-05",
                    "out_date": "2026-06-01",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"In date cannot be later than out date.", response.data)
        self.assertFalse(connection.committed)

    def test_independent_trip_country_menu_is_removed(self):
        response = self.client.get("/trip-countries")

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
