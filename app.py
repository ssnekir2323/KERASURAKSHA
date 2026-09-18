from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import sqlite3
import csv
import os
import math
import requests
from datetime import datetime
from functools import wraps

from ml.risk_model import predict_risk


app = Flask(__name__)

DATABASE = os.environ.get("DATABASE_PATH", "kerasuraksha.db")
RISK_FILE = os.path.join("data", "risk_zones.csv")
SHELTER_FILE = os.path.join("data", "shelters.csv")

app.secret_key = "KERASURAKSHA-DEVELOPMENT-SECRET-KEY"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "KERA@12345"
#==================================
# ADMIN PROTECTION
# ============================================================

def admin_required(function):

    @wraps(function)
    def decorated_function(*args, **kwargs):

        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))

        return function(*args, **kwargs)

    return decorated_function


# ============================================================
# DATABASE
# ============================================================

def init_database():

    connection = sqlite3.connect(DATABASE)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS sos_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            people INTEGER NOT NULL,
            medical TEXT NOT NULL,
            children INTEGER NOT NULL,
            elderly INTEGER NOT NULL,
            latitude TEXT,
            longitude TEXT,
            situation TEXT,
            created_at TEXT NOT NULL
        )
    """)

    columns = connection.execute(
        "PRAGMA table_info(sos_requests)"
    ).fetchall()

    column_names = [
        column[1]
        for column in columns
    ]

    if "status" not in column_names:

        connection.execute("""
            ALTER TABLE sos_requests
            ADD COLUMN status TEXT DEFAULT 'NEW'
        """)

    connection.commit()
    connection.close()


# Initialize database when the application is imported by Gunicorn/Render
# and when it is run locally. CREATE TABLE IF NOT EXISTS makes this safe.
init_database()

# ============================================================
# LOAD RISK ZONES
# ============================================================

def load_risk_zones():

    risk_zones = []

    if not os.path.exists(RISK_FILE):
        return risk_zones

    with open(
        RISK_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            try:

                risk_zones.append({
                    "district": row["district"],
                    "latitude": float(row["latitude"]),
                    "longitude": float(row["longitude"]),
                    "risk_level": row["risk_level"],
                    "risk_score": float(row["risk_score"])
                })

            except (ValueError, KeyError):
                continue

    return risk_zones


# ============================================================
# LOAD SHELTERS
# ============================================================

def load_shelters():

    shelters = []

    if not os.path.exists(SHELTER_FILE):
        return shelters

    with open(
        SHELTER_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            try:

                capacity = int(row["capacity"])
                occupied = int(row["occupied"])

                available = max(
                    capacity - occupied,
                    0
                )

                shelters.append({
                    "id": int(row["id"]),
                    "name": row["name"],
                    "district": row["district"],
                    "latitude": float(row["latitude"]),
                    "longitude": float(row["longitude"]),
                    "capacity": capacity,
                    "occupied": occupied,
                    "available": available,
                    "status": row["status"]
                })

            except (ValueError, KeyError):
                continue

    return shelters


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return render_template("home.html")


# ============================================================
# SOS
# ============================================================

@app.route("/sos", methods=["GET", "POST"])
def sos():

    if request.method == "POST":

        name = request.form["name"]
        phone = request.form["phone"]
        people = int(request.form["people"])
        medical = request.form["medical"]
        children = int(request.form["children"])
        elderly = int(request.form["elderly"])

        latitude = request.form.get(
            "latitude",
            ""
        )

        longitude = request.form.get(
            "longitude",
            ""
        )

        situation = request.form["situation"]

        connection = sqlite3.connect(DATABASE)

        connection.execute("""
            INSERT INTO sos_requests
            (
                name,
                phone,
                people,
                medical,
                children,
                elderly,
                latitude,
                longitude,
                situation,
                created_at,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name,
            phone,
            people,
            medical,
            children,
            elderly,
            latitude,
            longitude,
            situation,
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "NEW"
        ))

        connection.commit()
        connection.close()

        return render_template(
            "success.html"
        )

    return render_template("sos.html")


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
def dashboard():

    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    requests = connection.execute("""
        SELECT *
        FROM sos_requests
        ORDER BY id DESC
    """).fetchall()

    total_requests = connection.execute("""
        SELECT COUNT(*)
        FROM sos_requests
    """).fetchone()[0]

    total_people = connection.execute("""
        SELECT COALESCE(SUM(people), 0)
        FROM sos_requests
    """).fetchone()[0]

    medical_cases = connection.execute("""
        SELECT COUNT(*)
        FROM sos_requests
        WHERE medical = 'Yes'
    """).fetchone()[0]

    connection.close()

    risk_zones = load_risk_zones()

    return render_template(
        "dashboard.html",
        requests=requests,
        total_requests=total_requests,
        total_people=total_people,
        medical_cases=medical_cases,
        risk_zones=risk_zones
    )


