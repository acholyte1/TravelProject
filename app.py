import pymysql
from flask import Flask, abort, redirect, render_template, request
from db import get_connection

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/countries")
def countries():
    conn = get_connection()

    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                """
                SELECT
                    country_id,
                    country_name,
                    visit_status,
                    visit_count,
                    region_id,
                    region_name
                FROM country_region_view
                ORDER BY country_id DESC
                """
            )
            countries = cursor.fetchall()
    finally:
        conn.close()

    return render_template("countries/list.html", countries=countries)

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
