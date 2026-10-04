"""Chronological, location-specific logistic-regression pipeline for monsoon risks.

The model is trained only from imported observations and event labels. It deliberately
returns no validated prediction when the location lacks enough held-out observations.
"""
import argparse
from datetime import datetime, timezone
import math
from uuid import uuid4

import database
from data.climate.preprocessing import rolling_features
from models.monsoon.evaluation import (
    binary_classification_metrics, brier_score, regression_metrics, reliability_bins,
)


HORIZONS = (7, 14, 21, 30)
DRY_DAY_MM = 1.0
DRY_RUN_DAYS = 5
HEAVY_RAIN_MM = 64.5
TARGETS = ("onset_event", "false_onset_event", "dry_spell_event", "heavy_rain_event")
FEATURE_FIELDS = (
    "rolling_rain_3d_mm", "rolling_rain_7d_mm", "rolling_rain_14d_mm", "rolling_rain_30d_mm",
    "dry_spell_length_days", "rainfall_intensity_mm_day", "temperature_c", "humidity_percent",
    "wind_kmh", "pressure_hpa", "enso_index", "iod_index", "mjo_rmm1", "mjo_rmm2",
    "mjo_phase", "mjo_amplitude", "enso_index_lag_7d", "iod_index_lag_7d",
    "mjo_rmm1_lag_7d", "mjo_rmm2_lag_7d", "mjo_phase_lag_7d", "mjo_amplitude_lag_7d",
    "day_of_year_sin", "day_of_year_cos",
)


def _derive_features(rows):
    featured = rolling_features(rows)
    for row in featured:
        day = datetime.fromisoformat(row["date"][:10]).timetuple().tm_yday
        row["day_of_year_sin"] = math.sin(2 * math.pi * day / 365.25)
        row["day_of_year_cos"] = math.cos(2 * math.pi * day / 365.25)
    return featured


def _max_dry_run(values):
    longest = run = 0
    for value in values:
        if value is None:
            return None
        run = run + 1 if value < DRY_DAY_MM else 0
        longest = max(longest, run)
    return longest


def build_samples(rows, horizon):
    """Build origin-time predictors and future-window labels with no future features."""
    ordered = sorted(rows, key=lambda row: row["date"])
    if len({row.get("location_id") for row in ordered}) > 1:
        raise ValueError("Training rows must contain exactly one location_id.")
    features = _derive_features(ordered)
    samples = []
    for origin in range(30, len(ordered) - horizon):
        future = ordered[origin + 1:origin + horizon + 1]
        rainfall = [row.get("rainfall_mm") for row in future]
        feature_row = {field: features[origin].get(field) for field in FEATURE_FIELDS}
        if any(value is None for value in rainfall):
            dry_target = heavy_target = None
        else:
            dry_target = int((_max_dry_run(rainfall) or 0) >= DRY_RUN_DAYS)
            heavy_target = int(any(value >= HEAVY_RAIN_MM for value in rainfall))
        labels = {
            "onset_event": int(any(row["onset_event"] for row in future)) if all(row.get("onset_event") is not None for row in future) else None,
            "false_onset_event": int(any(row["false_onset_event"] for row in future)) if all(row.get("false_onset_event") is not None for row in future) else None,
            "dry_spell_event": dry_target,
            "heavy_rain_event": heavy_target,
        }
        normals = [row.get("normal_rainfall_mm") for row in future]
        anomaly = sum(rainfall) - sum(normals) if all(value is not None for value in rainfall + normals) else None
        samples.append({"origin": origin, "end": origin + horizon, "date": ordered[origin]["date"],
                       "features": feature_row, "labels": labels, "rainfall_anomaly_mm": anomaly})
    return samples


