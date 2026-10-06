import pymysql
from datetime import datetime
from flask import Flask, abort, jsonify, redirect, render_template, request
from db import get_connection

app = Flask(__name__)


def parse_date(value):
    if not value:
        return None

    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_optional_date(value):
    value = value.strip()
    if not value:
        return None, True

    parsed = parse_date(value)
    return parsed, parsed is not None


def calculate_stayed_day(in_date, out_date):
    if in_date is None or out_date is None:
        return None

    return (out_date - in_date).days

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/travel")
def travel():
    return render_template("travel.html")


@app.route("/calendar")
def calendar_page():
    from calendar import monthrange
    from datetime import timedelta, timezone
    from calendar_view import build_month

    today = datetime.now(timezone(timedelta(hours=9))).date()
    month = request.args.get("month", type=int) if "month" in request.args else today.month
    if month is None or not 1 <= month <= 12:
        abort(400)
    selected_day = request.args.get("day", type=int) if "day" in request.args else (today.day if month == today.month else 1)
    if selected_day is None or not 1 <= selected_day <= monthrange(2000, month)[1]:
        abort(400)
    connection = None
    error = None
    trips, countries, locations = [], [], []
    try:
        connection = get_connection()
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SELECT trip_id, trip_name, trip_memo, in_date, out_date FROM trip_list WHERE is_deleted = 0")
            trips = cursor.fetchall()
            cursor.execute("""
                SELECT tc.trip_id, tc.country_id, tc.in_date, tc.out_date,
                       COALESCE(NULLIF(c.country_name_ko, ''), c.country_name) AS name
                FROM trip_country_list tc JOIN country_list c ON c.country_id = tc.country_id
                JOIN trip_list t ON t.trip_id = tc.trip_id WHERE t.is_deleted = 0
            """)
            countries = cursor.fetchall()
            cursor.execute("""
                SELECT tl.trip_id, tl.country_id, tl.location_in, tl.location_out,
                       COALESCE(NULLIF(l.location_name_ko, ''), l.location_name) AS name
                FROM trip_location_list tl JOIN location_list l ON l.location_id = tl.location_id
                JOIN trip_list t ON t.trip_id = tl.trip_id WHERE t.is_deleted = 0
            """)
            locations = cursor.fetchall()
    except pymysql.MySQLError:
        app.logger.exception("Calendar database read failed")
        error = "여행 기록을 불러오지 못했습니다. DB 연결을 확인한 뒤 다시 시도해 주세요."
        trips, countries, locations = [], [], []
    finally:
        if connection is not None:
            connection.close()
    days, incomplete = build_month(trips, countries, locations, month)
    return render_template("calendar.html", month=month, selected_day=selected_day,
                           days=days, entries=days[selected_day], incomplete=incomplete,
                           today=today, error=error), (503 if error else 200)


