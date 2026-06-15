import pymysql
from datetime import datetime
from flask import Flask, abort, redirect, render_template, request
from db import get_connection

app = Flask(__name__)


def parse_date(value):
    if not value:
        return None

    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/countries")
def countries():
    sort_columns = {
        "id": "country_id",
        "country": "country_name",
        "status": "visit_status",
        "visit_count": "visit_count",
        "region": "region_name",
    }
    sort = request.args.get("sort", "id")
    direction = request.args.get("direction", "desc")

    if sort not in sort_columns:
        sort = "id"
    if direction not in {"asc", "desc"}:
        direction = "desc"

    filters = {
        "country_id": request.args.get("country_id", "").strip(),
        "country_name": request.args.get("country_name", "").strip(),
        "visit_status": request.args.get("visit_status", "").strip(),
        "visit_count": request.args.get("visit_count", "").strip(),
        "region_id": request.args.get("region_id", "").strip(),
    }
    where_clauses = []
    query_params = []

    if filters["country_id"].isdigit():
        where_clauses.append("country_id = %s")
        query_params.append(int(filters["country_id"]))
    if filters["country_name"]:
        where_clauses.append("country_name LIKE %s")
        query_params.append(f"%{filters['country_name']}%")
    if filters["visit_status"] in {"TRIP", "STAY", "WANT"}:
        where_clauses.append("visit_status = %s")
        query_params.append(filters["visit_status"])
    if filters["visit_count"].isdigit():
        where_clauses.append("visit_count = %s")
        query_params.append(int(filters["visit_count"]))
    if filters["region_id"].isdigit():
        where_clauses.append("region_id = %s")
        query_params.append(int(filters["region_id"]))

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    conn = get_connection()

    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                """
                SELECT region_id, region_name
                FROM region_list
                ORDER BY region_name
                """
            )
            regions = cursor.fetchall()

            cursor.execute(
                f"""
                SELECT
                    country_id,
                    country_name,
                    visit_status,
                    visit_count,
                    region_id,
                    region_name
                FROM country_region_view
                {where_sql}
                ORDER BY {sort_columns[sort]} {direction.upper()}, country_id DESC
                """,
                query_params,
            )
            countries = cursor.fetchall()
    finally:
        conn.close()

    return render_template(
        "countries/list.html",
        countries=countries,
        regions=regions,
        filters=filters,
        sort=sort,
        direction=direction,
    )

@app.route("/countries/add", methods=["GET", "POST"])
def add_country():
    conn = get_connection()
    error = None

    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            if request.method == "POST":
                country_name = request.form["country_name"].strip()
                visit_status = request.form["visit_status"]
                visit_count = int(request.form.get("visit_count") or 0)
                region_id = request.form.get("region_id") or None

                cursor.execute(
                    """
                    SELECT country_id
                    FROM country_list
                    WHERE country_name = %s
                    LIMIT 1
                    """,
                    (country_name,),
                )

                if cursor.fetchone():
                    error = "이미 등록된 국가입니다."
                else:
                    try:
                        cursor.execute(
                            """
                            INSERT INTO country_list
                                (country_name, visit_status, visit_count, region_id)
                            VALUES
                                (%s, %s, %s, %s)
                            """,
                            (country_name, visit_status, visit_count, region_id),
                        )
                        conn.commit()
                        return redirect("/countries")
                    except pymysql.err.IntegrityError as exc:
                        conn.rollback()
                        if exc.args[0] != 1062:
                            raise
                        error = "이미 등록된 국가입니다."

            cursor.execute(
                """
                SELECT region_id, region_name
                FROM region_list
                ORDER BY region_name
                """
            )
            regions = cursor.fetchall()
    finally:
        conn.close()

    return render_template(
        "countries/add.html",
        regions=regions,
        error=error,
        form_data=request.form,
    )

