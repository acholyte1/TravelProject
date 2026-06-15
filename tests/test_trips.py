import unittest
from datetime import date
from unittest.mock import patch

from app import app


class FakeCursor:
    def __init__(self, fetchone_result=None, fetchall_result=None):
        self.fetchone_result = fetchone_result
        self.fetchall_result = fetchall_result or []
        self.executions = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, query, params=None):
        self.executions.append((" ".join(query.split()), params))

    def fetchone(self):
        return self.fetchone_result

    def fetchall(self):
        return self.fetchall_result


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


class TripRoutesTest(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_add_trip_calculates_stayed_day(self):
        cursor = FakeCursor()
        connection = FakeConnection(cursor)

        with patch("app.get_connection", return_value=connection):
            response = self.client.post(
                "/trips/add",
                data={
                    "trip_name": "Summer Trip",
                    "trip_memo": "First memo",
                    "in_date": "2026-06-01",
                    "out_date": "2026-06-05",
                },
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/trips")
        self.assertEqual(
            cursor.executions[0][1],
            (
                "Summer Trip",
                "First memo",
                date(2026, 6, 1),
                date(2026, 6, 5),
                4,
            ),
        )
        self.assertTrue(connection.committed)

    def test_add_trip_rejects_reversed_dates(self):
        with patch("app.get_connection") as get_connection:
            response = self.client.post(
                "/trips/add",
                data={
                    "trip_name": "Summer Trip",
                    "in_date": "2026-06-05",
                    "out_date": "2026-06-01",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"In date cannot be later than out date.", response.data)
        get_connection.assert_not_called()

    def test_trip_list_filters_deleted_rows_and_overlapping_period(self):
        cursor = FakeCursor(fetchall_result=[])
        connection = FakeConnection(cursor)

        with patch("app.get_connection", return_value=connection):
            response = self.client.get(
                "/trips?period_start=2026-06-01&period_end=2026-06-30"
                "&sort=stayed_day&direction=asc"
            )

        query, params = cursor.executions[0]
        self.assertEqual(response.status_code, 200)
        self.assertIn("WHERE is_deleted = 0", query)
        self.assertIn("out_date >= %s", query)
        self.assertIn("in_date <= %s", query)
        self.assertIn("ORDER BY stayed_day ASC", query)
        self.assertEqual(params, [date(2026, 6, 1), date(2026, 6, 30)])

    def test_edit_trip_recalculates_stayed_day(self):
        cursor = FakeCursor(
            fetchone_result={
                "trip_id": 7,
                "trip_name": "Old Name",
                "trip_memo": None,
                "in_date": date(2026, 6, 1),
                "out_date": date(2026, 6, 5),
                "stayed_day": 4,
            }
        )
        connection = FakeConnection(cursor)

        with patch("app.get_connection", return_value=connection):
            response = self.client.post(
                "/trips/7/edit",
                data={
                    "trip_name": "New Name",
                    "trip_memo": "Updated memo",
                    "in_date": "2026-07-10",
                    "out_date": "2026-07-13",
                },
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            cursor.executions[1][1],
            (
                "New Name",
                "Updated memo",
                date(2026, 7, 10),
                date(2026, 7, 13),
                3,
                7,
            ),
        )
        self.assertTrue(connection.committed)

    def test_delete_trip_is_soft_delete(self):
        cursor = FakeCursor()
        connection = FakeConnection(cursor)

        with patch("app.get_connection", return_value=connection):
            response = self.client.post("/trips/9/delete")

        query, params = cursor.executions[0]
        self.assertEqual(response.status_code, 302)
        self.assertIn("SET is_deleted = 1", query)
        self.assertEqual(params, (9,))
        self.assertTrue(connection.committed)


if __name__ == "__main__":
    unittest.main()