@app.route("/api/travel/search")
def travel_search():
    sort_columns = {
        "name": "name",
        "kind": "kind",
        "region": "region_name",
        "status": "visit_status",
        "visit_count": "visit_count",
    }
    kind_values = {
        "country": "country",
        "location": "location",
        "국가": "country",
        "도시": "location",
    }

    query = request.args.get("q", "").strip()
    kind = request.args.get("kind", "all").strip()
    region = request.args.get("region", "").strip()
    status = request.args.get("status", "").strip()
    sort = request.args.get("sort", "name").strip()
    direction = request.args.get("direction", "asc").strip()

    if sort not in sort_columns:
        sort = "name"
    if direction not in {"asc", "desc"}:
        direction = "asc"

    where_clauses = []
    query_params = []

    if query:
        where_clauses.append(
            "(name LIKE %s OR location_name_en LIKE %s "
            "OR country_name LIKE %s OR country_name_en LIKE %s)"
        )
        query_params.extend([f"%{query}%"] * 4)
    if kind in kind_values:
        where_clauses.append("kind = %s")
        query_params.append(kind_values[kind])
    if region:
        where_clauses.append("region_name = %s")
        query_params.append(region)
    if status in {"TRIP", "STAY", "WANT"}:
        where_clauses.append("visit_status = %s")
        query_params.append(status)

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    conn = get_connection()

    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                f"""
                SELECT
                    id,
                    kind,
                    name,
                    country_name,
                    region_name,
                    visit_status,
                    visit_count
                FROM (
                    SELECT
                        c.country_id AS id,
                        'country' AS kind,
                        COALESCE(NULLIF(c.country_name_ko, ''), c.country_name) AS name,
                        c.country_name AS location_name_en,
                        COALESCE(NULLIF(c.country_name_ko, ''), c.country_name) AS country_name,
                        c.country_name AS country_name_en,
                        r.region_name_ko AS region_name,
                        c.visit_status AS visit_status,
                        c.visit_count AS visit_count
                    FROM country_list c
                    LEFT JOIN region_list r
                        ON c.region_id = r.region_id

                    UNION ALL

                    SELECT
                        l.location_id AS id,
                        'location' AS kind,
                        COALESCE(NULLIF(l.location_name_ko, ''), l.location_name) AS name,
                        l.location_name AS location_name_en,
                        COALESCE(NULLIF(c.country_name_ko, ''), c.country_name) AS country_name,
                        c.country_name AS country_name_en,
                        COALESCE(lr.region_name_ko, cr.region_name_ko) AS region_name,
                        l.visit_status AS visit_status,
                        l.visit_count AS visit_count
                    FROM location_list l
                    INNER JOIN country_list c
                        ON l.country_id = c.country_id
                    LEFT JOIN region_list lr
                        ON l.region_id = lr.region_id
                    LEFT JOIN region_list cr
                        ON c.region_id = cr.region_id
                ) travel_records
                {where_sql}
                ORDER BY {sort_columns[sort]} {direction.upper()}, kind ASC, id DESC
                """,
                query_params,
            )
            items = cursor.fetchall()
    finally:
        conn.close()

    return jsonify({"items": items, "total": len(items)})