@app.route("/countries/<int:country_id>/edit", methods=["GET", "POST"])
def edit_country(country_id):
    conn = get_connection()
    error = None

    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                """
                SELECT
                    country_id,
                    country_name,
                    visit_status,
                    visit_count,
                    region_id
                FROM country_list
                WHERE country_id = %s
                """,
                (country_id,),
            )
            country = cursor.fetchone()

            if country is None:
                abort(404)

            if request.method == "POST":
                country_name = request.form["country_name"].strip()
                visit_status = request.form["visit_status"]
                visit_count = int(request.form.get("visit_count") or 0)
                region_id = request.form.get("region_id") or None

                cursor.execute(
                    """
                    SELECT country_id
                    FROM country_list
                    WHERE country_name = %s
                      AND country_id <> %s
                    LIMIT 1
                    """,
                    (country_name, country_id),
                )

                if cursor.fetchone():
                    error = "이미 등록된 국가입니다."
                else:
                    try:
                        cursor.execute(
                            """
                            UPDATE country_list
                            SET
                                country_name = %s,
                                visit_status = %s,
                                visit_count = %s,
                                region_id = %s
                            WHERE country_id = %s
                            """,
                            (
                                country_name,
                                visit_status,
                                visit_count,
                                region_id,
                                country_id,
                            ),
                        )
                        conn.commit()
                        return redirect("/countries")
                    except pymysql.err.IntegrityError as exc:
                        conn.rollback()
                        if exc.args[0] != 1062:
                            raise
                        error = "이미 등록된 국가입니다."

                form_data = {
                    "country_name": country_name,
                    "visit_status": visit_status,
                    "visit_count": visit_count,
                    "region_id": region_id,
                }
            else:
                form_data = country

            cursor.execute(
                """
                SELECT region_id, region_name
                FROM region_list
                ORDER BY region_name
                """
            )
            regions = cursor.fetchall()
    finally:
        conn.close()

    return render_template(
        "countries/edit.html",
        country=country,
        regions=regions,
        error=error,
        form_data=form_data,
    )


@app.route("/locations")
def locations():
    sort_columns = {
        "id": "c.location_id",
        "country": "co.country_name",
        "location": "c.location_name",
        "status": "c.visit_status",
        "visit_count": "c.visit_count",
        "region": "r.region_name",
    }
    sort = request.args.get("sort", "id")
    direction = request.args.get("direction", "desc")

    if sort not in sort_columns:
        sort = "id"
    if direction not in {"asc", "desc"}:
        direction = "desc"

    filters = {
        "location_id": request.args.get("location_id", "").strip(),
        "country_id": request.args.get("country_id", "").strip(),
        "location_name": request.args.get("location_name", "").strip(),
        "visit_status": request.args.get("visit_status", "").strip(),
        "visit_count": request.args.get("visit_count", "").strip(),
        "region_id": request.args.get("region_id", "").strip(),
    }
    where_clauses = []
    query_params = []

    if filters["location_id"].isdigit():
        where_clauses.append("c.location_id = %s")
        query_params.append(int(filters["location_id"]))
    if filters["country_id"].isdigit():
        where_clauses.append("c.country_id = %s")
        query_params.append(int(filters["country_id"]))
    if filters["location_name"]:
        where_clauses.append("c.location_name LIKE %s")
        query_params.append(f"%{filters['location_name']}%")
    if filters["visit_status"] in {"TRIP", "STAY", "WANT"}:
        where_clauses.append("c.visit_status = %s")
        query_params.append(filters["visit_status"])
    if filters["visit_count"].isdigit():
        where_clauses.append("c.visit_count = %s")
        query_params.append(int(filters["visit_count"]))
    if filters["region_id"].isdigit():
        where_clauses.append("c.region_id = %s")
        query_params.append(int(filters["region_id"]))

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    conn = get_connection()

    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                """
                SELECT country_id, country_name
                FROM country_list
                ORDER BY country_name
                """
            )
            countries = cursor.fetchall()

            cursor.execute(
                """
                SELECT region_id, region_name
                FROM region_list
                ORDER BY region_name
                """
            )
            regions = cursor.fetchall()

            cursor.execute(
                f"""
                SELECT
                    c.location_id,
                    c.country_id,
                    co.country_name,
                    c.location_name,
                    c.visit_status,
                    c.visit_count,
                    c.region_id,
                    r.region_name
                FROM location_list c
                INNER JOIN country_list co
                    ON c.country_id = co.country_id
                LEFT JOIN region_list r
                    ON c.region_id = r.region_id
                {where_sql}
                ORDER BY {sort_columns[sort]} {direction.upper()}, c.location_id DESC
                """,
                query_params,
            )
            locations = cursor.fetchall()
    finally:
        conn.close()

    return render_template(
        "locations/list.html",
        locations=locations,
        countries=countries,
        regions=regions,
        filters=filters,
        sort=sort,
        direction=direction,
    )


