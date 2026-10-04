"""Forecast evaluation primitives for rolling-origin, location-held-out validation."""
from math import sqrt


def regression_metrics(actual, predicted):
    pairs = [(float(obs), float(pred)) for obs, pred in zip(actual, predicted) if obs is not None and pred is not None]
    if not pairs:
        return {"n": 0, "mae": None, "rmse": None}
    errors = [pred - obs for obs, pred in pairs]
    return {"n": len(pairs), "mae": sum(abs(error) for error in errors) / len(errors),
            "rmse": sqrt(sum(error * error for error in errors) / len(errors))}


def brier_score(actual, probability):
    pairs = [(float(obs), float(prob)) for obs, prob in zip(actual, probability) if obs is not None and prob is not None]
    return {"n": len(pairs), "brier": sum((prob - obs) ** 2 for obs, prob in pairs) / len(pairs) if pairs else None}


def binary_classification_metrics(actual, probability, threshold=.5):
    pairs = [(bool(obs), float(prob)) for obs, prob in zip(actual, probability) if obs is not None and prob is not None]
    tp = sum(obs and prob >= threshold for obs, prob in pairs)
    fp = sum(not obs and prob >= threshold for obs, prob in pairs)
    fn = sum(obs and prob < threshold for obs, prob in pairs)
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * precision * recall / (precision + recall) if precision is not None and recall is not None and precision + recall else 0.0 if precision is not None and recall is not None else None
    positives = [prob for obs, prob in pairs if obs]
    negatives = [prob for obs, prob in pairs if not obs]
    auc = (sum(1 if pos > neg else .5 if pos == neg else 0 for pos in positives for neg in negatives)
           / (len(positives) * len(negatives))) if positives and negatives else None
    return {"n": len(pairs), "precision": precision, "recall": recall, "f1": f1,
            "roc_auc": auc, "true_positive": tp, "false_positive": fp,
            "false_negative": fn, "threshold": threshold}


def reliability_bins(actual, probability, bins=10):
    groups = [[] for _ in range(bins)]
    for obs, prob in zip(actual, probability):
        if obs is None or prob is None:
            continue
        index = min(bins - 1, max(0, int(float(prob) * bins)))
        groups[index].append((float(obs), float(prob)))
    return [{"lower": index / bins, "upper": (index + 1) / bins,
             "n": len(group), "mean_probability": sum(prob for _, prob in group) / len(group) if group else None,
             "observed_frequency": sum(obs for obs, _ in group) / len(group) if group else None}
            for index, group in enumerate(groups)]
