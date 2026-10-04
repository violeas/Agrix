"""Transparent, source-aware decision summaries built from backend forecast data."""
from datetime import datetime, timezone


def _horizon(forecast, days):
    return next((item for item in forecast.get("horizons", []) if item.get("days") == int(days)), None)


def explain_forecast(forecast, days=14):
    horizon = _horizon(forecast, days) or {}
    history = forecast.get("recent_rainfall") or {}
    recent_days = (history.get("daily") or [])[-14:]
    observed_values = [row.get("rainfall_mm") for row in recent_days if row.get("rainfall_mm") is not None]
    observed_total = round(sum(observed_values), 1) if observed_values else None
    drivers = {row.get("name"): row for row in (forecast.get("climate_drivers") or {}).get("drivers", [])}
    model_result = ((forecast.get("agri_model") or {}).get("horizons") or {}).get(str(days), {})
    false_onset_probability = ((model_result.get("predictions") or {}).get("false_onset_event")
                               if model_result.get("validated") else None)
    return {
        "horizon_days": int(days),
        "observed_recent_rainfall": {
            "value_mm": observed_total, "days": len(observed_values),
            "source": history.get("source") if observed_values else None,
            "status": history.get("status", "Data unavailable"),
        },
        "historical_normal": {"value_mm": None, "status": "Data unavailable: validated local seasonal normals are not connected."},
        "enso": {"value": drivers.get("ENSO", {}).get("value"), "date": drivers.get("ENSO", {}).get("observed_date"),
                 "source": drivers.get("ENSO", {}).get("source"), "role": "Context only; no local effect coefficient is trained."},
        "iod": {"value": drivers.get("IOD", {}).get("value"), "date": drivers.get("IOD", {}).get("observed_date"),
                "source": drivers.get("IOD", {}).get("source"), "role": "Context only; no local effect coefficient is trained."},
        "mjo": {"phase": drivers.get("MJO", {}).get("phase"), "amplitude": drivers.get("MJO", {}).get("amplitude"),
                "date": drivers.get("MJO", {}).get("observed_date"), "source": drivers.get("MJO", {}).get("source"),
                "role": "Context only; no local effect coefficient is trained."},
        "provider_forecast": {"expected_rainfall_mm": horizon.get("expected_rainfall_mm"),
                              "rainfall_member_frequency": horizon.get("rainfall_probability"),
                              "source": (forecast.get("source") or {}).get("name"),
                              "basis": horizon.get("probability_basis", "Data unavailable")},
        "dry_spell_indicator": {"value": horizon.get("dry_spell_probability"),
                                "basis": horizon.get("probability_basis", "Data unavailable")},
        "model_confidence": {"validated": model_result.get("validated", False),
                             "status": model_result.get("calibration_status", "No validated AgriShield model is available for this location.")},
        "false_onset": {"value": false_onset_probability,
                         "status": ("Validated local event-label model output; raw, not calibrated."
                                    if false_onset_probability is not None else
                                    (forecast.get("events") or {}).get("false_onset_status", "Data unavailable"))},
    }


def sowing_window_assessment(crop_name, forecast, crop=None):
    """Do not score suitability until validated local and crop-water inputs exist."""
    horizon = _horizon(forecast, 14) or {}
    calendar = (crop or {}).get("crop_calendar") or {}
    complete_calendar = all(calendar.get(field) is not None for field in
                            ("sowing_start", "sowing_end", "water_requirement_mm_day"))
    reasons = []
    if not forecast.get("available"):
        reasons.append("Location weather forecast is unavailable.")
    if (forecast.get("events") or {}).get("onset_probability") is None:
        reasons.append("Validated local onset probability and official onset criteria are unavailable.")
    if not complete_calendar:
        reasons.append("A complete location-specific crop water requirement and sowing calendar are not connected.")
    reasons.append("Validated local seasonal rainfall normals are not connected.")
    if not (forecast.get("recent_rainfall") or {}).get("available"):
        reasons.append("Recent observed or reanalysis rainfall is unavailable.")
    return {
        "crop": crop_name,
        "suitability": "unavailable",
        "reasons": reasons,
        "inputs": {
            "recent_rainfall_available": bool((forecast.get("recent_rainfall") or {}).get("available")),
            "forecast_rainfall_mm_14d": horizon.get("expected_rainfall_mm"),
            "dry_spell_member_frequency_14d": horizon.get("dry_spell_probability"),
            "onset_probability": (forecast.get("events") or {}).get("onset_probability"),
            "crop_stage": (crop or {}).get("growth_stage"),
            "irrigation_type": (crop or {}).get("irrigation_type"),
            "crop_calendar_source": calendar.get("source"),
            "sowing_start": calendar.get("sowing_start"),
            "sowing_end": calendar.get("sowing_end"),
            "crop_water_requirement_mm_day": calendar.get("water_requirement_mm_day"),
            "crop_calendar_complete": complete_calendar,
        },
        "message": "Sowing suitability cannot be rated until local onset labels, seasonal rainfall normals and a complete location-specific crop calendar are available.",
        "decision_support_only": True,
    }