@app.route("/locations/add", methods=["GET", "POST"])
def add_location():
    conn = get_connection()
    error = None

    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            if request.method == "POST":
                country_id = request.form.get("country_id", "").strip()
                location_name = request.form.get("location_name", "").strip()
                visit_status = request.form.get("visit_status", "")
                visit_count = int(request.form.get("visit_count") or 0)
                region_id = request.form.get("region_id") or None

                if (
                    not country_id.isdigit()
                    or not location_name
                    or visit_status not in {"TRIP", "STAY", "WANT"}
                ):
                    error = "Country, location name, and visit status are required."
                else:
                    cursor.execute(
                        "SELECT country_id FROM country_list WHERE country_id = %s",
                        (int(country_id),),
                    )
                    if cursor.fetchone() is None:
                        error = "Please select a valid country."
                    else:
                        cursor.execute(
                            """
                            INSERT INTO location_list
                                (country_id, location_name, visit_status, visit_count, region_id)
                            VALUES (%s, %s, %s, %s, %s)
                            """,
                            (
                                int(country_id),
                                location_name,
                                visit_status,
                                visit_count,
                                region_id,
                            ),
                        )
                        conn.commit()
                        return redirect("/locations")

            cursor.execute(
                """
                SELECT country_id, country_name
                FROM country_list
                ORDER BY country_name
                """
            )
            countries = cursor.fetchall()

            cursor.execute(
                """
                SELECT region_id, region_name
                FROM region_list
                ORDER BY region_name
                """
            )
            regions = cursor.fetchall()
    finally:
        conn.close()

    return render_template(
        "locations/add.html",
        countries=countries,
        regions=regions,
        error=error,
        form_data=request.form,
    )


@app.route("/locations/<int:location_id>/edit", methods=["GET", "POST"])
def edit_location(location_id):
    conn = get_connection()
    error = None

    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                """
                SELECT
                    location_id,
                    country_id,
                    location_name,
                    visit_status,
                    visit_count,
                    region_id
                FROM location_list
                WHERE location_id = %s
                """,
                (location_id,),
            )
            location = cursor.fetchone()

            if location is None:
                abort(404)

            if request.method == "POST":
                country_id = request.form.get("country_id", "").strip()
                location_name = request.form.get("location_name", "").strip()
                visit_status = request.form.get("visit_status", "")
                visit_count = int(request.form.get("visit_count") or 0)
                region_id = request.form.get("region_id") or None

                if (
                    not country_id.isdigit()
                    or not location_name
                    or visit_status not in {"TRIP", "STAY", "WANT"}
                ):
                    error = "Country, location name, and visit status are required."
                else:
                    cursor.execute(
                        "SELECT country_id FROM country_list WHERE country_id = %s",
                        (int(country_id),),
                    )
                    if cursor.fetchone() is None:
                        error = "Please select a valid country."
                    else:
                        cursor.execute(
                            """
                            UPDATE location_list
                            SET
                                country_id = %s,
                                location_name = %s,
                                visit_status = %s,
                                visit_count = %s,
                                region_id = %s
                            WHERE location_id = %s
                            """,
                            (
                                int(country_id),
                                location_name,
                                visit_status,
                                visit_count,
                                region_id,
                                location_id,
                            ),
                        )
                        conn.commit()
                        return redirect("/locations")

                form_data = {
                    "country_id": country_id,
                    "location_name": location_name,
                    "visit_status": visit_status,
                    "visit_count": visit_count,
                    "region_id": region_id,
                }
            else:
                form_data = location

            cursor.execute(
                """
                SELECT country_id, country_name
                FROM country_list
                ORDER BY country_name
                """
            )
            countries = cursor.fetchall()

            cursor.execute(
                """
                SELECT region_id, region_name
                FROM region_list
                ORDER BY region_name
                """
            )
            regions = cursor.fetchall()
    finally:
        conn.close()

    return render_template(
        "locations/edit.html",
        location=location,
        countries=countries,
        regions=regions,
        error=error,
        form_data=form_data,
    )


