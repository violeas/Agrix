from datetime import date, datetime


STAGE_RULES = {
    "tomato": [
        (0, "Germination / establishment"),
        (15, "Seedling"),
        (35, "Vegetative"),
        (60, "Flowering"),
        (85, "Fruiting"),
        (110, "Harvest / late season"),
    ],
    "maize": [
        (0, "Germination / emergence"),
        (12, "Seedling"),
        (30, "Vegetative"),
        (55, "Tasseling / silking"),
        (75, "Grain fill"),
        (105, "Maturity / harvest"),
    ],
    "corn": [
        (0, "Germination / emergence"),
        (12, "Seedling"),
        (30, "Vegetative"),
        (55, "Tasseling / silking"),
        (75, "Grain fill"),
        (105, "Maturity / harvest"),
    ],
    "potato": [
        (0, "Sprout development"),
        (18, "Vegetative"),
        (35, "Tuber initiation"),
        (60, "Tuber bulking"),
        (90, "Maturation"),
        (110, "Harvest window"),
    ],
    "rose": [
        (0, "Establishment"),
        (20, "Vegetative growth"),
        (45, "Bud development"),
        (60, "Flowering"),
        (90, "Maintenance / pruning cycle"),
    ],
}


GENERIC_RULES = [
    (0, "Establishment"),
    (20, "Vegetative"),
    (45, "Flowering / reproductive"),
    (75, "Maturity"),
    (105, "Harvest / maintenance"),
]


def parse_date(value):
    if isinstance(value, date):
        return value
    if not value:
        return date.today()
    return datetime.fromisoformat(str(value)[:10]).date()


def days_since(planting_date, scan_date=None):
    planted = parse_date(planting_date)
    scanned = parse_date(scan_date) if scan_date else date.today()
    return max((scanned - planted).days, 0)


def estimate_growth_stage(crop_name, planting_date, scan_date=None):
    day_count = days_since(planting_date, scan_date)
    key = (crop_name or "").strip().lower()
    rules = STAGE_RULES.get(key, GENERIC_RULES)

    stage = rules[0][1]
    for threshold, label in rules:
        if day_count >= threshold:
            stage = label
        else:
            break

    return {
        "days_since_planting": day_count,
        "growth_stage": stage,
        "label": "Estimated growth stage",
    }