def _chronological_split(samples, row_count, horizon):
    train_cut = int(row_count * .6)
    validation_cut = int(row_count * .8)
    train = [sample for sample in samples if sample["end"] < train_cut]
    validation = [sample for sample in samples if sample["origin"] >= train_cut and sample["end"] < validation_cut]
    test = [sample for sample in samples if sample["origin"] >= validation_cut and sample["end"] < row_count]
    boundaries = {
        "training_start": train[0]["date"] if train else None,
        "training_end": train[-1]["date"] if train else None,
        "validation_start": validation[0]["date"] if validation else None,
        "validation_end": validation[-1]["date"] if validation else None,
        "test_start": test[0]["date"] if test else None,
        "test_end": test[-1]["date"] if test else None,
        "target_window_gap_days": horizon,
    }
    return train, validation, test, boundaries


def _fit_scaler(feature_rows):
    names = [name for name in FEATURE_FIELDS
             if sum(row.get(name) is not None for row in feature_rows) >= max(30, math.ceil(len(feature_rows) * .8))]
    if not names:
        raise ValueError("No usable predictors are available in the training period.")
    means = {}
    scales = {}
    for name in names:
        values = [float(row[name]) for row in feature_rows if row.get(name) is not None]
        means[name] = sum(values) / len(values)
        variance = sum((value - means[name]) ** 2 for value in values) / len(values)
        scales[name] = math.sqrt(variance) or 1.0
    return names, means, scales


def _matrix(feature_rows, names, means, scales):
    return [[(float(row[name]) if row.get(name) is not None else means[name] - means[name]) / scales[name]
             for name in names] for row in feature_rows]


def _sigmoid(value):
    value = max(-35.0, min(35.0, value))
    return 1.0 / (1.0 + math.exp(-value))


def fit_logistic_regression(feature_rows, labels, learning_rate=.08, epochs=700, l2=.001):
    """Deterministic batch-gradient logistic regression; scaler is fitted on train only."""
    if len(feature_rows) != len(labels) or len(labels) < 2:
        raise ValueError("Training data is insufficient.")
    if len(set(labels)) < 2:
        raise ValueError("A binary model requires positive and negative training examples.")
    names, means, scales = _fit_scaler(feature_rows)
    matrix = _matrix(feature_rows, names, means, scales)
    weights = [0.0] * len(names)
    intercept = 0.0
    count = len(labels)
    for _ in range(epochs):
        weight_gradients = [0.0] * len(names)
        intercept_gradient = 0.0
        for vector, label in zip(matrix, labels):
            error = _sigmoid(intercept + sum(weight * value for weight, value in zip(weights, vector))) - label
            intercept_gradient += error
            for index, value in enumerate(vector):
                weight_gradients[index] += error * value
        intercept -= learning_rate * intercept_gradient / count
        weights = [weight - learning_rate * (gradient / count + l2 * weight)
                   for weight, gradient in zip(weights, weight_gradients)]
    return {"feature_names": names, "means": means, "scales": scales,
            "weights": weights, "intercept": intercept, "algorithm": "logistic_regression",
            "probability_calibration": "raw logistic score; calibration is reported diagnostically, not fitted"}


def predict_probability(model, feature_row):
    vector = [((float(feature_row[name]) if feature_row.get(name) is not None else model["means"][name])
               - model["means"][name]) / model["scales"][name] for name in model["feature_names"]]
    score = model["intercept"] + sum(weight * value for weight, value in zip(model["weights"], vector))
    return _sigmoid(score)


def _fit_linear(feature_rows, targets, epochs=350):
    names, means, scales = _fit_scaler(feature_rows)
    matrix = _matrix(feature_rows, names, means, scales)
    target_mean = sum(targets) / len(targets)
    weights = [0.0] * len(names)
    intercept = target_mean
    count = len(targets)
    for _ in range(epochs):
        gradients = [0.0] * len(names)
        intercept_gradient = 0.0
        for vector, actual in zip(matrix, targets):
            error = intercept + sum(weight * value for weight, value in zip(weights, vector)) - actual
            intercept_gradient += error
            for index, value in enumerate(vector):
                gradients[index] += error * value
        intercept -= .025 * intercept_gradient / count
        weights = [weight - .025 * gradient / count for weight, gradient in zip(weights, gradients)]
    return {"feature_names": names, "means": means, "scales": scales, "weights": weights,
            "intercept": intercept, "algorithm": "linear_regression", "target": "rainfall_anomaly_mm"}


