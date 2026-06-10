import pymysql
from flask import Flask, redirect, render_template, request
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

    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            if request.method == "POST":
                country_name = request.form["country_name"]
                visit_status = request.form["visit_status"]
                visit_count = int(request.form.get("visit_count") or 0)
                region_id = request.form.get("region_id") or None

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

    return render_template("countries/add.html", regions=regions)

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