@app.route("/countries")
def countries():
    sort_columns = {
        "id": "country_id",
        "country": "COALESCE(NULLIF(country_name_ko, ''), country_name)",
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
        where_clauses.append("(country_name LIKE %s OR country_name_ko LIKE %s)")
        query_params.extend(
            [f"%{filters['country_name']}%", f"%{filters['country_name']}%"]
        )
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
                SELECT region_id, region_name_ko
                FROM region_list
                ORDER BY region_name_ko
                """
            )
            regions = cursor.fetchall()

            cursor.execute(
                f"""
                SELECT
                    country_id,
                    COALESCE(NULLIF(country_name_ko, ''), country_name) AS country_name,
                    visit_status,
                    visit_count,
                    region_id,
                    region_name_ko AS region_name
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
                country_name_ko = request.form.get("country_name_ko", "").strip() or None
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
                                (country_name, country_name_ko, visit_status, visit_count, region_id)
                            VALUES
                                (%s, %s, %s, %s, %s)
                            """,
                            (country_name, country_name_ko, visit_status, visit_count, region_id),
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
                SELECT region_id, region_name_ko
                FROM region_list
                ORDER BY region_name_ko
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
                    country_name_ko,
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
                country_name_ko = request.form.get("country_name_ko", "").strip() or None
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
                                country_name_ko = %s,
                                visit_status = %s,
                                visit_count = %s,
                                region_id = %s
                            WHERE country_id = %s
                            """,
                            (
                                country_name,
                                country_name_ko,
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
                    "country_name_ko": country_name_ko or "",
                    "visit_status": visit_status,
                    "visit_count": visit_count,
                    "region_id": region_id,
                }
            else:
                form_data = country

            cursor.execute(
                """
                SELECT region_id, region_name_ko
                FROM region_list
                ORDER BY region_name_ko
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
        "country": "COALESCE(NULLIF(co.country_name_ko, ''), co.country_name)",
        "location": "COALESCE(NULLIF(c.location_name_ko, ''), c.location_name)",
        "status": "c.visit_status",
        "visit_count": "c.visit_count",
        "region": "r.region_name_ko",
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
        where_clauses.append(
            "(c.location_name LIKE %s OR c.location_name_ko LIKE %s)"
        )
        query_params.extend(
            [f"%{filters['location_name']}%", f"%{filters['location_name']}%"]
        )
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
                SELECT country_id,
                       COALESCE(NULLIF(country_name_ko, ''), country_name) AS country_name
                FROM country_list
                ORDER BY COALESCE(NULLIF(country_name_ko, ''), country_name)
                """
            )
            countries = cursor.fetchall()

            cursor.execute(
                """
                SELECT region_id, region_name_ko
                FROM region_list
                ORDER BY region_name_ko
                """
            )
            regions = cursor.fetchall()

            cursor.execute(
                f"""
                SELECT
                    c.location_id,
                    c.country_id,
                    COALESCE(NULLIF(co.country_name_ko, ''), co.country_name) AS country_name,
                    COALESCE(NULLIF(c.location_name_ko, ''), c.location_name) AS location_name,
                    c.visit_status,
                    c.visit_count,
                    c.region_id,
                    r.region_name_ko AS region_name
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
                location_name_ko = request.form.get("location_name_ko", "").strip() or None
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
                                (country_id, location_name, location_name_ko,
                                 visit_status, visit_count, region_id)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            (
                                int(country_id),
                                location_name,
                                location_name_ko,
                                visit_status,
                                visit_count,
                                region_id,
                            ),
                        )
                        conn.commit()
                        return redirect("/locations")

            cursor.execute(
                """
                SELECT country_id,
                       COALESCE(NULLIF(country_name_ko, ''), country_name) AS country_name
                FROM country_list
                ORDER BY COALESCE(NULLIF(country_name_ko, ''), country_name)
                """
            )
            countries = cursor.fetchall()

            cursor.execute(
                """
                SELECT region_id, region_name_ko
                FROM region_list
                ORDER BY region_name_ko
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
                    location_name_ko,
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
                location_name_ko = request.form.get("location_name_ko", "").strip() or None
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
                                location_name_ko = %s,
                                visit_status = %s,
                                visit_count = %s,
                                region_id = %s
                            WHERE location_id = %s
                            """,
                            (
                                int(country_id),
                                location_name,
                                location_name_ko,
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
                    "location_name_ko": location_name_ko or "",
                    "visit_status": visit_status,
                    "visit_count": visit_count,
                    "region_id": region_id,
                }
            else:
                form_data = location

            cursor.execute(
                """
                SELECT country_id,
                       COALESCE(NULLIF(country_name_ko, ''), country_name) AS country_name
                FROM country_list
                ORDER BY COALESCE(NULLIF(country_name_ko, ''), country_name)
                """
            )
            countries = cursor.fetchall()

            cursor.execute(
                """
                SELECT region_id, region_name_ko
                FROM region_list
                ORDER BY region_name_ko
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


@app.route("/trips/<int:trip_id>", methods=["GET", "POST"])
def trip_detail(trip_id):
    conn = get_connection()
    error = None
    add_form_data = {}
    edit_form_data = {}
    editing_trip_country_id = None

    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                """
                SELECT trip_id, trip_name, trip_memo, in_date, out_date, stayed_day
                FROM trip_list
                WHERE trip_id = %s AND is_deleted = 0
                """,
                (trip_id,),
            )
            trip = cursor.fetchone()

            if trip is None:
                abort(404)

            if request.method == "POST":
                action = request.form.get("action", "")
                country_id = request.form.get("country_id", "").strip()
                in_date_value = request.form.get("in_date", "").strip()
                out_date_value = request.form.get("out_date", "").strip()
                in_date = parse_date(in_date_value)
                out_date = parse_date(out_date_value)

                if action == "add":
                    add_form_data = request.form
                elif action == "edit":
                    trip_country_id = request.form.get("trip_country_id", "").strip()
                    if not trip_country_id.isdigit():
                        abort(404)
                    editing_trip_country_id = int(trip_country_id)
                    edit_form_data = request.form
                    cursor.execute(
                        """
                        SELECT trip_country_id
                        FROM trip_country_list
                        WHERE trip_country_id = %s AND trip_id = %s
                        """,
                        (editing_trip_country_id, trip_id),
                    )
                    if cursor.fetchone() is None:
                        abort(404)
                else:
                    abort(400)

                if not country_id.isdigit():
                    error = "Country is required."
                elif in_date is None or out_date is None:
                    error = "In date and out date are required."
                elif in_date > out_date:
                    error = "In date cannot be later than out date."
                else:
                    cursor.execute(
                        "SELECT country_id FROM country_list WHERE country_id = %s",
                        (int(country_id),),
                    )
                    if cursor.fetchone() is None:
                        error = "Please select a valid country."
                    else:
                        stayed_day = (out_date - in_date).days
                        try:
                            if action == "add":
                                cursor.execute(
                                    """
                                    INSERT INTO trip_country_list
                                        (trip_id, country_id, in_date, out_date, stayed_day)
                                    VALUES (%s, %s, %s, %s, %s)
                                    """,
                                    (
                                        trip_id,
                                        int(country_id),
                                        in_date,
                                        out_date,
                                        stayed_day,
                                    ),
                                )
                            else:
                                cursor.execute(
                                    """
                                    UPDATE trip_country_list
                                    SET country_id = %s,
                                        in_date = %s,
                                        out_date = %s,
                                        stayed_day = %s
                                    WHERE trip_country_id = %s AND trip_id = %s
                                    """,
                                    (
                                        int(country_id),
                                        in_date,
                                        out_date,
                                        stayed_day,
                                        editing_trip_country_id,
                                        trip_id,
                                    ),
                                )
                            conn.commit()
                            return redirect(f"/trips/{trip_id}")
                        except pymysql.err.IntegrityError as exc:
                            conn.rollback()
                            if exc.args[0] != 1062:
                                raise
                            error = "The same trip, country, and dates are already registered."

            cursor.execute(
                """
                SELECT country_id,
                       COALESCE(NULLIF(country_name_ko, ''), country_name) AS country_name
                FROM country_list
                ORDER BY COALESCE(NULLIF(country_name_ko, ''), country_name)
                """
            )
            countries = cursor.fetchall()
            cursor.execute(
                """
                SELECT
                    tc.trip_country_id,
                    tc.country_id,
                    COALESCE(NULLIF(c.country_name_ko, ''), c.country_name) AS country_name,
                    tc.in_date,
                    tc.out_date,
                    tc.stayed_day
                FROM trip_country_list tc
                INNER JOIN country_list c
                    ON tc.country_id = c.country_id
                WHERE tc.trip_id = %s
                ORDER BY tc.in_date, tc.trip_country_id
                """,
                (trip_id,),
            )
            trip_countries = cursor.fetchall()
    finally:
        conn.close()

    return render_template(
        "trips/detail.html",
        trip=trip,
        trip_countries=trip_countries,
        countries=countries,
        error=error,
        add_form_data=add_form_data,
        edit_form_data=edit_form_data,
        editing_trip_country_id=editing_trip_country_id,
    )


@app.route("/trips/<int:trip_id>/countries/<int:country_id>/locations", methods=["GET", "POST"])
def trip_locations(trip_id, country_id):
    conn = get_connection()
    error = None
    add_form_data = {}
    edit_form_data = {}
    editing_trip_location_id = None

    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                """
                SELECT
                    t.trip_id,
                    t.trip_name,
                    t.in_date AS trip_in_date,
                    t.out_date AS trip_out_date,
                    tc.trip_country_id,
                    tc.in_date AS country_in_date,
                    tc.out_date AS country_out_date,
                    c.country_id,
                    COALESCE(NULLIF(c.country_name_ko, ''), c.country_name) AS country_name
                FROM trip_country_list tc
                INNER JOIN trip_list t
                    ON tc.trip_id = t.trip_id
                INNER JOIN country_list c
                    ON tc.country_id = c.country_id
                WHERE tc.trip_id = %s
                  AND tc.country_id = %s
                  AND t.is_deleted = 0
                ORDER BY tc.trip_country_id
                LIMIT 1
                """,
                (trip_id, country_id),
            )
            trip_country = cursor.fetchone()

            if trip_country is None:
                abort(404)

            if request.method == "POST":
                action = request.form.get("action", "")
                location_id = request.form.get("location_id", "").strip()
                location_in_value = request.form.get("location_in", "").strip()
                location_out_value = request.form.get("location_out", "").strip()
                location_in, location_in_valid = parse_optional_date(location_in_value)
                location_out, location_out_valid = parse_optional_date(location_out_value)

                if action == "add":
                    add_form_data = request.form
                elif action == "edit":
                    trip_location_id = request.form.get("trip_location_id", "").strip()
                    if not trip_location_id.isdigit():
                        abort(404)
                    editing_trip_location_id = int(trip_location_id)
                    edit_form_data = request.form
                    cursor.execute(
                        """
                        SELECT trip_location_id
                        FROM trip_location_list
                        WHERE trip_location_id = %s
                          AND trip_id = %s
                          AND country_id = %s
                        """,
                        (editing_trip_location_id, trip_id, country_id),
                    )
                    if cursor.fetchone() is None:
                        abort(404)
                else:
                    abort(400)

                if not location_id.isdigit():
                    error = "Location is required."
                elif not location_in_valid or not location_out_valid:
                    error = "Please enter valid location dates."
                elif location_in is not None and location_out is not None and location_in > location_out:
                    error = "Location in cannot be later than location out."
                else:
                    cursor.execute(
                        """
                        SELECT location_id
                        FROM location_list
                        WHERE location_id = %s AND country_id = %s
                        """,
                        (int(location_id), country_id),
                    )
                    if cursor.fetchone() is None:
                        error = "Please select a valid location for this country."
                    else:
                        stayed_day = calculate_stayed_day(location_in, location_out)
                        if action == "add":
                            cursor.execute(
                                """
                                INSERT INTO trip_location_list
                                    (trip_id, country_id, location_id, location_in, location_out, stayed_day)
                                VALUES (%s, %s, %s, %s, %s, %s)
                                """,
                                (
                                    trip_id,
                                    country_id,
                                    int(location_id),
                                    location_in,
                                    location_out,
                                    stayed_day,
                                ),
                            )
                        else:
                            cursor.execute(
                                """
                                UPDATE trip_location_list
                                SET location_id = %s,
                                    location_in = %s,
                                    location_out = %s,
                                    stayed_day = %s
                                WHERE trip_location_id = %s
                                  AND trip_id = %s
                                  AND country_id = %s
                                """,
                                (
                                    int(location_id),
                                    location_in,
                                    location_out,
                                    stayed_day,
                                    editing_trip_location_id,
                                    trip_id,
                                    country_id,
                                ),
                            )
                        conn.commit()
                        return redirect(f"/trips/{trip_id}/countries/{country_id}/locations")

            cursor.execute(
                """
                SELECT location_id,
                       COALESCE(NULLIF(location_name_ko, ''), location_name) AS location_name
                FROM location_list
                WHERE country_id = %s
                ORDER BY COALESCE(NULLIF(location_name_ko, ''), location_name)
                """,
                (country_id,),
            )
            locations = cursor.fetchall()

            cursor.execute(
                """
                SELECT
                    tl.trip_location_id,
                    tl.location_id,
                    COALESCE(NULLIF(l.location_name_ko, ''), l.location_name) AS location_name,
                    tl.location_in,
                    tl.location_out,
                    tl.stayed_day
                FROM trip_location_list tl
                INNER JOIN location_list l
                    ON tl.location_id = l.location_id
                WHERE tl.trip_id = %s
                  AND tl.country_id = %s
                ORDER BY tl.location_in, tl.trip_location_id
                """,
                (trip_id, country_id),
            )
            trip_locations = cursor.fetchall()
    finally:
        conn.close()

    return render_template(
        "trips/locations.html",
        trip_country=trip_country,
        locations=locations,
        trip_locations=trip_locations,
        error=error,
        add_form_data=add_form_data,
        edit_form_data=edit_form_data,
        editing_trip_location_id=editing_trip_location_id,
    )


