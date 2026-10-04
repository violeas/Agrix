"""Location-specific ensemble outlook and honest event/advisory interpretation."""
from datetime import date, datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
import re

from services.monsoon.providers import (
    NOAAClimateFeatureProvider, OpenMeteoRainfallHistoryProvider,
    OpenMeteoWeatherProvider,
)

WEATHER_PROVIDER = OpenMeteoWeatherProvider()
RAINFALL_PROVIDER = OpenMeteoRainfallHistoryProvider()
CLIMATE_PROVIDER = NOAAClimateFeatureProvider()

HORIZONS = (7, 14, 21, 30)
HEAVY_RAIN_MM = 64.5  # IMD daily heavy-rain threshold
WET_DAY_MM = 1.0
DRY_SPELL_DAYS = 5


def _ensemble_members(daily):
    keys = sorted((key for key in daily if re.fullmatch(r"precipitation_sum_member\d+", key)), key=lambda key: int(re.search(r"(\d+)$", key).group(1)))
    members = []
    for key in keys:
        values = daily.get(key) or []
        if values and all(value is not None for value in values):
            members.append([max(0.0, float(value)) for value in values])
    return members


def _max_dry_run(values):
    run = best = 0
    for amount in values:
        run = run + 1 if amount < WET_DAY_MM else 0
        best = max(best, run)
    return best


def _percent(count, total):
    return round(count / total, 3) if total else None


def _advisory(crop, events):
    if not crop:
        return ["Choose a crop profile to tailor these weather signals to its growth stage."]
    name = crop.get("crop_name", "crop")
    stage = crop.get("growth_stage", "current stage").lower()
    advice = []
    dry_probability = events.get("dry_spell_probability")
    heavy_probability = events.get("heavy_rain_probability")
    if dry_probability is not None and dry_probability >= .4:
        qualifier = "newly planted or at establishment" if any(term in stage for term in ("establish", "germination", "seedling")) else stage
        advice.append(f"A dry run appears in some ensemble members. For {name} ({qualifier}), check field moisture and irrigation options; use local extension advice before changing plans.")
    if heavy_probability is not None and heavy_probability >= .2:
        advice.append(f"Some ensemble members exceed the heavy-rain threshold. For {name}, inspect drainage and secure inputs; this is an early signal, not an official warning.")
    if not advice:
        advice.append(f"For {name} at {stage}, monitor local field conditions and revisit this outlook as forecasts update.")
    advice.append("This outlook is global-model ensemble guidance at a forecast grid cell; it is not a block or panchayat forecast and is not locally validated.")
    return advice


