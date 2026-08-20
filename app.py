import os
from datetime import date
from pathlib import Path
from uuid import uuid4

from flask import Flask, jsonify, request, send_from_directory
from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename

import database
from services.disease_analyzer import get_analyzer
from services.lifecycle import days_since, estimate_growth_stage
from services.weather import get_weather_summary


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = Path(os.getenv("AGRISHIELD_UPLOAD_DIR", BASE_DIR / "uploads"))
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

UPLOAD_DIR.mkdir(exist_ok=True)
database.init_db()

app = Flask(__name__, static_folder="dist", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


def error_response(message, status=400):
    return jsonify({"error": message}), status


def required_text(payload, key, label):
    value = str(payload.get(key, "")).strip()
    if not value:
        raise ValueError(f"{label} is required.")
    return value


def save_upload(file_storage, prefix):
    if file_storage is None or not file_storage.filename:
        raise ValueError("Please upload an image.")

    original = secure_filename(file_storage.filename)
    suffix = Path(original).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError("Please upload a JPG, PNG, or WEBP image.")

    filename = f"{prefix}-{uuid4().hex}{suffix}"
    destination = UPLOAD_DIR / filename
    file_storage.save(destination)

    try:
        with Image.open(destination) as image:
            image.verify()
    except (UnidentifiedImageError, OSError):
        destination.unlink(missing_ok=True)
        raise ValueError("The uploaded file is not a readable crop image.")

    return str(destination)


def pending_diagnosis(crop_name, description=""):
    evidence = [
        f"Crop entered by farmer: {crop_name}.",
        "Image saved for later disease-model analysis.",
        "No disease model was used for this first functional build.",
    ]
    if description.strip():
        evidence.append(f"Farmer observation saved: {description.strip()}")

    return {
        "crop_name": crop_name,
        "diagnosis": "Pending disease model diagnosis",
        "diagnosis_status": "pending_model",
        "reliability": "Not assessed",
        "model_confidence": None,
        "severity": "Unknown",
        "health_status": "Pending diagnosis",
        "health_score": None,
        "evidence": evidence,
        "possible_causes": [
            "Disease, pest damage, nutrient stress, water stress, or physical injury can be reviewed when the model layer is connected."
        ],
        "recommendations": [
            "Keep monitoring the crop and add clear close-up scans of affected parts.",
            "Compare future scans from the same plant or row for visible progression.",
        ],
        "precautions": [
            "Use clean tools when touching affected plants.",
            "Avoid wetting leaves unnecessarily while symptoms are unknown.",
        ],
        "do_not": [
            "Do not treat this placeholder as a confirmed disease diagnosis.",
            "Do not apply pesticide or fertilizer only from this pending result.",
        ],
        "next_check": [
            "Capture a close-up of the affected leaf or plant part.",
            "Capture a wider photo showing where the symptom appears on the crop.",
        ],
        "follow_up": "Add another scan after visible change or within 2 to 3 days if symptoms continue.",
        "model_label": "",
        "model_note": "Disease model integration intentionally disabled for this phase.",
    }


def request_coordinates(source):
    latitude = source.get("latitude")
    longitude = source.get("longitude")
    if latitude in (None, "") or longitude in (None, ""):
        return None, None
    try:
        return float(latitude), float(longitude)
    except ValueError:
        return None, None


def enrich_with_weather(analysis, latitude=None, longitude=None):
    if latitude is None or longitude is None:
        return analysis

    weather = get_weather_summary(latitude, longitude)
    result = {**analysis, "weather": weather}
    evidence = list(result.get("evidence") or [])
    precautions = list(result.get("precautions") or [])
    recommendations = list(result.get("recommendations") or [])

    if weather.get("available"):
        evidence.append(
            "Weather monitor: "
            f"{weather['temperature_c']} C, {weather['humidity_percent']}% humidity, "
            f"{weather['rain_probability_percent']}% rain chance."
        )
        if weather.get("risk_level") in {"Watch", "Elevated"}:
            precautions.append(weather["advisory"])
            recommendations.append("Use the weather risk with the image result before choosing spray, fertilizer, or natural treatment timing.")
    else:
        evidence.append(weather["advisory"])

    return {
        **result,
        "evidence": evidence,
        "precautions": precautions,
        "recommendations": recommendations,
    }


def analyze_image(image_path, crop_name, description, latitude=None, longitude=None):
    analysis = get_analyzer().analyze(image_path, crop_name, description)
    return enrich_with_weather(analysis, latitude, longitude)


def health_trend(scans):
    if len(scans) < 2:
        return "Insufficient data"

    scores = [scan.get("health_score") for scan in scans if scan.get("health_score") is not None]
    if len(scores) < 2:
        return "Awaiting diagnosis"

    delta = scores[-1] - scores[-2]
    if delta > 4:
        return "Improving"
    if delta < -4:
        return "Worsening"
    return "Stable"


def scan_day(crop, scan):
    return days_since(crop["planting_date"], scan["scan_date"]) + 1


def crop_with_summary(crop):
    scans = sorted(
        database.list_scans(crop["id"]),
        key=lambda item: (item["scan_date"], item["id"]),
    )
    lifecycle = estimate_growth_stage(crop["crop_name"], crop["planting_date"])
    latest = scans[-1] if scans else None

    return {
        **crop,
        "days_since_planting": lifecycle["days_since_planting"],
        "growth_stage": lifecycle["growth_stage"],
        "growth_stage_label": lifecycle["label"],
        "scan_count": len(scans),
        "latest_health_status": latest["health_status"] if latest else "No scans yet",
        "last_scan_date": latest["scan_date"] if latest else "",
        "health_trend": health_trend(scans),
        "latest_scan": latest,
    }


def crop_detail(crop):
    scans = sorted(
        database.list_scans(crop["id"]),
        key=lambda item: (item["scan_date"], item["id"]),
    )
    enriched_scans = [
        {
            **scan,
            "day_number": scan_day(crop, scan),
            "can_compare": index > 0,
        }
        for index, scan in enumerate(scans)
    ]
    return {
        **crop_with_summary(crop),
        "scans": enriched_scans,
    }


@app.route("/api/health", methods=["GET"])
def api_health():
    return jsonify({"ok": True, "database": str(database.DB_PATH), "uploads": str(UPLOAD_DIR)})


@app.route("/api/weather", methods=["GET"])
def api_weather():
    latitude, longitude = request_coordinates(request.args)
    if latitude is None or longitude is None:
        return error_response("Latitude and longitude are required.")
    return jsonify({"weather": get_weather_summary(latitude, longitude)})


@app.route("/api/dashboard", methods=["GET"])
def dashboard():
    crops = [crop_with_summary(crop) for crop in database.list_crops()]
    scans = sorted(database.list_scans(), key=lambda item: item["created_at"], reverse=True)
    latest_scan = scans[0] if scans else None
    recent_activity = []

    for crop in crops[:4]:
        recent_activity.append(
            {
                "type": "crop",
                "title": f"{crop['crop_name']} profile active",
                "detail": crop["field_name"],
                "date": crop["created_at"],
            }
        )
    for scan in scans[:4]:
        recent_activity.append(
            {
                "type": "scan",
                "title": f"{scan['crop_name']} scan recorded",
                "detail": scan["health_status"],
                "date": scan["created_at"],
            }
        )

    recent_activity.sort(key=lambda item: item["date"], reverse=True)
    return jsonify(
        {
            "summary": {
                "active_crops": len(crops),
                "latest_health": latest_scan["health_status"] if latest_scan else "No scans yet",
                "scans_recorded": len(scans),
            },
            "crops": crops,
            "recent_activity": recent_activity[:6],
        }
    )


@app.route("/api/crops", methods=["GET", "POST", "OPTIONS"])
def crops():
    if request.method == "OPTIONS":
        return ("", 204)
    if request.method == "GET":
        return jsonify({"crops": [crop_with_summary(crop) for crop in database.list_crops()]})

    payload = request.get_json(silent=True) or {}
    try:
        crop = database.create_crop(
            {
                "crop_name": required_text(payload, "crop_name", "Crop name"),
                "field_name": required_text(payload, "field_name", "Field name"),
                "planting_date": required_text(payload, "planting_date", "Planting date"),
                "location": str(payload.get("location", "")).strip(),
                "notes": str(payload.get("notes", "")).strip(),
            }
        )
    except ValueError as error:
        return error_response(str(error))
    except Exception:
        return error_response("Could not create crop profile.", 500)

    return jsonify({"crop": crop_with_summary(crop)}), 201


@app.route("/api/crops/<int:crop_id>", methods=["GET"])
def get_crop(crop_id):
    crop = database.get_crop(crop_id)
    if not crop:
        return error_response("Crop profile not found.", 404)
    return jsonify({"crop": crop_detail(crop)})


@app.route("/api/crops/<int:crop_id>/scans", methods=["POST", "OPTIONS"])
def add_scan(crop_id):
    if request.method == "OPTIONS":
        return ("", 204)

    crop = database.get_crop(crop_id)
    if not crop:
        return error_response("Crop profile not found.", 404)

    try:
        scan_date = request.form.get("scan_date") or date.today().isoformat()
        description = request.form.get("description", "").strip()
        latitude, longitude = request_coordinates(request.form)
        image_path = save_upload(request.files.get("image"), f"crop-{crop_id}-scan")
        lifecycle = estimate_growth_stage(crop["crop_name"], crop["planting_date"], scan_date)
        scan = database.create_scan(
            crop_id=crop_id,
            image_path=image_path,
            scan_date=scan_date,
            description=description,
            growth_stage=lifecycle["growth_stage"],
            diagnosis=analyze_image(image_path, crop["crop_name"], description, latitude, longitude),
        )
    except ValueError as error:
        return error_response(str(error))
    except Exception:
        return error_response("Could not save the scan. Please try again.", 500)

    scan["day_number"] = scan_day(crop, scan)
    previous = database.get_previous_scan(crop_id, scan["id"])
    scan["compare_ready"] = previous is not None
    return jsonify({"scan": scan, "crop": crop_detail(crop)}), 201


@app.route("/api/quick-diagnosis", methods=["POST", "OPTIONS"])
def quick_diagnosis():
    if request.method == "OPTIONS":
        return ("", 204)

    crop_name = request.form.get("crop_name", "").strip()
    if not crop_name:
        return error_response("Crop name is required.")

    try:
        description = request.form.get("description", "").strip()
        latitude, longitude = request_coordinates(request.form)
        image_path = save_upload(request.files.get("image"), "quick")
        record = database.create_quick_diagnosis(crop_name, image_path, description)
        analysis = analyze_image(image_path, crop_name, description, latitude, longitude)
    except ValueError as error:
        return error_response(str(error))
    except Exception:
        return error_response("Could not save this quick diagnosis image.", 500)

    return jsonify(
        {
            "quick_diagnosis": {
                **record,
                **analysis,
            }
        }
    ), 201


@app.route("/api/scans/<int:scan_id>/compare", methods=["GET"])
def compare_scan(scan_id):
    scan = database.get_scan(scan_id)
    if not scan:
        return error_response("Scan not found.", 404)
    crop = database.get_crop(scan["crop_id"])
    previous = database.get_previous_scan(scan["crop_id"], scan_id)

    if not previous:
        trend = "Insufficient data"
        explanation = "There is no previous scan for this crop yet."
    elif scan.get("health_score") is None or previous.get("health_score") is None:
        trend = "Insufficient data"
        explanation = "Diagnosis results are pending, so progression cannot be assessed reliably yet."
    else:
        delta = scan["health_score"] - previous["health_score"]
        trend = "Improving" if delta > 4 else "Worsening" if delta < -4 else "Stable"
        explanation = "This comparison is based on stored health scores from consecutive scans."

    return jsonify(
        {
            "crop": crop_with_summary(crop),
            "previous_scan": previous,
            "current_scan": scan,
            "health_trend": trend,
            "explanation": explanation,
        }
    )


@app.route("/uploads/<path:filename>", methods=["GET"])
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    dist_path = BASE_DIR / "dist"
    requested = dist_path / path
    if path and requested.exists():
        return send_from_directory(dist_path, path)
    index_path = dist_path / "index.html"
    if index_path.exists():
        return send_from_directory(dist_path, "index.html")
    return jsonify(
        {
            "message": "AgriShield API is running. Start the frontend with npm run dev.",
            "api": "/api/health",
        }
    )


if __name__ == "__main__":
    if __name__ == "__main__":
     import os

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        debug=False
    )