@app.route("/trip-countries")
def trip_countries():
    sort_columns = {
        "trip_id": "tc.trip_id",
        "country": "c.country_name",
        "in_date": "tc.in_date",
        "out_date": "tc.out_date",
        "stayed_day": "tc.stayed_day",
    }
    sort = request.args.get("sort", "trip_id")
    direction = request.args.get("direction", "desc")

    if sort not in sort_columns:
        sort = "trip_id"
    if direction not in {"asc", "desc"}:
        direction = "desc"

    filters = {
        "trip_id": request.args.get("trip_id", "").strip(),
        "country_id": request.args.get("country_id", "").strip(),
        "in_date": request.args.get("in_date", "").strip(),
        "out_date": request.args.get("out_date", "").strip(),
    }
    where_clauses = ["t.is_deleted = 0"]
    query_params = []

    if filters["trip_id"].isdigit():
        where_clauses.append("tc.trip_id = %s")
        query_params.append(int(filters["trip_id"]))
    if filters["country_id"].isdigit():
        where_clauses.append("tc.country_id = %s")
        query_params.append(int(filters["country_id"]))

    in_date = parse_date(filters["in_date"])
    out_date = parse_date(filters["out_date"])
    if in_date:
        where_clauses.append("tc.in_date = %s")
        query_params.append(in_date)
    if out_date:
        where_clauses.append("tc.out_date = %s")
        query_params.append(out_date)

    conn = get_connection()

    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                """
                SELECT country_id, country_name
                FROM country_list
                ORDER BY country_name
                """
            )
            countries = cursor.fetchall()

            cursor.execute(
                f"""
                SELECT
                    tc.trip_country_id,
                    tc.trip_id,
                    tc.country_id,
                    c.country_name,
                    tc.in_date,
                    tc.out_date,
                    tc.stayed_day
                FROM trip_country_list tc
                INNER JOIN trip_list t
                    ON tc.trip_id = t.trip_id
                INNER JOIN country_list c
                    ON tc.country_id = c.country_id
                WHERE {" AND ".join(where_clauses)}
                ORDER BY {sort_columns[sort]} {direction.upper()},
                         tc.trip_country_id DESC
                """,
                query_params,
            )
            trip_countries = cursor.fetchall()
    finally:
        conn.close()

    return render_template(
        "trip_countries/list.html",
        trip_countries=trip_countries,
        countries=countries,
        filters=filters,
        sort=sort,
        direction=direction,
    )


@app.route("/trip-countries/add", methods=["GET", "POST"])
def add_trip_country():
    conn = get_connection()
    error = None

    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            if request.method == "POST":
                trip_id = request.form.get("trip_id", "").strip()
                country_id = request.form.get("country_id", "").strip()
                in_date = parse_date(request.form.get("in_date", "").strip())
                out_date = parse_date(request.form.get("out_date", "").strip())

                if not trip_id.isdigit() or not country_id.isdigit():
                    error = "Trip and country are required."
                elif in_date is None or out_date is None:
                    error = "In date and out date are required."
                elif in_date > out_date:
                    error = "In date cannot be later than out date."
                else:
                    cursor.execute(
                        """
                        SELECT trip_id
                        FROM trip_list
                        WHERE trip_id = %s AND is_deleted = 0
                        """,
                        (int(trip_id),),
                    )
                    trip_exists = cursor.fetchone() is not None
                    cursor.execute(
                        "SELECT country_id FROM country_list WHERE country_id = %s",
                        (int(country_id),),
                    )
                    country_exists = cursor.fetchone() is not None

                    if not trip_exists:
                        error = "Please select a valid trip."
                    elif not country_exists:
                        error = "Please select a valid country."
                    else:
                        stayed_day = (out_date - in_date).days
                        try:
                            cursor.execute(
                                """
                                INSERT INTO trip_country_list
                                    (trip_id, country_id, in_date, out_date, stayed_day)
                                VALUES (%s, %s, %s, %s, %s)
                                """,
                                (
                                    int(trip_id),
                                    int(country_id),
                                    in_date,
                                    out_date,
                                    stayed_day,
                                ),
                            )
                            conn.commit()
                            return redirect("/trip-countries")
                        except pymysql.err.IntegrityError as exc:
                            conn.rollback()
                            if exc.args[0] != 1062:
                                raise
                            error = "The same trip, country, and dates are already registered."

            cursor.execute(
                """
                SELECT trip_id, in_date, out_date
                FROM trip_list
                WHERE is_deleted = 0
                ORDER BY trip_id DESC
                """
            )
            trips = cursor.fetchall()
            cursor.execute(
                """
                SELECT country_id, country_name
                FROM country_list
                ORDER BY country_name
                """
            )
            countries = cursor.fetchall()
    finally:
        conn.close()

    return render_template(
        "trip_countries/add.html",
        trips=trips,
        countries=countries,
        error=error,
        form_data=request.form,
    )


