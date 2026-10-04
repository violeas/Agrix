import os
import math
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
from services.monsoon.forecast import generate_forecast, sowing_decision
from services.monsoon.providers import search_locations, reverse_geocode, current_climate_drivers
from services.monsoon.decision import build_alerts, crop_advisories, explain_forecast, sowing_window_assessment
from models.monsoon.training import forecast_with_model_run
from data.climate.boundaries import resolve_boundary


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = Path(os.getenv("AGRISHIELD_UPLOAD_DIR", BASE_DIR / "uploads"))
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
database.init_db()

app = Flask(__name__, static_folder="dist", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024
app.config["JSON_SORT_KEYS"] = False

ALLOWED_ORIGIN = os.getenv("AGRISHIELD_ALLOWED_ORIGIN", "").strip()


@app.after_request
def add_cors_headers(response):
    if ALLOWED_ORIGIN:
        response.headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGIN
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
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
        parsed_latitude, parsed_longitude = float(latitude), float(longitude)
        if (not math.isfinite(parsed_latitude) or not math.isfinite(parsed_longitude)
                or not -90 <= parsed_latitude <= 90 or not -180 <= parsed_longitude <= 180):
            return None, None
        return parsed_latitude, parsed_longitude
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
    calendar = database.get_crop_calendar_rule(crop.get("location_id"), crop["crop_name"])
    lifecycle = estimate_growth_stage(crop["crop_name"], crop["planting_date"],
                                      calendar_rules=(calendar or {}).get("lifecycle_stages"))
    latest = scans[-1] if scans else None

    return {
        **crop,
        "days_since_planting": lifecycle["days_since_planting"],
        "growth_stage": lifecycle["growth_stage"],
        "next_stage": lifecycle["next_stage"],
        "days_to_next_stage": lifecycle["days_to_next_stage"],
        "lifecycle_source": lifecycle["lifecycle_source"],
        "lifecycle_available": lifecycle["lifecycle_available"],
        "scan_count": len(scans),
        "latest_health_status": latest["health_status"] if latest else "No scans yet",
        "last_scan_date": latest["scan_date"] if latest else "",
        "health_trend": health_trend(scans),
        "latest_scan": latest,
        "crop_calendar": ({"source": calendar["source"], "version": calendar.get("version"),
                           "sowing_start": calendar.get("sowing_start"), "sowing_end": calendar.get("sowing_end"),
                           "water_requirement_mm_day": calendar.get("water_requirement_mm_day")}
                          if calendar else None),
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


def active_location():
    return database.get_setting("active_location")


def with_boundary_metadata(location):
    if not location or location.get("latitude") is None or location.get("longitude") is None:
        return location
    boundary_path = os.getenv("AGRISHIELD_BOUNDARY_GEOJSON")
    if not boundary_path:
        return location
    try:
        boundary = resolve_boundary(location["latitude"], location["longitude"], boundary_path)
    except (OSError, ValueError, TypeError):
        return location
    if not boundary:
        return location
    enriched = {**location, **{key: value for key, value in boundary.items() if key != "boundary_source"}}
    if boundary.get("village_cluster"):
        enriched["village"] = boundary["village_cluster"]
    enriched["boundary_source"] = "Configured authoritative GeoJSON"
    enriched["admin_level_available"] = boundary.get("boundary_level", "coordinates")
    return enriched


def selected_location_id(source=None, location=None, crop=None):
    if source is not None:
        value = source.get("location_id")
        if value:
            return str(value).strip()
    for item in (crop, location):
        if item and item.get("location_id"):
            return str(item["location_id"]).strip()
    return None


def forecast_for_request(source=None, crop=None):
    source = source or request.args
    latitude, longitude = request_coordinates(source)
    coordinate_supplied = source.get("latitude") not in (None, "") or source.get("longitude") not in (None, "")
    invalid_coordinates = coordinate_supplied and (latitude is None or longitude is None)
    location = None if invalid_coordinates else active_location()
    requested_coordinates = latitude is not None and longitude is not None
    if (not invalid_coordinates and (latitude is None or longitude is None)
            and crop and crop.get("latitude") is not None and crop.get("longitude") is not None):
        latitude, longitude = crop["latitude"], crop["longitude"]
        location = {**(location or {}), **crop}
    if not invalid_coordinates and (latitude is None or longitude is None):
        latitude = (location or {}).get("latitude")
        longitude = (location or {}).get("longitude")
    def coordinates_match(item):
        if not item or item.get("latitude") is None or item.get("longitude") is None:
            return False
        try:
            return (abs(float(item["latitude"]) - float(latitude)) < 0.00001 and
                    abs(float(item["longitude"]) - float(longitude)) < 0.00001)
        except (TypeError, ValueError):
            return False

    crop_matches = coordinates_match(crop)
    active_matches = coordinates_match(location)
    if latitude is not None and longitude is not None:
        matched_location = crop if crop_matches else location if active_matches else None
        if matched_location:
            location = {**(location or {}), **matched_location,
                        "latitude": float(latitude), "longitude": float(longitude)}
        else:
            location = {"latitude": float(latitude), "longitude": float(longitude),
                        "label": "Selected coordinates", "admin_level_available": "coordinates"}
        location = with_boundary_metadata(location)
    forecast = generate_forecast(latitude, longitude, crop, location)
    if invalid_coordinates:
        location_id = None
    elif requested_coordinates:
        location_id = (crop.get("location_id") if crop_matches else
                       (active_location() or {}).get("location_id") if active_matches else None)
    else:
        location_id = selected_location_id(source, location, crop)
    run = database.latest_validated_model_run(location_id) if location_id else None
    local_rows = database.get_climate_observations(location_id, limit=90) if run else []
    if run:
        model_horizons = forecast_with_model_run(local_rows, run)
        forecast["agri_model"] = {"available": any(item["available"] for item in model_horizons.values()),
                                  "model_version": run["model_version"], "validated": run["validated"],
                                  "horizons": model_horizons, "data_timestamp": run["data_timestamp"]}
    else:
        forecast["agri_model"] = {"available": False, "validated": False, "model_version": None,
                                  "horizons": {}, "reason": "No validated AgriShield model is trained for this exact location. Provider guidance remains separate."}
    try:
        horizon = int(source.get("horizon_days", 14))
    except (TypeError, ValueError):
        horizon = 14
    forecast["explanation"] = explain_forecast(forecast, horizon if horizon in (7, 14, 21, 30) else 14)
    forecast["data_transparency"] = {
        "data_source": (forecast.get("source") or {}).get("name"),
        "observation_timestamp": (forecast.get("recent_rainfall") or {}).get("last_observation_date"),
        "forecast_timestamp": (forecast.get("source") or {}).get("generated_at"),
        "forecast_horizon_days": (forecast.get("explanation") or {}).get("horizon_days"),
        "location": forecast.get("location"),
        "model_version": (forecast.get("agri_model") or {}).get("model_version"),
        "validated": bool((forecast.get("agri_model") or {}).get("validated")),
        "provider_output_is_agri_ml": False,
    }
    forecast["advisory_details"] = crop_advisories(forecast, crop)
    return forecast


def parse_crop_payload(payload, existing=None):
    existing = existing or {}
    crop_name = required_text(payload, "crop_name", "Crop name")
    field_name = required_text(payload, "field_name", "Field name")
    planting_date = required_text(payload, "planting_date", "Sowing date")
    try:
        planting_date = date.fromisoformat(planting_date[:10]).isoformat()
    except ValueError as error:
        raise ValueError("Enter a valid sowing date.") from error
    area = payload.get("field_area", existing.get("field_area"))
    try:
        area = float(area)
        if not math.isfinite(area) or area <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("Field area must be a positive number.")
    irrigation_type = str(payload.get("irrigation_type", existing.get("irrigation_type", ""))).strip()
    if irrigation_type not in {"rainfed", "canal", "drip", "sprinkler", "borewell", "other"}:
        raise ValueError("Choose an irrigation type.")
    location = active_location() or {}
    latitude = payload.get("latitude", existing.get("latitude", location.get("latitude")))
    longitude = payload.get("longitude", existing.get("longitude", location.get("longitude")))
    try:
        latitude, longitude = float(latitude), float(longitude)
        if not math.isfinite(latitude) or not math.isfinite(longitude) or not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("Set a real field location using GPS or location search before saving this crop.")
    return {
        "crop_name": crop_name, "field_name": field_name, "planting_date": planting_date,
        "location": str(payload.get("location", existing.get("location", location.get("label", "")))).strip(),
        "latitude": latitude, "longitude": longitude,
        "state": payload.get("state", existing.get("state", location.get("state"))),
        "district": payload.get("district", existing.get("district", location.get("district"))),
        "block": payload.get("block", existing.get("block", location.get("block"))),
        "village_cluster": payload.get("village_cluster", existing.get("village_cluster", location.get("village_cluster") or location.get("village"))),
        "field_area": area,
        "field_area_unit": str(payload.get("field_area_unit", existing.get("field_area_unit", "acre"))).strip() or "acre",
        "irrigation_type": irrigation_type,
        "status": "planned" if planting_date > date.today().isoformat() else "active",
        "location_id": payload.get("location_id", existing.get("location_id", location.get("location_id"))),
        "notes": str(payload.get("notes", existing.get("notes", ""))).strip(),
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


@app.route("/api/location", methods=["GET", "POST", "OPTIONS"])
def api_location():
    if request.method == "OPTIONS":
        return ("", 204)
    if request.method == "GET":
        return jsonify({"location": active_location()})
    payload = request.get_json(silent=True) or {}
    try:
        latitude = float(payload.get("latitude"))
        longitude = float(payload.get("longitude"))
        if not math.isfinite(latitude) or not math.isfinite(longitude) or not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
            raise ValueError
    except (TypeError, ValueError):
        return error_response("A valid latitude and longitude are required.")
    location = {
        "label": str(payload.get("label") or "Selected map location").strip()[:180],
        "latitude": latitude, "longitude": longitude,
        "village": str(payload.get("village") or "").strip() or None,
        "village_cluster": str(payload.get("village_cluster") or "").strip() or None,
        "block": str(payload.get("block") or "").strip() or None,
        "district": str(payload.get("district") or "").strip() or None,
        "state": str(payload.get("state") or "").strip() or None,
        "country": str(payload.get("country") or "").strip() or None,
        "admin_level_available": str(payload.get("admin_level_available") or "coordinates"),
        "location_id": str(payload.get("location_id") or "").strip() or None,
        "boundary_id": str(payload.get("boundary_id") or "").strip() or None,
        "boundary_level": str(payload.get("boundary_level") or "").strip() or None,
        "boundary_source": str(payload.get("boundary_source") or "").strip() or None,
        "source": str(payload.get("source") or "User-selected coordinates"),
        "status": str(payload.get("status") or "Location selected"),
    }
    database.set_setting("active_location", location)
    return jsonify({"location": location}), 200


@app.route("/api/location/search", methods=["GET"])
def api_location_search():
    query = request.args.get("q", "").strip()
    if len(query) < 2:
        return error_response("Enter at least two characters to search locations.")
    try:
        return jsonify({"results": [with_boundary_metadata(result) for result in search_locations(query)]})
    except Exception:
        return jsonify({"error": "Location search is unavailable. Try coordinates or use your device location."}), 503


@app.route("/api/location/reverse", methods=["GET"])
def api_location_reverse():
    latitude, longitude = request_coordinates(request.args)
    if latitude is None or longitude is None or not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
        return error_response("A valid latitude and longitude are required.")
    try:
        location = reverse_geocode(round(latitude, 5), round(longitude, 5))
        return jsonify({"location": with_boundary_metadata(location)})
    except Exception:
        return jsonify({"error": "Address lookup is unavailable; location remains at coordinate level."}), 503


@app.route("/api/monsoon/forecast", methods=["GET"])
@app.route("/api/monsoon/outlook", methods=["GET"])
def api_monsoon_forecast():
    crop = None
    crop_id = request.args.get("crop_id")
    if crop_id:
        try:
            crop_record = database.get_crop(int(crop_id))
        except (TypeError, ValueError):
            crop_record = None
        if crop_record is None:
            return error_response("Crop profile was not found.", 404)
        crop = crop_with_summary(crop_record)
    return jsonify({"forecast": forecast_for_request(request.args, crop)})


@app.route("/api/monsoon/events", methods=["GET"])
def api_monsoon_events():
    forecast = forecast_for_request(request.args)
    return jsonify({"events": forecast.get("events"), "available": forecast.get("available"), "data_status": forecast.get("data_status")})


@app.route("/api/monsoon/risk-map", methods=["GET"])
def api_monsoon_risk_map():
    forecast = forecast_for_request(request.args)
    boundary_match = bool((forecast.get("location") or {}).get("boundary_id"))
    return jsonify({"location": forecast.get("location"), "daily": forecast.get("daily", []),
                    "events": forecast.get("events"), "boundaries_available": boundary_match,
                    "boundary_match": boundary_match,
                    "spatial_resolution": "selected weather grid point; no area aggregation",
                    "boundary_status": "An administrative boundary identifies this point, but risk values remain grid-point guidance." if boundary_match else "Administrative boundary data is not connected. The map shows the selected weather grid point only."})


@app.route("/api/monsoon/sowing-decision", methods=["POST", "OPTIONS"])
def api_sowing_decision():
    if request.method == "OPTIONS":
        return ("", 204)
    payload = request.get_json(silent=True) or {}
    forecast = forecast_for_request(payload)
    try:
        horizon = int(payload.get("horizon_days", 14))
    except (TypeError, ValueError):
        horizon = 0
    if horizon not in (7, 14, 21, 30):
        return error_response("Forecast horizon must be 7, 14, 21 or 30 days.")
    crop_name = str(payload.get("crop_name") or "").strip()[:80]
    if not crop_name:
        return error_response("Choose a crop before reviewing sowing conditions.")
    result = sowing_decision(forecast, crop_name, bool(payload.get("irrigation_available")), horizon,
                             str(payload.get("crop_stage") or "")[:100],
                             str(payload.get("sowing_preference") or "")[:100])
    return jsonify({"decision": result, "data_status": forecast.get("data_status")})


@app.route("/api/monsoon/advisory", methods=["GET"])
def api_monsoon_advisory():
    crop = None
    crop_id = request.args.get("crop_id")
    if crop_id:
        try:
            record = database.get_crop(int(crop_id))
        except (TypeError, ValueError):
            record = None
        if record is None:
            return error_response("Crop profile was not found.", 404)
        crop = crop_with_summary(record)
    forecast = forecast_for_request(request.args, crop)
    return jsonify({"advisory": forecast.get("advisory", []),
                    "advisory_details": forecast.get("advisory_details", []),
                    "available": forecast.get("available"), "data_status": forecast.get("data_status"),
                    "events": forecast.get("events")})


@app.route("/api/climate", methods=["GET"])
def api_climate():
    return jsonify(current_climate_drivers())


@app.route("/api/monsoon/model-performance", methods=["GET"])
def api_model_performance():
    location_id = request.args.get("location_id") or selected_location_id(request.args, active_location())
    runs = database.list_model_runs(location_id) if location_id else []
    public_runs = []
    for run in runs:
        public_runs.append({**run, "models": None, "model_count": len(run.get("models") or {})})
    return jsonify({"location_id": location_id, "runs": public_runs,
                    "available": any(run.get("validated") for run in public_runs),
                    "status": "Metrics are from chronological held-out data." if public_runs else
                    "No local model has been trained. Metrics are not available and have not been invented."})


@app.route("/api/monsoon/sowing-window", methods=["GET", "POST", "OPTIONS"])
def api_sowing_window():
    if request.method == "OPTIONS":
        return ("", 204)
    payload = request.get_json(silent=True) if request.method == "POST" else request.args
    payload = payload or {}
    crop_name = str(payload.get("crop_name") or "").strip()
    if not crop_name:
        return error_response("Choose a crop to assess a sowing window.")
    crop = None
    crop_id = payload.get("crop_id")
    if crop_id:
        try:
            crop_record = database.get_crop(int(crop_id))
        except (TypeError, ValueError):
            crop_record = None
        if crop_record is None:
            return error_response("Crop profile was not found.", 404)
        crop = crop_with_summary(crop_record)
        crop_name = crop_record["crop_name"]
    forecast = forecast_for_request(payload, crop)
    result = sowing_window_assessment(crop_name, forecast, crop)
    return jsonify({"assessment": result, "data_transparency": forecast.get("data_transparency")})


@app.route("/api/monsoon/alerts", methods=["GET"])
def api_monsoon_alerts():
    location = active_location()
    location_id = selected_location_id(request.args, location) or ""
    latitude, longitude = request_coordinates(request.args)
    if latitude is None or longitude is None:
        latitude = (location or {}).get("latitude")
        longitude = (location or {}).get("longitude")
    if latitude is None or longitude is None:
        return jsonify({"alerts": [], "available": False,
                        "status": "Set a location to check weather-based in-app advisories."})
    horizon = request.args.get("horizon_days", 14, type=int)
    if horizon not in (7, 14, 21, 30):
        return error_response("Forecast horizon must be 7, 14, 21 or 30 days.")
    location_id = location_id or f"grid:{round(float(latitude), 3)}:{round(float(longitude), 3)}"
    forecast = forecast_for_request({"latitude": latitude, "longitude": longitude,
                                     "location_id": location_id, "horizon_days": horizon})
    alerts = build_alerts(forecast, location_id, horizon)
    saved = database.upsert_monsoon_alerts(location_id, alerts) if alerts else database.list_monsoon_alerts(location_id)
    return jsonify({"alerts": saved, "available": forecast.get("available"),
                    "status": "Threshold advisories from raw weather-provider ensemble signals; not official warnings."})


@app.route("/api/monsoon/alerts/<int:alert_id>/acknowledge", methods=["POST", "OPTIONS"])
def acknowledge_monsoon_alert(alert_id):
    if request.method == "OPTIONS":
        return ("", 204)
    if not database.acknowledge_monsoon_alert(alert_id):
        return error_response("Active alert was not found.", 404)
    return jsonify({"ok": True, "id": alert_id, "status": "acknowledged"})


@app.route("/api/languages", methods=["GET"])
def api_languages():
    return jsonify({"languages": [
        {"code": "en", "label": "English"}, {"code": "hi", "label": "Hindi"},
        {"code": "te", "label": "Telugu"}, {"code": "ta", "label": "Tamil"},
        {"code": "kn", "label": "Kannada"}, {"code": "mr", "label": "Marathi"},
    ]})


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
                "active_crops": sum(1 for crop in crops if crop.get("status") == "active"),
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
        crop = database.create_crop(parse_crop_payload(payload))
    except ValueError as error:
        return error_response(str(error))
    except Exception:
        return error_response("Could not create crop profile.", 500)

    return jsonify({"crop": crop_with_summary(crop)}), 201


@app.route("/api/crops/<int:crop_id>", methods=["GET", "PUT", "DELETE", "OPTIONS"])
def get_crop(crop_id):
    if request.method == "OPTIONS":
        return ("", 204)
    crop = database.get_crop(crop_id)
    if not crop or crop.get("status") not in {"active", "planned"}:
        return error_response("Crop profile not found.", 404)
    if request.method == "DELETE":
        if not database.archive_crop(crop_id):
            return error_response("Crop profile could not be archived.", 404)
        return jsonify({"ok": True, "status": "archived", "crop_id": crop_id})
    if request.method == "PUT":
        payload = request.get_json(silent=True) or {}
        try:
            updated = database.update_crop(crop_id, parse_crop_payload(payload, crop))
        except ValueError as error:
            return error_response(str(error))
        except Exception:
            return error_response("Could not update crop profile.", 500)
        if not updated:
            return error_response("Crop profile was not found.", 404)
        return jsonify({"crop": crop_with_summary(updated)})
    return jsonify({"crop": crop_detail(crop)})


@app.route("/api/crop-timeline", methods=["GET"])
def api_crop_timeline():
    crop_id = request.args.get("crop_id", "")
    try:
        crop = database.get_crop(int(crop_id))
    except (TypeError, ValueError):
        crop = None
    if crop is None or crop.get("status") not in {"active", "planned"}:
        return error_response("A valid crop_id is required.")
    return jsonify({"crop": crop_detail(crop)})


@app.route("/api/crops/<int:crop_id>/scans", methods=["POST", "OPTIONS"])
def add_scan(crop_id):
    if request.method == "OPTIONS":
        return ("", 204)

    crop = database.get_crop(crop_id)
    if not crop or crop.get("status") != "active":
        return error_response("Crop profile not found.", 404)

    try:
        scan_date = request.form.get("scan_date") or date.today().isoformat()
        description = request.form.get("description", "").strip()
        latitude, longitude = request_coordinates(request.form)
        image_path = save_upload(request.files.get("image"), f"crop-{crop_id}-scan")
        calendar = database.get_crop_calendar_rule(crop.get("location_id"), crop["crop_name"])
        lifecycle = estimate_growth_stage(crop["crop_name"], crop["planting_date"], scan_date,
                                          calendar_rules=(calendar or {}).get("lifecycle_stages"))
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
@app.route("/api/disease/analyze", methods=["POST", "OPTIONS"])
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
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        debug=False
    )
