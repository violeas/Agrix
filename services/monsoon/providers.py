"""Public data adapters used by Monsoon Intelligence.

Open-Meteo ensemble and archive APIs are unauthenticated for non-commercial use.
Geocoding uses Open-Meteo search and OpenStreetMap Nominatim reverse lookup.
All network failures are returned as unavailable data, never simulated values.
"""
from datetime import date, timedelta
from functools import lru_cache
import json
import os
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen


TIMEOUT_SECONDS = float(os.getenv("AGRISHIELD_PROVIDER_TIMEOUT", "8"))
APP_USER_AGENT = os.getenv("AGRISHIELD_USER_AGENT", "AgriShield/1.0")


def _get_json(url, user_agent=APP_USER_AGENT):
    request = Request(url, headers={"User-Agent": user_agent, "Accept": "application/json"})
    with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict) or payload.get("error"):
        raise ValueError((payload or {}).get("reason", "The data provider returned an invalid response."))
    return payload


def _district_location_id(district, state):
    if not district or not state:
        return None
    slug = lambda value: re.sub(r"[^\w-]+", "-", str(value).strip().lower()).strip("-")
    return f"district:{slug(district)}:{slug(state)}"


@lru_cache(maxsize=128)
def get_ensemble_forecast(latitude, longitude, forecast_date=None):
    """Fetch actual 30-day GFS ensemble member precipitation at the provider grid point."""
    query = urlencode({
        "latitude": round(float(latitude), 4), "longitude": round(float(longitude), 4),
        "models": "gfs_seamless", "daily": "precipitation_sum",
        "forecast_days": 30, "timezone": "auto",
    })
    return _get_json(f"https://ensemble-api.open-meteo.com/v1/ensemble?{query}")


@lru_cache(maxsize=128)
def get_recent_rainfall(latitude, longitude, today=None):
    """Get recent gridded rainfall observations/reanalysis; recent days may be delayed upstream."""
    end = date.fromisoformat(today or date.today().isoformat()) - timedelta(days=5)
    start = end - timedelta(days=29)
    query = urlencode({
        "latitude": round(float(latitude), 4), "longitude": round(float(longitude), 4),
        "start_date": start.isoformat(), "end_date": end.isoformat(),
        "daily": "precipitation_sum", "timezone": "auto",
    })
    return _get_json(f"https://archive-api.open-meteo.com/v1/archive?{query}")


@lru_cache(maxsize=256)
def search_locations(query_text):
    query = urlencode({"name": query_text, "count": 8, "language": "en", "format": "json"})
    payload = _get_json(f"https://geocoding-api.open-meteo.com/v1/search?{query}")
    return [{
        "name": item.get("name", ""), "latitude": item.get("latitude"),
        "longitude": item.get("longitude"), "village": None,
        "block": None, "district": item.get("admin2"),
        "state": item.get("admin1"), "country": item.get("country"),
        "country_code": item.get("country_code"),
        "location_id": _district_location_id(item.get("admin2"), item.get("admin1")),
        "admin_level_available": "district" if item.get("admin2") else "state" if item.get("admin1") else "country",
        "source": "Open-Meteo Geocoding API",
    } for item in payload.get("results", [])]


@lru_cache(maxsize=256)
def reverse_geocode(latitude, longitude):
    query = urlencode({"lat": round(float(latitude), 5), "lon": round(float(longitude), 5), "format": "jsonv2", "zoom": 10, "addressdetails": 1})
    url = f"https://nominatim.openstreetmap.org/reverse?{query}"
    payload = _get_json(url, f"{APP_USER_AGENT} ({os.getenv('AGRISHIELD_CONTACT', 'contact not configured')})")
    address = payload.get("address") or {}
    locality = address.get("village") or address.get("hamlet") or address.get("town") or address.get("city") or address.get("municipality")
    district = address.get("state_district") or address.get("district")
    return {
        "label": ", ".join(item for item in [locality, district, address.get("state"), address.get("country")] if item),
        "village": address.get("village") or address.get("hamlet"),
        "block": None, "district": district, "state": address.get("state"),
        "country": address.get("country"), "latitude": float(latitude),
        "longitude": float(longitude), "admin_level_available": "district" if district else "locality" if locality else "coordinates",
        "source": "OpenStreetMap Nominatim",
        "location_id": _district_location_id(district, address.get("state")),
    }


def current_climate_drivers():
    from services.monsoon.climate import current_climate_drivers as load_indices
    return load_indices()


class OpenMeteoWeatherProvider:
    """GFS ensemble weather input. Forecast lead is up to 30 days at gridded resolution."""

    source = "Open-Meteo Ensemble API"
    endpoint = "https://ensemble-api.open-meteo.com/v1/ensemble"
    credentials = "None for non-commercial access; commercial terms may require an API key."
    update_frequency = "Upstream model-dependent; request-level response metadata is returned."
    limitations = "Global-model grid guidance. Member frequencies are raw and uncalibrated; no district boundary aggregation."

    def ensemble_daily(self, latitude, longitude, days=30):
        if days != 30:
            raise ValueError("The current provider adapter requests the supported 30-day horizon.")
        return get_ensemble_forecast(round(float(latitude), 4), round(float(longitude), 4), date.today().isoformat())


class OpenMeteoRainfallHistoryProvider:
    source = "Open-Meteo Historical Weather API (reanalysis)"
    endpoint = "https://archive-api.open-meteo.com/v1/archive"
    credentials = "None for non-commercial access; commercial terms may require an API key."
    update_frequency = "Daily; most recent values may be delayed."
    limitations = "Reanalysis grid estimate, not a local rain gauge."

    def daily_rainfall(self, latitude, longitude, start=None, end=None):
        return get_recent_rainfall(round(float(latitude), 4), round(float(longitude), 4), date.today().isoformat())


class NOAAClimateFeatureProvider:
    source = "NOAA CPC RONI, NOAA PSL DMI, Australian Bureau of Meteorology RMM"
    update_frequency = "Monthly for RONI/DMI; daily for RMM, source-dependent."
    limitations = "Global climate context; no validated local rainfall influence is applied."

    def current_indices(self):
        return current_climate_drivers()


class OpenStreetMapBoundaryProvider:
    source = "OpenStreetMap Nominatim reverse geocoding"
    endpoint = "https://nominatim.openstreetmap.org/reverse"
    credentials = "None; public service policy and request limits apply."
    update_frequency = "On location selection; result cached in application settings."
    limitations = "Only address fields returned upstream are shown; block/panchayat boundaries are not bundled."

    def resolve(self, latitude, longitude):
        return reverse_geocode(round(float(latitude), 5), round(float(longitude), 5))
