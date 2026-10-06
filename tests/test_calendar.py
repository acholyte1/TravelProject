import unittest
from datetime import date
from unittest.mock import patch
from app import app
from calendar_view import build_month


def trip(start, end, ident=1):
    return dict(trip_id=ident, trip_name='여행 <test>', trip_memo='', in_date=start, out_date=end)


class CalendarTests(unittest.TestCase):
    def test_life_record_is_excluded_from_calendar_only(self):
        life = trip(date(1988, 9, 26), date(2026, 10, 6))
        life["trip_name"] = "인생"
        holiday = trip(date(2024, 10, 1), date(2024, 10, 2), 2)
        days, missing = build_month([life, holiday], [], [], 10)
        self.assertEqual([entry["trip_id"] for entry in days[1]], [2])
        self.assertFalse(days[3])
        self.assertEqual(missing, 0)
        self.assertEqual(life["trip_name"], "인생")

    def test_new_year_and_multiple_years(self):
        rows = [trip(date(2023,12,30),date(2024,1,2)),trip(date(2025,1,1),date(2025,1,1),2)]
        days, _ = build_month(rows, [], [], 1)
        self.assertEqual([e['actual_date'].year for e in days[1]], [2025,2024])
        self.assertEqual(len(days[2]),1)
        self.assertFalse(days[3])
        self.assertEqual(len(build_month(rows,[],[],12)[0][31]),1)

    def test_leap_day_and_missing_dates(self):
        rows=[trip(date(2024,2,28),date(2024,3,1)),trip(date(2023,2,28),date(2023,3,1),2),trip(None,None,3),trip(date(2024,3,1),date(2024,2,1),4)]
        days, missing=build_month(rows,[],[],2)
        self.assertEqual(len(days[28]),2)
        self.assertEqual(len(days[29]),1)
        self.assertEqual(missing,2)

    def test_place_dates_are_not_inferred(self):
        rows=[trip(date(2024,1,1),date(2024,1,3))]
        countries=[dict(trip_id=1,in_date=date(2024,1,2),out_date=date(2024,1,3),name='한국')]
        locations=[dict(trip_id=1,location_in=None,location_out=None,name='서울')]
        days,_=build_month(rows,countries,locations,1)
        self.assertFalse(days[1][0]['countries'])
        self.assertEqual(days[2][0]['countries'][0]['name'],'한국')
        self.assertFalse(days[2][0]['locations'])

    def test_route_and_validation(self):
        from unittest.mock import MagicMock
        connection=MagicMock()
        cursor=connection.cursor.return_value.__enter__.return_value
        cursor.fetchall.side_effect=[[trip(date(2024,2,29),date(2024,2,29))],[],[]]
        with patch('app.get_connection',return_value=connection):
            response=app.test_client().get('/calendar?month=2&day=29')
        self.assertEqual(response.status_code,200)
        self.assertIn('여행 &lt;test&gt;',response.text)
        connection.close.assert_called_once()
        for query in ['month=0','month=13','month=x','month=2&day=30','month=1&day=x']:
            self.assertEqual(app.test_client().get('/calendar?'+query).status_code,400)

    def test_database_error_is_not_empty_calendar(self):
        import pymysql
        with patch('app.get_connection',side_effect=pymysql.OperationalError('unavailable')):
            response=app.test_client().get('/calendar')
        self.assertEqual(response.status_code,503)
        self.assertIn('불러오지 못했습니다',response.text)

if __name__=='__main__':
    unittest.main()