def build_alerts(forecast, location_id, horizon_days=14):
    """Create explainable in-app advisories from raw ensemble member frequencies."""
    item = _horizon(forecast, horizon_days)
    if not forecast.get("available") or item is None:
        return []
    source = (forecast.get("source") or {}).get("name", "Weather provider")
    timestamp = (forecast.get("source") or {}).get("generated_at") or datetime.now(timezone.utc).isoformat()
    data_timestamp = (forecast.get("recent_rainfall") or {}).get("last_observation_date")
    today = timestamp[:10]
    alerts = []
    dry = item.get("dry_spell_probability")
    if dry is not None and dry >= .5:
        alerts.append({
            "location_id": location_id, "alert_key": f"{location_id}:{today}:dry-spell:{horizon_days}",
            "alert_type": "dry_spell", "severity": "high" if dry >= .75 else "moderate",
            "title": "Dry-spell signal in weather ensemble",
            "message": f"{round(dry * 100)}% of raw ensemble members contain a dry run of at least five days within {horizon_days} days. Check field moisture and local advisories; this is not an official warning.",
            "source": source, "probability": dry, "horizon_days": horizon_days,
            "data_timestamp": data_timestamp, "forecast_timestamp": timestamp,
        })
    heavy = item.get("heavy_rain_probability")
    if heavy is not None and heavy >= .2:
        alerts.append({
            "location_id": location_id, "alert_key": f"{location_id}:{today}:heavy-rain:{horizon_days}",
            "alert_type": "heavy_rain", "severity": "high" if heavy >= .5 else "moderate",
            "title": "Heavy-rain signal in weather ensemble",
            "message": f"{round(heavy * 100)}% of raw ensemble members include at least one day at or above 64.5 mm within {horizon_days} days. Review drainage and official local warnings.",
            "source": source, "probability": heavy, "horizon_days": horizon_days,
            "data_timestamp": data_timestamp, "forecast_timestamp": timestamp,
        })
    model_output = ((forecast.get("agri_model") or {}).get("horizons") or {}).get(str(horizon_days), {})
    false_onset = (model_output.get("predictions") or {}).get("false_onset_event")
    if model_output.get("validated") and false_onset is not None and false_onset >= .5:
        model_version = (forecast.get("agri_model") or {}).get("model_version", "AgriShield model")
        alerts.append({
            "location_id": location_id, "alert_key": f"{location_id}:{today}:false-onset:{horizon_days}:{model_version}",
            "alert_type": "false_onset", "severity": "high" if false_onset >= .75 else "moderate",
            "title": "False-onset risk from validated local model",
            "message": f"The trained local model estimates {round(false_onset * 100)}% false-onset risk within {horizon_days} days. Review the model's held-out metrics and regional criteria before making a sowing decision.",
            "source": model_version, "probability": false_onset, "horizon_days": horizon_days,
            "data_timestamp": (forecast.get("agri_model") or {}).get("data_timestamp"),
            "forecast_timestamp": model_output.get("forecast_timestamp") or timestamp,
        })
    return alerts


def crop_advisories(forecast, crop=None):
    if not forecast.get("available"):
        return [{"type": "data", "text": "Forecast unavailable for this location because sufficient validated data is not available.",
                 "reason": "Weather provider or location data is missing.", "decision_support_only": True}]
    crop_name = (crop or {}).get("crop_name", "selected crop")
    stage = (crop or {}).get("growth_stage", "pre-sowing")
    item = _horizon(forecast, 14) or {}
    advice = []
    dry = item.get("dry_spell_probability")
    heavy = item.get("heavy_rain_probability")
    if dry is not None and dry >= .4:
        advice.append({"type": "irrigation", "text": f"Check soil moisture and confirm irrigation options for {crop_name} at {stage}.",
                       "reason": f"{round(dry * 100)}% raw GFS member frequency for a five-day dry run in the 14-day window.",
                       "percent": round(dry * 100), "crop": crop_name, "stage": stage,
                       "basis": item.get("probability_basis"), "decision_support_only": True})
    if heavy is not None and heavy >= .2:
        advice.append({"type": "drainage", "text": f"Review field drainage and protect stored inputs for {crop_name} at {stage}.",
                       "reason": f"{round(heavy * 100)}% raw GFS member frequency for at least one day at or above 64.5 mm.",
                       "percent": round(heavy * 100), "crop": crop_name, "stage": stage,
                       "basis": item.get("probability_basis"), "decision_support_only": True})
    if not advice:
        advice.append({"type": "monitor", "text": f"Check field conditions and review the updated outlook for {crop_name} at {stage}.",
                       "reason": "Provider signals do not cross the configured prompt thresholds; this does not mean field risk is zero.",
                       "crop": crop_name, "stage": stage, "basis": item.get("probability_basis"), "decision_support_only": True})
    advice.append({"type": "fertilizer", "text": "Fertilizer timing advice is unavailable.",
                   "reason": "Field soil, crop nutrient plan and locally approved timing rules are not connected.",
                   "crop": crop_name, "stage": stage, "decision_support_only": True})
    return advice
