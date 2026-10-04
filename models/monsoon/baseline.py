"""Transparent empirical baseline. Probabilities are historical frequencies, not guarantees."""
import csv
import math
from datetime import date
from pathlib import Path
from statistics import mean


NUMERIC_FIELDS = ("rainfall_mm", "temperature_c", "humidity_percent", "enso_index",
                 "iod_index", "mjo_phase", "wind_kmh")


def _optional_number(value, field, row_number):
    if value is None or not str(value).strip():
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid {field} value on CSV row {row_number}.") from error
    if not math.isfinite(number):
        raise ValueError(f"Invalid {field} value on CSV row {row_number}.")
    return number


def load_historical_csv(path):
    """Load canonical daily observations from CSV; rainfall_mm and date are required.

    Optional variables stay null when absent instead of being fabricated as zero.
    Rows without rainfall are excluded because the rainfall baseline cannot train on them.
    """
    with Path(path).open("r", newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        headers = set(reader.fieldnames or [])
        missing = {"date", "rainfall_mm"} - headers
        if missing:
            raise ValueError("CSV requires columns: date, rainfall_mm.")
        rows = []
        for row_number, row in enumerate(reader, start=2):
            raw_date = (row.get("date") or "").strip()
            try:
                date.fromisoformat(raw_date)
            except ValueError as error:
                raise ValueError(f"Invalid ISO date on CSV row {row_number}.") from error
            item = {"date": raw_date}
            for field in NUMERIC_FIELDS:
                item[field] = _optional_number(row.get(field), field, row_number)
            if item["rainfall_mm"] is not None:
                if item["rainfall_mm"] < 0:
                    raise ValueError(f"Rainfall cannot be negative on CSV row {row_number}.")
                rows.append(item)
    return sorted(rows, key=lambda row: row["date"])


def run_baseline_csv(path, horizons=(7, 14, 21, 30)):
    """Load, train and forecast from one historical CSV file."""
    model = train_baseline(load_historical_csv(path))
    return {"model": model, "forecast": predict(model, horizons)}


def time_series_features(rows):
    rows = sorted(rows, key=lambda row: row["date"])
    features = []
    for index, row in enumerate(rows):
        prior = rows[max(0, index - 6):index]
        prior_rain = [float(item["rainfall_mm"]) for item in prior if item.get("rainfall_mm") is not None]
        complete_prior = len(prior) == 6 and len(prior_rain) == 6
        features.append({
            "date": row["date"], "rainfall_mm": _optional_number(row.get("rainfall_mm"), "rainfall_mm", index + 1),
            "rain_7d_mm": sum(prior_rain) if complete_prior else None,
            "temperature_c": _optional_number(row.get("temperature_c"), "temperature_c", index + 1),
            "humidity_percent": _optional_number(row.get("humidity_percent"), "humidity_percent", index + 1),
            "enso_index": _optional_number(row.get("enso_index"), "enso_index", index + 1),
            "iod_index": _optional_number(row.get("iod_index"), "iod_index", index + 1),
            "mjo_phase": _optional_number(row.get("mjo_phase"), "mjo_phase", index + 1),
            "wind_kmh": _optional_number(row.get("wind_kmh"), "wind_kmh", index + 1),
        })
    return features


def train_baseline(rows):
    """Fit a seasonal-climatology baseline from daily rainfall observations."""
    rows = sorted(rows, key=lambda row: row["date"])
    if len(rows) < 30:
        raise ValueError("At least 30 daily historical observations are required.")
    daily = [max(0.0, float(row["rainfall_mm"])) for row in rows if row.get("rainfall_mm") is not None]
    if len(daily) < 30:
        raise ValueError("At least 30 daily rainfall observations are required.")
    wet = sum(value >= 1.0 for value in daily) / len(daily)
    return {"daily_mean_mm": mean(daily), "wet_day_probability": wet,
            "daily_samples": len(daily), "features": time_series_features(rows)}


def predict(model, horizons=(7, 14, 21, 30), climatology_anomaly_mm=0.0):
    output = []
    for days in horizons:
        expected = max(0.0, model["daily_mean_mm"] * days + climatology_anomaly_mm)
        # The cumulative chance of at least one wet day under a simple independence baseline.
        wet = model["wet_day_probability"]
        any_rain = 1 - (1 - wet) ** days
        output.append({"days": days, "expected_rainfall_mm": round(expected, 1),
                       "rainfall_probability": round(any_rain, 3),
                       "probability_basis": "historical wet-day frequency baseline"})
    return output