def _predict_linear(model, feature_row):
    vector = [((float(feature_row[name]) if feature_row.get(name) is not None else model["means"][name])
               - model["means"][name]) / model["scales"][name] for name in model["feature_names"]]
    return model["intercept"] + sum(weight * value for weight, value in zip(model["weights"], vector))


def _fit_target(samples, target, horizon, min_test_samples, epochs):
    sample_rows = [sample for sample in samples if sample["labels"].get(target) is not None]
    train, validation, test, split = _chronological_split(sample_rows, len(samples) + horizon + 30, horizon)
    metric = {"target": target, "horizon_days": horizon, "train_n": len(train),
              "validation_n": len(validation), "test_n": len(test), **split,
              "precision": None, "recall": None, "f1": None, "roc_auc": None,
              "brier_score": None, "calibration": [], "mae": None, "rmse": None,
              "validated": False}
    if len(train) < 60 or len(test) < min_test_samples:
        metric["status"] = f"Insufficient labeled observations: need >=60 train and >={min_test_samples} held-out test rows."
        return None, metric
    labels_train = [sample["labels"][target] for sample in train]
    if len(set(labels_train)) < 2:
        metric["status"] = "Training period needs both positive and negative event examples."
        return None, metric
    try:
        model = fit_logistic_regression([sample["features"] for sample in train], labels_train, epochs=epochs)
    except ValueError as error:
        metric["status"] = str(error)
        return None, metric
    probabilities = [predict_probability(model, sample["features"]) for sample in test]
    labels = [sample["labels"][target] for sample in test]
    class_metrics = binary_classification_metrics(labels, probabilities)
    metric.update(class_metrics)
    metric["brier_score"] = brier_score(labels, probabilities)["brier"]
    metric["calibration"] = reliability_bins(labels, probabilities)
    metric["validated"] = len(set(labels)) == 2 and len(test) >= min_test_samples
    metric["status"] = "Chronological held-out metrics computed." if metric["validated"] else "Held-out data lacks both event classes; probability not validated."
    model.update({"target": target, "horizon_days": horizon, "metrics_key": f"{target}:{horizon}"})
    model["validated"] = metric["validated"]
    return model, metric


def _fit_anomaly(samples, horizon, min_test_samples, epochs):
    eligible = [sample for sample in samples if sample["rainfall_anomaly_mm"] is not None]
    train, validation, test, split = _chronological_split(eligible, len(samples) + horizon + 30, horizon)
    metric = {"target": "rainfall_anomaly_mm", "horizon_days": horizon, "train_n": len(train),
              "validation_n": len(validation), "test_n": len(test), **split,
              "precision": None, "recall": None, "f1": None, "roc_auc": None,
              "brier_score": None, "calibration": [], "mae": None, "rmse": None,
              "validated": False}
    if len(train) < 60 or len(test) < min_test_samples:
        metric["status"] = f"Insufficient rainfall normals or observations: need >=60 train and >={min_test_samples} held-out test rows."
        return None, metric
    model = _fit_linear([sample["features"] for sample in train], [sample["rainfall_anomaly_mm"] for sample in train], epochs)
    predictions = [_predict_linear(model, sample["features"]) for sample in test]
    metric.update(regression_metrics([sample["rainfall_anomaly_mm"] for sample in test], predictions))
    metric["validated"] = True
    metric["status"] = "Chronological held-out metrics computed." 
    model.update({"horizon_days": horizon, "metrics_key": f"rainfall_anomaly_mm:{horizon}", "validated": True})
    return model, metric