@app.route("/trip-countries/<int:trip_country_id>/edit", methods=["GET", "POST"])
def edit_trip_country(trip_country_id):
    conn = get_connection()
    error = None

    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                """
                SELECT trip_country_id, trip_id, country_id, in_date, out_date, stayed_day
                FROM trip_country_list
                WHERE trip_country_id = %s
                """,
                (trip_country_id,),
            )
            trip_country = cursor.fetchone()

            if trip_country is None:
                abort(404)

            if request.method == "POST":
                trip_id = request.form.get("trip_id", "").strip()
                country_id = request.form.get("country_id", "").strip()
                in_date_value = request.form.get("in_date", "").strip()
                out_date_value = request.form.get("out_date", "").strip()
                in_date = parse_date(in_date_value)
                out_date = parse_date(out_date_value)

                if not trip_id.isdigit() or not country_id.isdigit():
                    error = "Trip and country are required."
                elif in_date is None or out_date is None:
                    error = "In date and out date are required."
                elif in_date > out_date:
                    error = "In date cannot be later than out date."
                else:
                    cursor.execute(
                        """
                        SELECT trip_id
                        FROM trip_list
                        WHERE trip_id = %s AND is_deleted = 0
                        """,
                        (int(trip_id),),
                    )
                    trip_exists = cursor.fetchone() is not None
                    cursor.execute(
                        "SELECT country_id FROM country_list WHERE country_id = %s",
                        (int(country_id),),
                    )
                    country_exists = cursor.fetchone() is not None

                    if not trip_exists:
                        error = "Please select a valid trip."
                    elif not country_exists:
                        error = "Please select a valid country."
                    else:
                        stayed_day = (out_date - in_date).days
                        try:
                            cursor.execute(
                                """
                                UPDATE trip_country_list
                                SET trip_id = %s,
                                    country_id = %s,
                                    in_date = %s,
                                    out_date = %s,
                                    stayed_day = %s
                                WHERE trip_country_id = %s
                                """,
                                (
                                    int(trip_id),
                                    int(country_id),
                                    in_date,
                                    out_date,
                                    stayed_day,
                                    trip_country_id,
                                ),
                            )
                            conn.commit()
                            return redirect("/trip-countries")
                        except pymysql.err.IntegrityError as exc:
                            conn.rollback()
                            if exc.args[0] != 1062:
                                raise
                            error = "The same trip, country, and dates are already registered."

                form_data = {
                    "trip_id": trip_id,
                    "country_id": country_id,
                    "in_date": in_date_value,
                    "out_date": out_date_value,
                }
            else:
                form_data = trip_country

            cursor.execute(
                """
                SELECT trip_id, in_date, out_date
                FROM trip_list
                WHERE is_deleted = 0
                ORDER BY trip_id DESC
                """
            )
            trips = cursor.fetchall()
            cursor.execute(
                """
                SELECT country_id, country_name
                FROM country_list
                ORDER BY country_name
                """
            )
            countries = cursor.fetchall()
    finally:
        conn.close()

    return render_template(
        "trip_countries/edit.html",
        trip_country=trip_country,
        trips=trips,
        countries=countries,
        error=error,
        form_data=form_data,
    )