def generate_forecast(latitude=None, longitude=None, crop=None, location=None):
    if latitude is None or longitude is None:
        return unavailable_forecast("Select a location or allow device location to load the weather ensemble.", location)
    try:
        lat, lon = float(latitude), float(longitude)
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return unavailable_forecast("The selected coordinates are outside the valid range.", location)
        with ThreadPoolExecutor(max_workers=3) as pool:
            ensemble_task = pool.submit(WEATHER_PROVIDER.ensemble_daily, lat, lon, 30)
            history_task = pool.submit(_recent_history, lat, lon)
            climate_task = pool.submit(CLIMATE_PROVIDER.current_indices)
            payload = ensemble_task.result()
            recent_rainfall = history_task.result()
            climate_drivers = climate_task.result()
        daily = payload.get("daily") or {}
        dates = daily.get("time") or []
        members = _ensemble_members(daily)
        if not dates or not members:
            return unavailable_forecast("The ensemble provider returned no usable rainfall members.", location)
        size = min(len(dates), *(len(member) for member in members))
        dates = dates[:size]
        members = [member[:size] for member in members]
        outputs = []
        for horizon in HORIZONS:
            n = min(horizon, size)
            sample = [member[:n] for member in members]
            totals = [sum(values) for values in sample]
            rainfall_probability = _percent(sum(total >= WET_DAY_MM for total in totals), len(totals))
            dry_probability = _percent(sum(_max_dry_run(values) >= DRY_SPELL_DAYS for values in sample), len(sample))
            heavy_probability = _percent(sum(any(value >= HEAVY_RAIN_MM for value in values) for values in sample), len(sample))
            outputs.append({
                "days": horizon,
                "available": n == horizon,
                "expected_rainfall_mm": round(sum(totals) / len(totals), 1),
                "rainfall_probability": rainfall_probability,
                "dry_spell_probability": dry_probability,
                "heavy_rain_probability": heavy_probability,
                "onset_probability": None,
                "rainfall_anomaly_mm": None,
                "anomaly_status": "Data unavailable: local seasonal rainfall normals are not connected.",
                "ensemble_members": len(sample),
                "probability_basis": "raw fraction of GFS ensemble members; not calibrated or locally validated",
            })
        # The API normally returns all 30 days. Never publish partial member coverage as a full horizon.
        for item in outputs:
            if not item["available"]:
                item.update({"expected_rainfall_mm": None, "rainfall_probability": None,
                             "dry_spell_probability": None, "heavy_rain_probability": None,
                             "ensemble_members": 0})
        daily_outlook = []
        for index, day in enumerate(dates):
            probability = _percent(sum(member[index] >= WET_DAY_MM for member in members), len(members))
            average = round(sum(member[index] for member in members) / len(members), 1)
            heavy = _percent(sum(member[index] >= HEAVY_RAIN_MM for member in members), len(members))
            daily_outlook.append({"date": day, "day": index + 1, "expected_rainfall_mm": average,
                                  "rain_probability": probability, "heavy_rain_probability": heavy,
                                  "risk": "Higher heavy-rain signal" if heavy >= .3 else "Rain signal" if probability >= .5 else "Lower rain signal"})
        horizon_30 = outputs[-1]
        events = {
            "onset_probability": None, "false_onset_probability": None,
            "dry_spell_probability": horizon_30["dry_spell_probability"],
            "heavy_rain_probability": horizon_30["heavy_rain_probability"],
            "rainfall_anomaly_mm": None,
            "onset_status": "Data unavailable: official regional onset criteria and observed rainfall are not connected.",
            "false_onset_status": "Data unavailable: onset and local observed rainfall continuity are required.",
            "revival_status": "Data unavailable: recent observed rainfall series is not connected.",
            "break_monsoon_status": "Ensemble dry-run signal available; monsoon break classification is unavailable without regional observations.",
            "heavy_rain_threshold_mm": HEAVY_RAIN_MM,
            "dry_spell_definition": f"at least {DRY_SPELL_DAYS} consecutive days below {WET_DAY_MM} mm in one ensemble member",
        }
        location_result = {
            **(location or {}), "latitude": payload.get("latitude", lat), "longitude": payload.get("longitude", lon),
            "grid_elevation_m": payload.get("elevation"), "forecast_grid": "GFS Seamless ensemble grid",
            "scale": "gridded regional weather; administrative boundary forecast unavailable",
            "village": (location or {}).get("village"), "block": (location or {}).get("block"),
            "district": (location or {}).get("district"), "state": (location or {}).get("state"),
            "boundary_status": ("This point matches an authoritative administrative boundary; risk values are not area-aggregated."
                                 if (location or {}).get("boundary_id") else
                                 "Block/panchayat boundaries and area-aggregated risk data are unavailable."),
        }
        return {
            "available": True, "location": location_result,
            "horizons": outputs, "daily": daily_outlook, "events": events,
            "advisory": _advisory(crop, events), "climate_drivers": climate_drivers,
            "data_status": "REAL DATA: GFS ensemble forecast retrieved for the selected coordinates. Ensemble probabilities are raw, uncalibrated member frequencies.",
            "source": {"name": "Open-Meteo Ensemble API", "model": "GFS Seamless ensemble", "api": "https://ensemble-api.open-meteo.com/v1/ensemble", "generated_at": datetime.now(timezone.utc).isoformat(), "request_generation_ms": payload.get("generationtime_ms"), "member_count": len(members), "limitations": ["Grid-cell weather guidance, not district/block/panchayat prediction.", "Raw ensemble member fractions are not calibrated probabilities.", "ENSO, IOD and MJO are shown as context only; no regional relationship is applied."]},
            "model": {"name": "GFS Seamless ensemble frequency baseline", "trained": False, "validated": False, "probabilities_are_guarantees": False},
            "recent_rainfall": recent_rainfall,
        }
    except Exception as error:
        return unavailable_forecast(f"Weather ensemble unavailable: {str(error)[:180]}", location)