def train_location_model(rows, location_id, min_test_samples=30, epochs=250, regression_epochs=350):
    rows = sorted((row for row in rows if row.get("location_id") == location_id), key=lambda row: row["date"])
    if len(rows) < 365:
        raise ValueError("At least one year of daily observations is required before training; multi-year local data is recommended.")
    models = {}
    metrics = {}
    ranges = []
    for horizon in HORIZONS:
        samples = build_samples(rows, horizon)
        for target in TARGETS:
            model, metric = _fit_target(samples, target, horizon, min_test_samples, epochs)
            metrics[f"{target}:{horizon}"] = metric
            if model:
                models[f"{target}:{horizon}"] = model
        model, metric = _fit_anomaly(samples, horizon, min_test_samples, regression_epochs)
        metrics[f"rainfall_anomaly_mm:{horizon}"] = metric
        if model:
            models[f"rainfall_anomaly_mm:{horizon}"] = model
        ranges.extend([metric[key] for key in ("training_start", "test_end") if metric.get(key)])
    validated_count = sum(bool(metric.get("validated")) for metric in metrics.values())
    version = f"agrishield-logreg-{uuid4().hex[:12]}"
    created = datetime.now(timezone.utc).isoformat()
    run = {
        "model_version": version, "location_id": location_id,
        "algorithm": "deterministic logistic regression + linear regression; horizon-specific",
        "status": "partially_validated" if validated_count else "not_validated",
        "validated": validated_count > 0,
        "training_start": min((item["training_start"] for item in metrics.values() if item.get("training_start")), default=None),
        "training_end": max((item["training_end"] for item in metrics.values() if item.get("training_end")), default=None),
        "validation_start": min((item["validation_start"] for item in metrics.values() if item.get("validation_start")), default=None),
        "validation_end": max((item["validation_end"] for item in metrics.values() if item.get("validation_end")), default=None),
        "test_start": min((item["test_start"] for item in metrics.values() if item.get("test_start")), default=None),
        "test_end": max((item["test_end"] for item in metrics.values() if item.get("test_end")), default=None),
        "sample_count": len(rows), "data_timestamp": max(row["date"] for row in rows),
        "models": models, "metrics": metrics, "created_at": created,
    }
    return run


def forecast_with_model_run(rows, run):
    rows = sorted(rows, key=lambda row: row["date"])
    if not rows:
        return {str(horizon): {"available": False, "reason": "No local observations are available."} for horizon in HORIZONS}
    features = _derive_features(rows)[-1]
    output = {}
    for horizon in HORIZONS:
        event_values = {}
        for target in (*TARGETS, "rainfall_anomaly_mm"):
            model = run.get("models", {}).get(f"{target}:{horizon}")
            event_values[target] = None
            if model and model.get("validated"):
                value = _predict_linear(model, features) if target == "rainfall_anomaly_mm" else predict_probability(model, features)
                event_values[target] = value
        output[str(horizon)] = {
            "available": any(value is not None for value in event_values.values()),
            "horizon_days": horizon,
            "predictions": event_values,
            "model_version": run["model_version"],
            "forecast_timestamp": datetime.now(timezone.utc).isoformat(),
            "data_timestamp": run.get("data_timestamp"),
            "location_id": run.get("location_id"),
            "validated": any(value is not None for value in event_values.values()),
            "calibration_status": "Raw logistic probabilities; see held-out reliability bins. No calibration layer has been fitted.",
        }
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--location-id", required=True, help="Exact imported location_id")
    parser.add_argument("--min-test-samples", type=int, default=30)
    parser.add_argument("--epochs", type=int, default=250)
    parser.add_argument("--regression-epochs", type=int, default=350)
    args = parser.parse_args()
    database.init_db()
    rows = database.get_climate_observations(args.location_id)
    run = train_location_model(rows, args.location_id, args.min_test_samples, args.epochs, args.regression_epochs)
    database.save_model_run(run)
    print(f"Saved {run['model_version']} for {args.location_id}: {run['status']} (n={run['sample_count']}).")
    for key, metric in run["metrics"].items():
        print(f"{key}: {metric['status']} n_test={metric['test_n']} brier={metric['brier_score']} MAE={metric['mae']} RMSE={metric['rmse']}")


if __name__ == "__main__":
    main()
