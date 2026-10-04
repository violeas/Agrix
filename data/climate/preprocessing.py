"""Canonical climate record parsing and leakage-safe time-series features."""
from datetime import date, datetime, timezone
import math


NUMERIC_FIELDS = (
    "rainfall_mm", "temperature_c", "humidity_percent", "wind_kmh", "pressure_hpa",
    "enso_index", "iod_index", "mjo_rmm1", "mjo_rmm2", "mjo_phase", "mjo_amplitude",
    "normal_rainfall_mm",
)
EVENT_FIELDS = ("onset_event", "false_onset_event")


def _number(value, field, row_number):
    if value is None or str(value).strip() == "":
        return None
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid {field} on row {row_number}.") from error
    if not math.isfinite(result):
        raise ValueError(f"Invalid {field} on row {row_number}.")
    return result


def _event(value, field, row_number):
    if value is None or str(value).strip() == "":
        return None
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "positive"}:
        return 1
    if text in {"0", "false", "no", "negative"}:
        return 0
    raise ValueError(f"Invalid {field} label on row {row_number}; use 0/1 or true/false.")


def normalize_observation(row, location_id=None, source=None, row_number=1):
    """Normalize one joined daily row; absent measurements remain None."""
    raw_date = str(row.get("date") or row.get("observation_date") or "").strip()
    try:
        observed = date.fromisoformat(raw_date[:10])
    except ValueError as error:
        raise ValueError(f"Invalid ISO observation date on row {row_number}.") from error
    normalized_location = str(location_id or row.get("location_id") or "").strip()
    normalized_source = str(source or row.get("source") or "").strip()
    if not normalized_location:
        raise ValueError(f"A location_id is required on row {row_number}.")
    if not normalized_source:
        raise ValueError(f"A source is required on row {row_number}.")
    output = {"date": observed.isoformat(), "location_id": normalized_location, "source": normalized_source}
    for field in NUMERIC_FIELDS:
        output[field] = _number(row.get(field), field, row_number)
    if output["rainfall_mm"] is not None and output["rainfall_mm"] < 0:
        raise ValueError(f"Negative rainfall on row {row_number}.")
    for field in EVENT_FIELDS:
        output[field] = _event(row.get(field), field, row_number)
    for field in ("latitude", "longitude"):
        output[field] = _number(row.get(field), field, row_number)
    return output


def spatial_align(rows, location_id):
    """Keep exact location matches; never silently borrow a neighboring area's data."""
    location_id = str(location_id or "").strip()
    if not location_id:
        raise ValueError("A location_id is required for spatial alignment.")
    return sorted((row for row in rows if row.get("location_id") == location_id), key=lambda row: row["date"])


def temporal_align(daily_rows, dated_feature_rows, fields, max_age_days=90):
    """Carry the most recent known climate index forward, never a future observation."""
    features = sorted(dated_feature_rows, key=lambda row: row["date"])
    output = []
    cursor = 0
    latest = None
    for row in sorted(daily_rows, key=lambda item: item["date"]):
        day = date.fromisoformat(row["date"][:10])
        while cursor < len(features) and date.fromisoformat(features[cursor]["date"][:10]) <= day:
            latest = features[cursor]
            cursor += 1
        merged = dict(row)
        age = (day - date.fromisoformat(latest["date"][:10])).days if latest else None
        for field in fields:
            usable = latest is not None and age <= max_age_days and latest.get(field) is not None
            merged[field] = latest[field] if usable else None
            merged[f"{field}_observed_date"] = latest["date"] if usable else None
            merged[f"{field}_age_days"] = age if usable else None
        output.append(merged)
    return output


def rolling_features(rows, dry_day_mm=1.0):
    """Create lagged rainfall, rolling totals, intensity and dry-spell features."""
    ordered = sorted(rows, key=lambda row: row["date"])
    output = []
    dry_run = 0
    for index, row in enumerate(ordered):
        rain = row.get("rainfall_mm")
        dry_run = (dry_run + 1 if rain < dry_day_mm else 0) if rain is not None else 0
        item = dict(row)
        item["rainfall_intensity_mm_day"] = rain
        item["dry_spell_length_days"] = dry_run if rain is not None else None
        for window in (3, 7, 14, 30):
            sample = ordered[max(0, index - window + 1):index + 1]
            values = [entry.get("rainfall_mm") for entry in sample]
            complete = len(sample) == window and all(value is not None for value in values)
            item[f"rolling_rain_{window}d_mm"] = sum(values) if complete else None
            item[f"cumulative_rain_{window}d_mm"] = item[f"rolling_rain_{window}d_mm"]
        prior_7 = ordered[index - 7] if index >= 7 else {}
        for field in ("enso_index", "iod_index", "mjo_rmm1", "mjo_rmm2", "mjo_phase", "mjo_amplitude"):
            item[f"{field}_lag_7d"] = prior_7.get(field)
        output.append(item)
    return output


def rainfall_anomalies(rows, normals_by_date):
    """Calculate anomalies only against explicitly supplied date-specific normals."""
    output = []
    for row in rows:
        item = dict(row)
        normal = normals_by_date.get(row["date"])
        rain = row.get("rainfall_mm")
        item["rainfall_anomaly_mm"] = float(rain) - float(normal) if rain is not None and normal is not None else None
        output.append(item)
    return output


def timestamp_for_date(value):
    """Return a UTC-midnight ISO timestamp for a daily observation date."""
    day = date.fromisoformat(str(value)[:10])
    return datetime(day.year, day.month, day.day, tzinfo=timezone.utc).isoformat()