@app.route("/trips")
def trips():
    sort_columns = {
        "id": "trip_id",
        "in_date": "in_date",
        "out_date": "out_date",
        "stayed_day": "stayed_day",
    }
    sort = request.args.get("sort", "id")
    direction = request.args.get("direction", "desc")

    if sort not in sort_columns:
        sort = "id"
    if direction not in {"asc", "desc"}:
        direction = "desc"

    filters = {
        "in_date": request.args.get("in_date", "").strip(),
        "out_date": request.args.get("out_date", "").strip(),
        "period_start": request.args.get("period_start", "").strip(),
        "period_end": request.args.get("period_end", "").strip(),
    }
    where_clauses = ["is_deleted = 0"]
    query_params = []

    in_date = parse_date(filters["in_date"])
    out_date = parse_date(filters["out_date"])
    period_start = parse_date(filters["period_start"])
    period_end = parse_date(filters["period_end"])

    if in_date:
        where_clauses.append("in_date = %s")
        query_params.append(in_date)
    if out_date:
        where_clauses.append("out_date = %s")
        query_params.append(out_date)
    if period_start:
        where_clauses.append("out_date >= %s")
        query_params.append(period_start)
    if period_end:
        where_clauses.append("in_date <= %s")
        query_params.append(period_end)

    where_sql = "WHERE " + " AND ".join(where_clauses)
    conn = get_connection()

    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                f"""
                SELECT trip_id, in_date, out_date, stayed_day
                FROM trip_list
                {where_sql}
                ORDER BY {sort_columns[sort]} {direction.upper()}, trip_id DESC
                """,
                query_params,
            )
            trips = cursor.fetchall()
    finally:
        conn.close()

    return render_template(
        "trips/list.html",
        trips=trips,
        filters=filters,
        sort=sort,
        direction=direction,
    )


@app.route("/trips/add", methods=["GET", "POST"])
def add_trip():
    error = None

    if request.method == "POST":
        in_date = parse_date(request.form.get("in_date", "").strip())
        out_date = parse_date(request.form.get("out_date", "").strip())

        if in_date is None or out_date is None:
            error = "In date and out date are required."
        elif in_date > out_date:
            error = "In date cannot be later than out date."
        else:
            stayed_day = (out_date - in_date).days
            conn = get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO trip_list (in_date, out_date, stayed_day)
                        VALUES (%s, %s, %s)
                        """,
                        (in_date, out_date, stayed_day),
                    )
                conn.commit()
            finally:
                conn.close()

            return redirect("/trips")

    return render_template(
        "trips/add.html",
        error=error,
        form_data=request.form,
    )


@app.route("/trips/<int:trip_id>/edit", methods=["GET", "POST"])
def edit_trip(trip_id):
    conn = get_connection()
    error = None

    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                """
                SELECT trip_id, in_date, out_date, stayed_day
                FROM trip_list
                WHERE trip_id = %s AND is_deleted = 0
                """,
                (trip_id,),
            )
            trip = cursor.fetchone()

            if trip is None:
                abort(404)

            if request.method == "POST":
                in_date_value = request.form.get("in_date", "").strip()
                out_date_value = request.form.get("out_date", "").strip()
                in_date = parse_date(in_date_value)
                out_date = parse_date(out_date_value)

                if in_date is None or out_date is None:
                    error = "In date and out date are required."
                elif in_date > out_date:
                    error = "In date cannot be later than out date."
                else:
                    stayed_day = (out_date - in_date).days
                    cursor.execute(
                        """
                        UPDATE trip_list
                        SET in_date = %s, out_date = %s, stayed_day = %s
                        WHERE trip_id = %s AND is_deleted = 0
                        """,
                        (in_date, out_date, stayed_day, trip_id),
                    )
                    conn.commit()
                    return redirect("/trips")

                form_data = {
                    "in_date": in_date_value,
                    "out_date": out_date_value,
                }
            else:
                form_data = trip
    finally:
        conn.close()

    return render_template(
        "trips/edit.html",
        trip=trip,
        error=error,
        form_data=form_data,
    )


@app.route("/trips/<int:trip_id>/delete", methods=["POST"])
def delete_trip(trip_id):
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE trip_list
                SET is_deleted = 1
                WHERE trip_id = %s AND is_deleted = 0
                """,
                (trip_id,),
            )
        conn.commit()
    finally:
        conn.close()

    return redirect("/trips")

@app.route("/db-test")
def db_test():
    conn = get_connection()
    
    with conn.cursor() as cursor:
        cursor.execute("SELECT VERSION()")
        result = cursor.fetchone()

    conn.close()
    
    return f"MySQL Version: {result[0]}"

if __name__ == "__main__":
    app.run(debug=True)