def _recent_history(latitude, longitude):
    try:
        payload = RAINFALL_PROVIDER.daily_rainfall(latitude, longitude)
        daily = payload.get("daily") or {}
        dates = daily.get("time", [])
        return {"available": True, "source": "Open-Meteo Historical Weather API (reanalysis; recent days delayed)",
                "daily": [{"date": day, "rainfall_mm": rain} for day, rain in zip(dates, daily.get("precipitation_sum", []))],
                "last_observation_date": dates[-1] if dates else None,
                "status": "Recent gridded reanalysis; not a station measurement."}
    except Exception:
        return {"available": False, "daily": [], "status": "Data unavailable: recent rainfall history could not be loaded."}


def unavailable_forecast(reason, location=None):
    return {
        "available": False, "location": location or {"label": "Location unavailable", "scale": "unavailable"},
        "horizons": [{"days": days, "available": False, "expected_rainfall_mm": None,
                      "rainfall_probability": None, "dry_spell_probability": None,
                      "heavy_rain_probability": None, "onset_probability": None,
                      "rainfall_anomaly_mm": None, "anomaly_status": "Data unavailable"} for days in HORIZONS],
        "daily": [], "events": {"onset_probability": None, "false_onset_probability": None,
                                 "dry_spell_probability": None, "heavy_rain_probability": None,
                                 "rainfall_anomaly_mm": None, "onset_status": "Data unavailable",
                                 "false_onset_status": "Data unavailable", "revival_status": "Data unavailable",
                                 "break_monsoon_status": "Data unavailable"},
        "advisory": ["Weather data is unavailable. Do not use this screen to make a sowing or irrigation decision."],
        "climate_drivers": CLIMATE_PROVIDER.current_indices(), "data_status": reason,
        "source": {"name": "Open-Meteo Ensemble API", "status": "unavailable"},
        "model": {"name": "Not run", "trained": False, "validated": False,
                  "probabilities_are_guarantees": False},
        "recent_rainfall": {"available": False, "daily": [], "status": "Data unavailable"},
    }


def build_advisory(events, crop=None):
    return _advisory(crop, events)


def sowing_decision(forecast, crop_name, irrigation_available=False, horizon_days=14, crop_stage=None, sowing_preference=None):
    item = next((row for row in forecast.get("horizons", []) if row.get("days") == int(horizon_days)), None)
    if not forecast.get("available") or not item or not item.get("available"):
        return {"decision": "WAIT FOR DATA", "confidence": "Unavailable", "reason": "A usable location-specific ensemble outlook is not available.", "alternative_action": "Check the local weather office or agricultural extension service."}
    dry = item.get("dry_spell_probability")
    heavy = item.get("heavy_rain_probability")
    if dry is None or heavy is None:
        return {"decision": "WAIT FOR DATA", "confidence": "Unavailable", "reason": "Ensemble event probabilities were not returned.", "alternative_action": "Check local field conditions and official advisories."}
    if dry >= .5 and not irrigation_available:
        choice = "WAIT"
        reason = f"{round(dry * 100)}% of ensemble members contain a dry run of at least {DRY_SPELL_DAYS} days in the {horizon_days}-day window, and irrigation is unavailable. Crop stage: {crop_stage or 'not specified'}."
        action = "Prepare seed and field work; review the outlook again before sowing."
    elif heavy >= .35:
        choice = "SOW WITH CAUTION"
        reason = f"Some ensemble members indicate heavy-rain potential ({round(heavy * 100)}% raw member frequency) in the {horizon_days}-day window."
        action = "Check field drainage and avoid making an irreversible decision from this outlook alone."
    elif dry < .35:
        choice = "SOW WITH CAUTION"
        reason = "The ensemble has a lower dry-run signal, but it does not establish soil moisture or sowing suitability."
        action = "Confirm seedbed moisture and crop-specific local guidance before sowing."
    else:
        choice = "WAIT"
        reason = "The ensemble shows notable dry-run uncertainty for this window."
        action = "Monitor soil moisture and check updated local forecasts."
    return {"decision": choice, "crop": crop_name, "crop_stage": crop_stage,
            "sowing_preference": sowing_preference, "horizon_days": horizon_days,
            "confidence": "Uncalibrated ensemble guidance", "reason": reason,
            "alternative_action": action, "not_a_guarantee": True}
