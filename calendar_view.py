"""Year-independent month/day projection; source dates remain unchanged."""
from calendar import monthrange
from datetime import date


def build_month(trips, countries, locations, month):
    days = {day: [] for day in range(1, monthrange(2000, month)[1] + 1)}
    incomplete = 0
    for trip in trips:
        if (trip.get("trip_name") or "").strip() == "인생":
            continue
        start, end = trip['in_date'], trip['out_date']
        if not start or not end or end < start:
            incomplete += 1
            continue
        trip_countries = [row for row in countries if row['trip_id'] == trip['trip_id']]
        trip_locations = [row for row in locations if row['trip_id'] == trip['trip_id']]
        for year in range(start.year, end.year + 1):
            for day in range(1, monthrange(year, month)[1] + 1):
                actual = date(year, month, day)
                if not start <= actual <= end:
                    continue
                def matches(row, first, last):
                    return row[first] is not None and row[last] is not None and row[first] <= actual <= row[last]
                days[day].append(dict(trip, actual_date=actual,
                    countries=[r for r in trip_countries if matches(r, 'in_date', 'out_date')],
                    locations=[r for r in trip_locations if matches(r, 'location_in', 'location_out')]))
    for entries in days.values():
        entries.sort(key=lambda entry: (entry['actual_date'], entry['trip_id']), reverse=True)
    return days, incomplete
