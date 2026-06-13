import pymysql
from flask import Flask, abort, redirect, render_template, request
from db import get_connection

app = Flask(__name__)

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