# ============================================================
# SOS API
# ============================================================

@app.route("/api/sos")
def api_sos():

    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    rows = connection.execute("""
        SELECT
            id,
            name,
            phone,
            people,
            medical,
            children,
            elderly,
            latitude,
            longitude,
            situation,
            created_at,
            status
        FROM sos_requests
        ORDER BY id DESC
    """).fetchall()

    connection.close()

    data = []

    for row in rows:

        data.append({
            "id": row["id"],
            "name": row["name"],
            "phone": row["phone"],
            "people": row["people"],
            "medical": row["medical"],
            "children": row["children"],
            "elderly": row["elderly"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "situation": row["situation"],
            "created_at": row["created_at"],
            "status": row["status"]
        })

    return jsonify(data)


# ============================================================
# RISK ZONE API
# ============================================================

@app.route("/api/risk-zones")
def api_risk_zones():

    return jsonify(load_risk_zones())


# ============================================================
# AI RISK PREDICTION
# ============================================================

@app.route("/api/ai-risk", methods=["POST"])
def api_ai_risk():

    try:

        data = request.get_json() or {}

        rainfall_mm = float(
            data["rainfall_mm"]
        )

        elevation_m = float(
            data["elevation_m"]
        )

        slope_degree = float(
            data["slope_degree"]
        )

        river_distance_km = float(
            data["river_distance_km"]
        )

        historical_risk = float(
            data["historical_risk"]
        )

        result = predict_risk(
            rainfall_mm,
            elevation_m,
            slope_degree,
            river_distance_km,
            historical_risk
        )

        return jsonify({
            "success": True,
            "risk_score": result["risk_score"],
            "risk_level": result["risk_level"]
        })

    except Exception as error:

        return jsonify({
            "success": False,
            "error": str(error)
        }), 400


# ============================================================
# AI EMERGENCY PRIORITY
# ============================================================

def calculate_priority(
    people,
    medical,
    children,
    elderly,
    risk_score,
    situation
):

    score = 0

    # Number of people
    if people >= 10:
        score += 25
    elif people >= 5:
        score += 20
    elif people >= 3:
        score += 15
    elif people >= 1:
        score += 10

    # Medical emergency
    if str(medical).strip().lower() == "yes":
        score += 25

    # Children
    score += min(
        max(children, 0) * 5,
        15
    )

    # Elderly
    score += min(
        max(elderly, 0) * 5,
        15
    )

    # Risk score
    if risk_score >= 75:
        score += 20
    elif risk_score >= 50:
        score += 15
    elif risk_score >= 30:
        score += 10
    else:
        score += 5

    # Dangerous situation words
    dangerous_words = [
        "trapped",
        "flood",
        "landslide",
        "injured",
        "critical",
        "danger",
        "dangerous",
        "building collapse"
    ]

    situation_text = str(
        situation
    ).lower()

    if any(
        word in situation_text
        for word in dangerous_words
    ):
        score += 10

    score = min(score, 100)

    if score >= 80:
        level = "CRITICAL"
    elif score >= 60:
        level = "HIGH"
    elif score >= 40:
        level = "MODERATE"
    else:
        level = "LOW"

    return score, level


@app.route("/api/priority", methods=["POST"])
def api_priority():

    try:

        data = request.get_json() or {}

        people = int(
            data.get("people", 0)
        )

        children = int(
            data.get("children", 0)
        )

        elderly = int(
            data.get("elderly", 0)
        )

        medical = data.get(
            "medical",
            "No"
        )

        risk_score = float(
            data.get("risk_score", 50)
        )

        situation = data.get(
            "situation",
            ""
        )

        score, level = calculate_priority(
            people,
            medical,
            children,
            elderly,
            risk_score,
            situation
        )

        return jsonify({
            "success": True,
            "priority_score": score,
            "priority": level
        })

    except Exception as error:

        return jsonify({
            "success": False,
            "error": str(error)
        }), 400


# ============================================================
# SHELTER API
# ============================================================

@app.route("/api/shelters")
def api_shelters():

    return jsonify(load_shelters())


# ============================================================
# HAVERSINE DISTANCE
# ============================================================

def haversine_distance(
    latitude1,
    longitude1,
    latitude2,
    longitude2
):

    earth_radius_km = 6371.0

    lat1 = math.radians(latitude1)
    lat2 = math.radians(latitude2)

    delta_lat = math.radians(
        latitude2 - latitude1
    )

    delta_lon = math.radians(
        longitude2 - longitude1
    )

    a = (
        math.sin(delta_lat / 2) ** 2
        +
        math.cos(lat1)
        * math.cos(lat2)
        * math.sin(delta_lon / 2) ** 2
    )

    c = 2 * math.asin(
        math.sqrt(a)
    )

    return earth_radius_km * c


# ============================================================
# NEAREST SHELTER
# ============================================================

@app.route(
    "/api/nearest-shelter",
    methods=["POST"]
)
def api_nearest_shelter():

    try:

        data = request.get_json() or {}

        latitude = float(
            data["latitude"]
        )

        longitude = float(
            data["longitude"]
        )

        shelters = load_shelters()

        available_shelters = [
            shelter
            for shelter in shelters
            if shelter["available"] > 0
            and str(
                shelter["status"]
            ).upper() != "FULL"
        ]

        if not available_shelters:

            return jsonify({
                "success": True,
                "found": False
            })

        nearest = None
        nearest_distance = float("inf")

        for shelter in available_shelters:

            distance = haversine_distance(
                latitude,
                longitude,
                shelter["latitude"],
                shelter["longitude"]
            )

            if distance < nearest_distance:

                nearest_distance = distance
                nearest = shelter

        nearest = dict(nearest)

        nearest["distance_km"] = round(
            nearest_distance,
            2
        )

        return jsonify({
            "success": True,
            "found": True,
            "shelter": nearest
        })

    except Exception as error:

        return jsonify({
            "success": False,
            "found": False,
            "error": str(error)
        }), 400


# ============================================================
# WEATHER DESCRIPTION
# ============================================================

def weather_description(weather_code):

    descriptions = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        56: "Light freezing drizzle",
        57: "Dense freezing drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        66: "Light freezing rain",
        67: "Heavy freezing rain",
        71: "Slight snow",
        73: "Moderate snow",
        75: "Heavy snow",
        77: "Snow grains",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        85: "Slight snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail"
    }

    try:
        code = int(weather_code)
    except (TypeError, ValueError):
        code = 0

    return descriptions.get(
        code,
        "Unknown conditions"
    )


