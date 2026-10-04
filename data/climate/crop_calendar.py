"""Import authoritative, location-specific crop calendar CSV rows into SQLite.

CSV columns: location_id,crop_name,source,sowing_start,sowing_end,
water_requirement_mm_day,lifecycle_stages_json,version. Lifecycle stages are a
JSON array such as [{"day":0,"stage":"Establishment"}]. No sample calendar is bundled.
"""
import argparse
import csv
import json
from datetime import date
from pathlib import Path

import database


def _month_day(value, field):
    value = (value or "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(f"2000-{value}").strftime("%m-%d")
    except ValueError as error:
        raise ValueError(f"{field} must use a valid MM-DD date.") from error


def _stages(value):
    if not value:
        return []
    try:
        items = json.loads(value)
    except json.JSONDecodeError as error:
        raise ValueError("lifecycle_stages_json must be a JSON array.") from error
    if not isinstance(items, list):
        raise ValueError("lifecycle_stages_json must be a JSON array.")
    stages = []
    for item in items:
        if not isinstance(item, dict) or not str(item.get("stage", "")).strip():
            raise ValueError("Each crop calendar stage needs a day and stage label.")
        try:
            day = int(item["day"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("Each crop calendar stage day must be a non-negative integer.") from error
        if day < 0:
            raise ValueError("Crop calendar stage days must be non-negative.")
        stages.append({"day": day, "stage": str(item["stage"]).strip()[:100]})
    stages.sort(key=lambda item: item["day"])
    if len({item["day"] for item in stages}) != len(stages):
        raise ValueError("Crop calendar stage days must be unique.")
    if stages and stages[0]["day"] != 0:
        raise ValueError("A lifecycle calendar must start at day 0 from the recorded sowing date.")
    return stages


def load_csv(path):
    with Path(path).open("r", newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        required = {"location_id", "crop_name", "source"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError("Crop calendar CSV requires location_id, crop_name and source columns.")
        rows = []
        for line_number, row in enumerate(reader, start=2):
            location_id = (row.get("location_id") or "").strip()
            crop_name = (row.get("crop_name") or "").strip()
            source = (row.get("source") or "").strip()
            if not location_id or not crop_name or not source:
                raise ValueError(f"CSV row {line_number} is missing location_id, crop_name or source.")
            water = (row.get("water_requirement_mm_day") or "").strip()
            try:
                water = float(water) if water else None
            except ValueError as error:
                raise ValueError(f"CSV row {line_number} has an invalid water requirement.") from error
            if water is not None and water <= 0:
                raise ValueError(f"CSV row {line_number} water requirement must be positive.")
            rows.append({
                "location_id": location_id,
                "crop_name": crop_name,
                "source": source,
                "sowing_start": _month_day(row.get("sowing_start"), "sowing_start"),
                "sowing_end": _month_day(row.get("sowing_end"), "sowing_end"),
                "water_requirement_mm_day": water,
                "lifecycle_stages": _stages(row.get("lifecycle_stages_json")),
                "version": (row.get("version") or "").strip() or None,
            })
    if not rows:
        raise ValueError("Crop calendar CSV contains no rows.")
    return rows


def ingest_csv(path):
    database.init_db()
    rows = load_csv(path)
    database.upsert_crop_calendar_rules(rows)
    return len(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Authoritative crop-calendar CSV")
    args = parser.parse_args()
    print(f"Stored {ingest_csv(args.input)} crop calendar rows in {database.DB_PATH}.")


if __name__ == "__main__":
    main()
