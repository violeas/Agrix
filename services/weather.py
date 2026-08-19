import json
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen


def _risk_level(humidity, rain_probability, precipitation):
    if humidity >= 78 or rain_probability >= 55 or precipitation >= 0.5:
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
            "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
            "daily": "precipitation_probability_max",
            "forecast_days": 1,
            "timezone": "auto",
        }
    )
    url = f"https://api.open-meteo.com/v1/forecast?{params}"

    try:
        with urlopen(url, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, TimeoutError, json.JSONDecodeError):
        return {
            "available": False,
            "risk_level": "Unavailable",
            "advisory": "Weather monitoring could not be reached right now.",
        }

    current = payload.get("current") or {}
    daily = payload.get("daily") or {}
    humidity = float(current.get("relative_humidity_2m") or 0)
    rain_probability = float((daily.get("precipitation_probability_max") or [0])[0] or 0)
    precipitation = float(current.get("precipitation") or 0)
    risk_level = _risk_level(humidity, rain_probability, precipitation)

    return {
        "available": True,
        "temperature_c": round(float(current.get("temperature_2m") or 0), 1),
        "humidity_percent": round(humidity),
        "precipitation_mm": round(precipitation, 2),
        "rain_probability_percent": round(rain_probability),
        "wind_kmh": round(float(current.get("wind_speed_10m") or 0), 1),
        "risk_level": risk_level,
        "advisory": _advisory(risk_level),
    }