# ============================================================
# LIVE WEATHER API
# ============================================================

@app.route("/api/weather", methods=["GET"])
def api_weather():

    try:

        latitude = float(
            request.args["latitude"]
        )

        longitude = float(
            request.args["longitude"]
        )

        if not (
            -90 <= latitude <= 90
            and
            -180 <= longitude <= 180
        ):

            return jsonify({
                "success": False,
                "error": "Invalid GPS coordinates."
            }), 400

        api_url = (
            "https://api.open-meteo.com/v1/forecast"
        )

        parameters = {
            "latitude": latitude,
            "longitude": longitude,
            "current": (
                "temperature_2m,"
                "relative_humidity_2m,"
                "precipitation,"
                "rain,"
                "wind_speed_10m,"
                "weather_code"
            ),
            "timezone": "auto"
        }

        response = requests.get(
            api_url,
            params=parameters,
            timeout=10
        )

        response.raise_for_status()

        weather_data = response.json()

        current = weather_data.get(
            "current"
        )

        if not current:

            return jsonify({
                "success": False,
                "error": "No current weather data returned."
            }), 502

        weather_code = current.get(
            "weather_code",
            0
        )

        return jsonify({

            "success": True,

            "latitude": latitude,

            "longitude": longitude,

            "temperature_c": current.get(
                "temperature_2m"
            ),

            "humidity_percent": current.get(
                "relative_humidity_2m"
            ),

            "rain_mm": current.get(
                "rain",
                current.get(
                    "precipitation",
                    0
                )
            ),

            "precipitation_mm": current.get(
                "precipitation",
                0
            ),

            "wind_kmh": current.get(
                "wind_speed_10m"
            ),

            "weather_code": weather_code,

            "condition": weather_description(
                weather_code
            ),

            "updated_at": current.get(
                "time",
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M"
                )
            )

        })

    except requests.RequestException:

        return jsonify({
            "success": False,
            "error": "Weather service could not be reached."
        }), 503

    except Exception as error:

        return jsonify({
            "success": False,
            "error": str(error)
        }), 400


# ============================================================
# WARNING API
# ============================================================

