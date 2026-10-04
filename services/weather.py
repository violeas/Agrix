import json
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import os


def _risk_level(humidity, rain_probability, precipitation):
    if humidity >= 78 or rain_probability >= 55 or (precipitation is not None and precipitation >= 0.5):
        return "Elevated"
    if humidity >= 65 or rain_probability >= 35:
        return "Watch"
    return "Low"


def _advisory(risk_level):
    if risk_level == "Elevated":
        return "High humidity or rain can increase fungal disease pressure. Avoid leaf-wetting irrigation, delay spraying during rain, and check lower leaves closely."
    if risk_level == "Watch":
        return "Weather is moderately favorable for disease spread. Keep leaves dry where possible and repeat scans after rain or heavy dew."
    return "Current weather risk is low. Continue normal monitoring and keep the crop canopy well ventilated."


def get_weather_summary(latitude, longitude):
    params = urlencode(
        {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,surface_pressure",
            "daily": "precipitation_probability_max",
            "forecast_days": 1,
            "timezone": "auto",
        }
    )
    url = f"https://api.open-meteo.com/v1/forecast?{params}"

    try:
        req = Request(url, headers={"User-Agent": os.getenv("AGRISHIELD_USER_AGENT", "AgriShield/1.0")})
        with urlopen(req, timeout=float(os.getenv("AGRISHIELD_PROVIDER_TIMEOUT", "8"))) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, TimeoutError, json.JSONDecodeError):
        return {
            "available": False,
            "risk_level": "Unavailable",
            "advisory": "Weather monitoring could not be reached right now.",
        }

    current = payload.get("current") or {}
    daily = payload.get("daily") or {}
    humidity_raw = current.get("relative_humidity_2m")
    rain_values = daily.get("precipitation_probability_max") or []
    temperature_raw = current.get("temperature_2m")
    precipitation_raw = current.get("precipitation")
    if humidity_raw is None or temperature_raw is None or not rain_values or rain_values[0] is None:
        return {"available": False, "risk_level": "Unavailable",
                "advisory": "Weather data was incomplete; no weather assessment was generated."}
    humidity = float(humidity_raw)
    rain_probability = float(rain_values[0])
    precipitation = float(precipitation_raw) if precipitation_raw is not None else None
    risk_level = _risk_level(humidity, rain_probability, precipitation)

    return {
        "available": True,
        "temperature_c": round(float(temperature_raw), 1),
        "humidity_percent": round(humidity),
        "precipitation_mm": round(precipitation, 2) if precipitation is not None else None,
        "rain_probability_percent": round(rain_probability),
        "wind_kmh": round(float(current.get("wind_speed_10m") or 0), 1),
        "pressure_hpa": round(float(current["surface_pressure"]), 1) if current.get("surface_pressure") is not None else None,
        "risk_level": risk_level,
        "advisory": _advisory(risk_level),
    }