@app.route("/trips")
def trips():
    sort_columns = {
        "id": "trip_id",
        "name": "trip_name",
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
        "trip_name": request.args.get("trip_name", "").strip(),
        "in_date": request.args.get("in_date", "").strip(),
        "out_date": request.args.get("out_date", "").strip(),
        "period_start": request.args.get("period_start", "").strip(),
        "period_end": request.args.get("period_end", "").strip(),
    }
    where_clauses = ["is_deleted = 0"]
    query_params = []

    if filters["trip_name"]:
        where_clauses.append("trip_name LIKE %s")
        query_params.append(f"%{filters['trip_name']}%")

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
                SELECT trip_id, trip_name, trip_memo, in_date, out_date, stayed_day
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
        trip_name = request.form.get("trip_name", "").strip()
        trip_memo = request.form.get("trip_memo", "").strip() or None
        in_date = parse_date(request.form.get("in_date", "").strip())
        out_date = parse_date(request.form.get("out_date", "").strip())

        if not trip_name:
            error = "Trip name is required."
        elif len(trip_name) > 100:
            error = "Trip name must be 100 characters or fewer."
        elif in_date is None or out_date is None:
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
                        INSERT INTO trip_list
                            (trip_name, trip_memo, in_date, out_date, stayed_day)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (trip_name, trip_memo, in_date, out_date, stayed_day),
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
                SELECT trip_id, trip_name, trip_memo, in_date, out_date, stayed_day
                FROM trip_list
                WHERE trip_id = %s AND is_deleted = 0
                """,
                (trip_id,),
            )
            trip = cursor.fetchone()

            if trip is None:
                abort(404)

            if request.method == "POST":
                trip_name = request.form.get("trip_name", "").strip()
                trip_memo = request.form.get("trip_memo", "").strip() or None
                in_date_value = request.form.get("in_date", "").strip()
                out_date_value = request.form.get("out_date", "").strip()
                in_date = parse_date(in_date_value)
                out_date = parse_date(out_date_value)

                if not trip_name:
                    error = "Trip name is required."
                elif len(trip_name) > 100:
                    error = "Trip name must be 100 characters or fewer."
                elif in_date is None or out_date is None:
                    error = "In date and out date are required."
                elif in_date > out_date:
                    error = "In date cannot be later than out date."
                else:
                    stayed_day = (out_date - in_date).days
                    cursor.execute(
                        """
                        UPDATE trip_list
                        SET trip_name = %s,
                            trip_memo = %s,
                            in_date = %s,
                            out_date = %s,
                            stayed_day = %s
                        WHERE trip_id = %s AND is_deleted = 0
                        """,
                        (
                            trip_name,
                            trip_memo,
                            in_date,
                            out_date,
                            stayed_day,
                            trip_id,
                        ),
                    )
                    conn.commit()
                    return redirect("/trips")

                form_data = {
                    "trip_name": trip_name,
                    "trip_memo": trip_memo or "",
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