@app.route("/api/warnings")
def api_warnings():

    risk_zones = load_risk_zones()

    warnings = []

    for zone in risk_zones:

        score = float(
            zone.get(
                "risk_score",
                0
            )
        )

        if score >= 75:

            message = (
                "Critical prototype risk level. "
                "Close monitoring required."
            )

        elif score >= 50:

            message = (
                "High prototype risk level. "
                "Monitor conditions."
            )

        elif score >= 30:

            message = (
                "Moderate prototype risk level."
            )

        else:

            message = (
                "Low prototype risk level."
            )

        warnings.append({

            "district": zone["district"],

            "risk_score": score,

            "risk_level": zone["risk_level"],

            "message": message

        })

    warnings.sort(
        key=lambda item: item["risk_score"],
        reverse=True
    )

    return jsonify(warnings)


# ============================================================
# RESCUE TEAMS
# ============================================================

@app.route("/api/rescue-teams")
def api_rescue_teams():

    teams = [

        {
            "id": 1,
            "name": "Kollam Rescue Team",
            "district": "Kollam",
            "members": 8,
            "vehicle": "Rescue Vehicle",
            "status": "AVAILABLE",
            "assignment": "None"
        },

        {
            "id": 2,
            "name": "Alappuzha Rescue Team",
            "district": "Alappuzha",
            "members": 10,
            "vehicle": "Rescue Boat",
            "status": "AVAILABLE",
            "assignment": "None"
        },

        {
            "id": 3,
            "name": "Pathanamthitta Rescue Team",
            "district": "Pathanamthitta",
            "members": 7,
            "vehicle": "Rescue Vehicle",
            "status": "AVAILABLE",
            "assignment": "None"
        },

        {
            "id": 4,
            "name": "Idukki Mountain Rescue",
            "district": "Idukki",
            "members": 9,
            "vehicle": "4x4 Rescue Vehicle",
            "status": "AVAILABLE",
            "assignment": "None"
        },

        {
            "id": 5,
            "name": "Ernakulam Emergency Team",
            "district": "Ernakulam",
            "members": 12,
            "vehicle": "Emergency Vehicle",
            "status": "AVAILABLE",
            "assignment": "None"
        }

    ]

    return jsonify(teams)


# ============================================================
# ADMIN LOGIN
# ============================================================

@app.route(
    "/admin",
    methods=["GET", "POST"]
)
def admin_login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        )

        password = request.form.get(
            "password",
            ""
        )

        if (
            username == ADMIN_USERNAME
            and
            password == ADMIN_PASSWORD
        ):

            session["admin_logged_in"] = True

            return redirect(
                url_for("admin_dashboard")
            )

        return render_template(
            "admin_login.html",
            error="Invalid username or password."
        )

    return render_template(
        "admin_login.html"
    )


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():

    connection = sqlite3.connect(
        DATABASE
    )

    connection.row_factory = sqlite3.Row

    requests = connection.execute("""
        SELECT *
        FROM sos_requests
        ORDER BY id DESC
    """).fetchall()

    connection.close()

    return render_template(
        "admin_dashboard.html",
        requests=requests
    )


# ============================================================
# UPDATE SOS STATUS
# ============================================================

@app.route(
    "/admin/status/<int:request_id>/<status>",
    methods=["POST"]
)
@admin_required
def update_status(
    request_id,
    status
):

    allowed_statuses = [
        "NEW",
        "RESCUE UNDERWAY",
        "RESOLVED"
    ]

    if status not in allowed_statuses:

        return (
            "Invalid status",
            400
        )

    connection = sqlite3.connect(
        DATABASE
    )

    connection.execute("""
        UPDATE sos_requests
        SET status = ?
        WHERE id = ?
    """, (
        status,
        request_id
    ))

    connection.commit()
    connection.close()

    return redirect(
        url_for("admin_dashboard")
    )


# ============================================================
# DELETE SOS
# ============================================================

@app.route(
    "/admin/delete/<int:request_id>",
    methods=["POST"]
)
@admin_required
def delete_request(
    request_id
):

    connection = sqlite3.connect(
        DATABASE
    )

    connection.execute("""
        DELETE FROM sos_requests
        WHERE id = ?
    """, (
        request_id,
    ))

    connection.commit()
    connection.close()

    return redirect(
        url_for("admin_dashboard")
    )


# ============================================================
# ADMIN LOGOUT
# ============================================================

@app.route("/admin/logout")
def admin_logout():

    session.clear()

    return redirect(
        url_for("admin_login")
    )


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    print()
    print("========================================")
    print("        KERASURAKSHA")
    print("========================================")
    print()
    print("Server starting...")
    print()
    print("Dashboard:")
    print("http://127.0.0.1:5000/dashboard")
    print()
    print("SOS:")
    print("http://127.0.0.1:5000/sos")
    print()
    print("Admin:")
    print("http://127.0.0.1:5000/admin")
    print()
    print("Weather:")
    print("Open-Meteo weather enabled")
    print()
    print("========================================")
    print()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )