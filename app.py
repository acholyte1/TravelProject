from flask import Flask, render_template
from db import get_connection

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

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
