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


def parse_date(value):
    if isinstance(value, date):
        return value
    if not value:
        raise ValueError("A real sowing date is required to calculate crop age.")
    return datetime.fromisoformat(str(value)[:10]).date()


def days_since(planting_date, scan_date=None):
    planted = parse_date(planting_date)
    scanned = parse_date(scan_date) if scan_date else date.today()
    return max((scanned - planted).days, 0)


def estimate_growth_stage(crop_name, planting_date, scan_date=None, calendar_rules=None):
    planted = parse_date(planting_date)
    reference_day = parse_date(scan_date) if scan_date else date.today()
    if planted > reference_day:
        return {
            "days_since_planting": None,
            "growth_stage": "Not planted yet",
            "next_stage": "Establishment / planting",
            "days_to_next_stage": (planted - reference_day).days,
            "lifecycle_source": "Planned sowing date",
            "lifecycle_available": True,
        }
    day_count = max((reference_day - planted).days, 0)
    key = (crop_name or "").strip().lower()
    rules = []
    for item in (calendar_rules or []):
        try:
            rules.append((int(item["day"]), str(item["stage"])))
        except (KeyError, TypeError, ValueError):
            continue
    source = "Imported crop calendar"
    if not rules:
        rules = STAGE_RULES.get(key)
        source = "Configured crop lifecycle estimates; not locally calibrated"
    if not rules:
        return {
            "days_since_planting": day_count,
            "growth_stage": "Crop calendar unavailable",
            "next_stage": None,
            "days_to_next_stage": None,
            "lifecycle_source": "No configured lifecycle for this crop",
            "lifecycle_available": False,
        }

    stage = rules[0][1]
    next_stage = None
    days_to_next_stage = None
    for index, (threshold, label) in enumerate(rules):
        if day_count >= threshold:
            stage = label
        else:
            next_stage = label
            days_to_next_stage = threshold - day_count
            break

    return {
        "days_since_planting": day_count,
        "growth_stage": stage,
        "next_stage": next_stage,
        "days_to_next_stage": days_to_next_stage,
        "lifecycle_source": source,
        "lifecycle_available": True,
    }
