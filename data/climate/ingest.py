"""Validate and persist canonical climate CSV observations into SQLite."""
import argparse
import csv
from pathlib import Path

import database
from data.climate.preprocessing import normalize_observation


def load_csv(path, location_id=None, source=None):
    with Path(path).open("r", newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        required = {"date", "rainfall_mm"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError("Climate CSV must include date and rainfall_mm columns.")
        rows = [normalize_observation(row, location_id, source, index)
                for index, row in enumerate(reader, start=2)]
    if not rows:
        raise ValueError("Climate CSV has no observation rows.")
    return rows


def ingest_csv(path, location_id=None, source=None):
    database.init_db()
    rows = load_csv(path, location_id, source)
    locations = {row["location_id"] for row in rows}
    if len(locations) != 1:
        raise ValueError("Import one location_id per CSV file to keep spatial alignment explicit.")
    return database.upsert_climate_observations(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Daily canonical CSV file")
    parser.add_argument("--location-id", help="Use one explicit location id when omitted from CSV")
    parser.add_argument("--source", help="Source label when omitted from CSV")
    args = parser.parse_args()
    count = ingest_csv(args.input, args.location_id, args.source)
    print(f"Stored {count} validated daily observations in {database.DB_PATH}.")


if __name__ == "__main__":
    main()
