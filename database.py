import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("AGRISHIELD_DB_PATH", BASE_DIR / "agrishield.db"))


def utc_now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def init_db():
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS crops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crop_name TEXT NOT NULL,
                field_name TEXT NOT NULL,
                planting_date TEXT NOT NULL,
                location TEXT DEFAULT '',
                latitude REAL,
                longitude REAL,
                state TEXT,
                district TEXT,
                block TEXT,
                village_cluster TEXT,
                field_area REAL,
                field_area_unit TEXT DEFAULT 'acre',
                irrigation_type TEXT DEFAULT '',
                location_id TEXT,
                notes TEXT DEFAULT '',
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crop_id INTEGER NOT NULL,
                scan_date TEXT NOT NULL,
                image_path TEXT NOT NULL,
                description TEXT DEFAULT '',
                growth_stage TEXT DEFAULT 'Unknown',
                created_at TEXT NOT NULL,
                FOREIGN KEY (crop_id) REFERENCES crops(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS diagnosis_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_id INTEGER NOT NULL UNIQUE,
                crop_name TEXT NOT NULL,
                diagnosis TEXT NOT NULL,
                diagnosis_status TEXT NOT NULL,
                reliability TEXT NOT NULL,
                model_confidence REAL,
                severity TEXT NOT NULL,
                health_status TEXT NOT NULL,
                health_score INTEGER,
                evidence TEXT NOT NULL,
                possible_causes TEXT NOT NULL,
                recommendations TEXT NOT NULL,
                precautions TEXT NOT NULL,
                do_not TEXT NOT NULL,
                next_check TEXT NOT NULL,
                follow_up TEXT NOT NULL,
                model_label TEXT DEFAULT '',
                model_note TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS quick_diagnoses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crop_name TEXT NOT NULL,
                image_path TEXT NOT NULL,
                description TEXT DEFAULT '',
                diagnosis_status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS app_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS climate_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location_id TEXT NOT NULL,
                observation_date TEXT NOT NULL,
                rainfall_mm REAL,
                temperature_c REAL,
                humidity_percent REAL,
                wind_kmh REAL,
                pressure_hpa REAL,
                enso_index REAL,
                iod_index REAL,
                mjo_rmm1 REAL,
                mjo_rmm2 REAL,
                mjo_phase REAL,
                mjo_amplitude REAL,
                normal_rainfall_mm REAL,
                onset_event INTEGER,
                false_onset_event INTEGER,
                source TEXT NOT NULL,
                ingested_at TEXT NOT NULL,
                UNIQUE(location_id, observation_date, source)
            );

            CREATE INDEX IF NOT EXISTS climate_observations_location_date
                ON climate_observations(location_id, observation_date);

            CREATE TABLE IF NOT EXISTS crop_calendar_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location_id TEXT NOT NULL,
                crop_name TEXT NOT NULL,
                sowing_start TEXT,
                sowing_end TEXT,
                water_requirement_mm_day REAL,
                lifecycle_json TEXT NOT NULL DEFAULT '[]',
                source TEXT NOT NULL,
                version TEXT,
                imported_at TEXT NOT NULL,
                UNIQUE(location_id, crop_name, source)
            );

            CREATE INDEX IF NOT EXISTS crop_calendar_location_crop
                ON crop_calendar_rules(location_id, crop_name, imported_at DESC);

            CREATE TABLE IF NOT EXISTS monsoon_model_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_version TEXT NOT NULL UNIQUE,
                location_id TEXT NOT NULL,
                algorithm TEXT NOT NULL,
                status TEXT NOT NULL,
                validated INTEGER NOT NULL DEFAULT 0,
                training_start TEXT,
                training_end TEXT,
                validation_start TEXT,
                validation_end TEXT,
                test_start TEXT,
                test_end TEXT,
                sample_count INTEGER NOT NULL DEFAULT 0,
                data_timestamp TEXT,
                models_json TEXT NOT NULL,
                metrics_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS monsoon_model_runs_location
                ON monsoon_model_runs(location_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS monsoon_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location_id TEXT NOT NULL,
                alert_key TEXT NOT NULL UNIQUE,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                source TEXT NOT NULL,
                probability REAL,
                horizon_days INTEGER,
                data_timestamp TEXT,
                forecast_timestamp TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                acknowledged_at TEXT,
                created_at TEXT NOT NULL
            );
            """
        )
        ensure_column(connection, "crops", "latitude", "REAL")
        ensure_column(connection, "crops", "longitude", "REAL")
        ensure_column(connection, "crops", "state", "TEXT")
        ensure_column(connection, "crops", "district", "TEXT")
        ensure_column(connection, "crops", "block", "TEXT")
        ensure_column(connection, "crops", "village_cluster", "TEXT")
        ensure_column(connection, "crops", "field_area", "REAL")
        ensure_column(connection, "crops", "field_area_unit", "TEXT DEFAULT 'acre'")
        ensure_column(connection, "crops", "irrigation_type", "TEXT DEFAULT ''")
        ensure_column(connection, "crops", "location_id", "TEXT")
        ensure_column(connection, "diagnosis_results", "visual_indicators", "TEXT NOT NULL DEFAULT '[]'")
        ensure_column(connection, "diagnosis_results", "preventive_measures", "TEXT NOT NULL DEFAULT '[]'")
        ensure_column(connection, "diagnosis_results", "medicine_guidance", "TEXT NOT NULL DEFAULT '[]'")
        ensure_column(connection, "diagnosis_results", "fertilizer_guidance", "TEXT NOT NULL DEFAULT '[]'")
        ensure_column(connection, "diagnosis_results", "natural_remedies", "TEXT NOT NULL DEFAULT '[]'")
        ensure_column(connection, "diagnosis_results", "expert_confirmation", "TEXT NOT NULL DEFAULT ''")
        ensure_column(connection, "diagnosis_results", "description_alignment", "TEXT NOT NULL DEFAULT ''")
        ensure_column(connection, "diagnosis_results", "top_predictions", "TEXT NOT NULL DEFAULT '[]'")
        ensure_column(connection, "monsoon_alerts", "probability", "REAL")
        ensure_column(connection, "monsoon_alerts", "horizon_days", "INTEGER")


def ensure_column(connection, table, column, declaration):
    columns = [row["name"] for row in connection.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")


def to_json(value):
    return json.dumps(value or [], ensure_ascii=False)


def from_json(value):
    if value in (None, ""):
        return []
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return []


def row_to_crop(row):
    if row is None:
        return None
    return {
        "id": row["id"],
        "crop_name": row["crop_name"],
        "field_name": row["field_name"],
        "planting_date": row["planting_date"],
        "location": row["location"] or "",
        "latitude": row["latitude"] if "latitude" in row.keys() else None,
        "longitude": row["longitude"] if "longitude" in row.keys() else None,
        "state": row["state"] if "state" in row.keys() else None,
        "district": row["district"] if "district" in row.keys() else None,
        "block": row["block"] if "block" in row.keys() else None,
        "village_cluster": row["village_cluster"] if "village_cluster" in row.keys() else None,
        "field_area": row["field_area"] if "field_area" in row.keys() else None,
        "field_area_unit": row["field_area_unit"] if "field_area_unit" in row.keys() else "acre",
        "irrigation_type": row["irrigation_type"] if "irrigation_type" in row.keys() else "",
        "location_id": row["location_id"] if "location_id" in row.keys() else None,
        "notes": row["notes"] or "",
        "status": row["status"] or "active",
        "created_at": row["created_at"],
    }


def row_to_scan(row):
    if row is None:
        return None

    scan = {
        "id": row["scan_id"] if "scan_id" in row.keys() else row["id"],
        "crop_id": row["crop_id"],
        "scan_date": row["scan_date"],
        "image_path": row["image_path"],
        "image_url": f"/uploads/{Path(row['image_path']).name}",
        "description": row["description"] or "",
        "growth_stage": row["growth_stage"] or "Unknown",
        "created_at": row["created_at"],
    }

    if "diagnosis" in row.keys() and row["diagnosis"] is not None:
        scan.update(
            {
                "crop_name": row["crop_name"],
                "diagnosis": row["diagnosis"],
                "diagnosis_status": row["diagnosis_status"],
                "reliability": row["reliability"],
                "model_confidence": row["model_confidence"],
                "severity": row["severity"],
                "health_status": row["health_status"],
                "health_score": row["health_score"],
                "evidence": from_json(row["evidence"]),
                "possible_causes": from_json(row["possible_causes"]),
                "recommendations": from_json(row["recommendations"]),
                "visual_indicators": from_json(row["visual_indicators"]) if "visual_indicators" in row.keys() else [],
                "preventive_measures": from_json(row["preventive_measures"]) if "preventive_measures" in row.keys() else [],
                "medicine_guidance": from_json(row["medicine_guidance"]) if "medicine_guidance" in row.keys() else [],
                "fertilizer_guidance": from_json(row["fertilizer_guidance"]) if "fertilizer_guidance" in row.keys() else [],
                "natural_remedies": from_json(row["natural_remedies"]) if "natural_remedies" in row.keys() else [],
                "expert_confirmation": row["expert_confirmation"] if "expert_confirmation" in row.keys() else "",
                "description_alignment": row["description_alignment"] if "description_alignment" in row.keys() else "",
                "top_predictions": from_json(row["top_predictions"]) if "top_predictions" in row.keys() else [],
                "precautions": from_json(row["precautions"]),
                "do_not": from_json(row["do_not"]),
                "next_check": from_json(row["next_check"]),
                "follow_up": row["follow_up"],
                "model_label": row["model_label"],
                "model_note": row["model_note"],
            }
        )

    return scan


def create_crop(crop):
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO crops (
                crop_name, field_name, planting_date, location, latitude, longitude,
                state, district, block, village_cluster, field_area, field_area_unit,
                irrigation_type, location_id, notes, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                crop["crop_name"].strip(),
                crop["field_name"].strip(),
                crop["planting_date"],
                crop.get("location", "").strip(),
                crop.get("latitude"), crop.get("longitude"), crop.get("state"),
                crop.get("district"), crop.get("block"), crop.get("village_cluster"),
                crop.get("field_area"), crop.get("field_area_unit", "acre"),
                crop.get("irrigation_type", ""), crop.get("location_id"),
                crop.get("notes", "").strip(), crop.get("status", "active"),
                utc_now(),
            ),
        )
        crop_id = cursor.lastrowid
        return get_crop(crop_id, connection)


def get_crop(crop_id, connection=None):
    close_connection = connection is None
    if connection is None:
        connection = sqlite3.connect(DB_PATH)
        connection.row_factory = sqlite3.Row
    try:
        connection.execute("UPDATE crops SET status='active' WHERE id=? AND status='planned' AND planting_date<=?",
                           (crop_id, date.today().isoformat()))
        if close_connection:
            connection.commit()
        row = connection.execute("SELECT * FROM crops WHERE id = ?", (crop_id,)).fetchone()
        return row_to_crop(row)
    finally:
        if close_connection:
            connection.close()


def list_crops():
    with get_connection() as connection:
        connection.execute("UPDATE crops SET status='active' WHERE status='planned' AND planting_date<=?",
                           (date.today().isoformat(),))
        rows = connection.execute(
            "SELECT * FROM crops WHERE COALESCE(status, 'active') IN ('active', 'planned') ORDER BY created_at DESC, id DESC"
        ).fetchall()
        return [row_to_crop(row) for row in rows]


def update_crop(crop_id, crop):
    with get_connection() as connection:
        cursor = connection.execute(
            """UPDATE crops SET crop_name=?, field_name=?, planting_date=?, location=?,
               latitude=?, longitude=?, state=?, district=?, block=?, village_cluster=?,
               field_area=?, field_area_unit=?, irrigation_type=?, location_id=?, notes=?, status=?
               WHERE id=? AND COALESCE(status, 'active') IN ('active', 'planned')""",
            (crop["crop_name"].strip(), crop["field_name"].strip(), crop["planting_date"],
             crop.get("location", "").strip(), crop.get("latitude"), crop.get("longitude"),
             crop.get("state"), crop.get("district"), crop.get("block"), crop.get("village_cluster"),
             crop.get("field_area"), crop.get("field_area_unit", "acre"), crop.get("irrigation_type", ""),
             crop.get("location_id"), crop.get("notes", "").strip(), crop.get("status", "active"), crop_id),
        )
        if cursor.rowcount == 0:
            return None
    return get_crop(crop_id)


def archive_crop(crop_id):
    with get_connection() as connection:
        cursor = connection.execute(
            "UPDATE crops SET status='archived' WHERE id=? AND COALESCE(status, 'active') IN ('active', 'planned')",
            (crop_id,),
        )
        return cursor.rowcount > 0


CLIMATE_VALUE_FIELDS = (
    "rainfall_mm", "temperature_c", "humidity_percent", "wind_kmh", "pressure_hpa",
    "enso_index", "iod_index", "mjo_rmm1", "mjo_rmm2", "mjo_phase", "mjo_amplitude",
    "normal_rainfall_mm", "onset_event", "false_onset_event",
)


def upsert_climate_observations(rows):
    ingested_at = utc_now()
    with get_connection() as connection:
        for row in rows:
            values = [row.get(field) for field in CLIMATE_VALUE_FIELDS]
            connection.execute(
                """INSERT INTO climate_observations (
                    location_id, observation_date, rainfall_mm, temperature_c, humidity_percent,
                    wind_kmh, pressure_hpa, enso_index, iod_index, mjo_rmm1, mjo_rmm2,
                    mjo_phase, mjo_amplitude, normal_rainfall_mm, onset_event,
                    false_onset_event, source, ingested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(location_id, observation_date, source) DO UPDATE SET
                    rainfall_mm=excluded.rainfall_mm, temperature_c=excluded.temperature_c,
                    humidity_percent=excluded.humidity_percent, wind_kmh=excluded.wind_kmh,
                    pressure_hpa=excluded.pressure_hpa, enso_index=excluded.enso_index,
                    iod_index=excluded.iod_index, mjo_rmm1=excluded.mjo_rmm1,
                    mjo_rmm2=excluded.mjo_rmm2, mjo_phase=excluded.mjo_phase,
                    mjo_amplitude=excluded.mjo_amplitude, normal_rainfall_mm=excluded.normal_rainfall_mm,
                    onset_event=excluded.onset_event, false_onset_event=excluded.false_onset_event,
                    ingested_at=excluded.ingested_at""",
                [row["location_id"], row["date"], *values, row["source"], ingested_at],
            )
    return len(rows)


def upsert_crop_calendar_rules(rows):
    imported_at = utc_now()
    with get_connection() as connection:
        for row in rows:
            connection.execute(
                """INSERT INTO crop_calendar_rules (
                    location_id, crop_name, sowing_start, sowing_end,
                    water_requirement_mm_day, lifecycle_json, source, version, imported_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(location_id, crop_name, source) DO UPDATE SET
                    sowing_start=excluded.sowing_start, sowing_end=excluded.sowing_end,
                    water_requirement_mm_day=excluded.water_requirement_mm_day,
                    lifecycle_json=excluded.lifecycle_json, version=excluded.version,
                    imported_at=excluded.imported_at""",
                (row["location_id"], row["crop_name"], row.get("sowing_start"),
                 row.get("sowing_end"), row.get("water_requirement_mm_day"),
                 json.dumps(row.get("lifecycle_stages", []), ensure_ascii=False),
                 row["source"], row.get("version"), imported_at),
            )
    return len(rows)


def get_crop_calendar_rule(location_id, crop_name):
    if not location_id or not crop_name:
        return None
    with get_connection() as connection:
        row = connection.execute(
            """SELECT * FROM crop_calendar_rules WHERE location_id=? AND lower(crop_name)=lower(?)
               ORDER BY imported_at DESC, id DESC LIMIT 1""",
            (location_id, crop_name),
        ).fetchone()
    if row is None:
        return None
    result = dict(row)
    result["lifecycle_stages"] = from_json(result.pop("lifecycle_json"))
    return result


def get_climate_observations(location_id, limit=None):
    sql = "SELECT * FROM climate_observations WHERE location_id=? ORDER BY observation_date"
    params = [location_id]
    if limit:
        sql += " DESC LIMIT ?"
        params.append(int(limit))
    with get_connection() as connection:
        rows = connection.execute(sql, params).fetchall()
    output = [dict(row) for row in rows]
    if limit:
        output.reverse()
    for row in output:
        row["date"] = row.pop("observation_date")
        row.pop("id", None)
        row.pop("ingested_at", None)
    return output


def save_model_run(run):
    with get_connection() as connection:
        connection.execute(
            """INSERT INTO monsoon_model_runs (
                model_version, location_id, algorithm, status, validated,
                training_start, training_end, validation_start, validation_end,
                test_start, test_end, sample_count, data_timestamp,
                models_json, metrics_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (run["model_version"], run["location_id"], run["algorithm"], run["status"],
             int(bool(run.get("validated"))), run.get("training_start"), run.get("training_end"),
             run.get("validation_start"), run.get("validation_end"), run.get("test_start"),
             run.get("test_end"), int(run.get("sample_count", 0)), run.get("data_timestamp"),
             json.dumps(run.get("models", {}), ensure_ascii=False),
             json.dumps(run.get("metrics", {}), ensure_ascii=False), run.get("created_at", utc_now())),
        )
    return run


def _row_to_model_run(row):
    if row is None:
        return None
    run = dict(row)
    run["validated"] = bool(run["validated"])
    run["models"] = from_json(run.pop("models_json"))
    run["metrics"] = from_json(run.pop("metrics_json"))
    return run


def list_model_runs(location_id=None):
    with get_connection() as connection:
        if location_id:
            rows = connection.execute(
                "SELECT * FROM monsoon_model_runs WHERE location_id=? ORDER BY created_at DESC",
                (location_id,),
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT * FROM monsoon_model_runs ORDER BY created_at DESC"
            ).fetchall()
    return [_row_to_model_run(row) for row in rows]


def latest_validated_model_run(location_id):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM monsoon_model_runs WHERE location_id=? AND validated=1 ORDER BY created_at DESC LIMIT 1",
            (location_id,),
        ).fetchone()
    return _row_to_model_run(row)


def upsert_monsoon_alerts(location_id, alerts):
    now = utc_now()
    with get_connection() as connection:
        for alert in alerts:
            connection.execute(
                """INSERT INTO monsoon_alerts (
                    location_id, alert_key, alert_type, severity, title, message, source,
                    probability, horizon_days, data_timestamp, forecast_timestamp, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)
                ON CONFLICT(alert_key) DO UPDATE SET severity=excluded.severity,
                    title=excluded.title, message=excluded.message, source=excluded.source,
                    probability=excluded.probability, horizon_days=excluded.horizon_days,
                    data_timestamp=excluded.data_timestamp, forecast_timestamp=excluded.forecast_timestamp""",
                (location_id, alert["alert_key"], alert["alert_type"], alert["severity"],
                 alert["title"], alert["message"], alert["source"], alert.get("probability"),
                 alert.get("horizon_days"), alert.get("data_timestamp"), alert["forecast_timestamp"], now),
            )
    return list_monsoon_alerts(location_id)


def list_monsoon_alerts(location_id=None):
    query = "SELECT * FROM monsoon_alerts"
    params = []
    if location_id:
        query += " WHERE location_id=?"
        params.append(location_id)
    query += " ORDER BY CASE severity WHEN 'high' THEN 0 WHEN 'moderate' THEN 1 ELSE 2 END, created_at DESC"
    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def acknowledge_monsoon_alert(alert_id):
    with get_connection() as connection:
        cursor = connection.execute(
            "UPDATE monsoon_alerts SET status='acknowledged', acknowledged_at=? WHERE id=? AND status='active'",
            (utc_now(), alert_id),
        )
        return cursor.rowcount > 0


def create_scan(crop_id, image_path, scan_date, description, growth_stage, diagnosis):
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO scans (
                crop_id, scan_date, image_path, description, growth_stage, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                crop_id,
                scan_date,
                image_path,
                description or "",
                growth_stage or "Unknown",
                utc_now(),
            ),
        )
        scan_id = cursor.lastrowid
        connection.execute(
            """
            INSERT INTO diagnosis_results (
                scan_id, crop_name, diagnosis, diagnosis_status, reliability,
                model_confidence, severity, health_status, health_score, evidence,
                possible_causes, recommendations, precautions, do_not, next_check,
                follow_up, model_label, model_note, visual_indicators,
                preventive_measures, medicine_guidance, fertilizer_guidance,
                natural_remedies, expert_confirmation, description_alignment,
                top_predictions, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scan_id,
                diagnosis["crop_name"],
                diagnosis["diagnosis"],
                diagnosis["diagnosis_status"],
                diagnosis["reliability"],
                diagnosis.get("model_confidence"),
                diagnosis["severity"],
                diagnosis["health_status"],
                diagnosis.get("health_score"),
                to_json(diagnosis.get("evidence")),
                to_json(diagnosis.get("possible_causes")),
                to_json(diagnosis.get("recommendations")),
                to_json(diagnosis.get("precautions")),
                to_json(diagnosis.get("do_not")),
                to_json(diagnosis.get("next_check")),
                diagnosis["follow_up"],
                diagnosis.get("model_label", ""),
                diagnosis.get("model_note", ""),
                to_json(diagnosis.get("visual_indicators")),
                to_json(diagnosis.get("preventive_measures")),
                to_json(diagnosis.get("medicine_guidance")),
                to_json(diagnosis.get("fertilizer_guidance")),
                to_json(diagnosis.get("natural_remedies")),
                diagnosis.get("expert_confirmation", ""),
                diagnosis.get("description_alignment", ""),
                to_json(diagnosis.get("top_predictions")),
                utc_now(),
            ),
        )
        return get_scan(scan_id, connection)


def get_scan(scan_id, connection=None):
    close_connection = connection is None
    if connection is None:
        connection = sqlite3.connect(DB_PATH)
        connection.row_factory = sqlite3.Row
    try:
        row = connection.execute(
            """
            SELECT
                scans.id AS scan_id,
                scans.crop_id,
                scans.scan_date,
                scans.image_path,
                scans.description,
                scans.growth_stage,
                scans.created_at,
                diagnosis_results.crop_name,
                diagnosis_results.diagnosis,
                diagnosis_results.diagnosis_status,
                diagnosis_results.reliability,
                diagnosis_results.model_confidence,
                diagnosis_results.severity,
                diagnosis_results.health_status,
                diagnosis_results.health_score,
                diagnosis_results.evidence,
                diagnosis_results.possible_causes,
                diagnosis_results.recommendations,
                diagnosis_results.visual_indicators,
                diagnosis_results.preventive_measures,
                diagnosis_results.medicine_guidance,
                diagnosis_results.fertilizer_guidance,
                diagnosis_results.natural_remedies,
                diagnosis_results.expert_confirmation,
                diagnosis_results.description_alignment,
                diagnosis_results.top_predictions,
                diagnosis_results.precautions,
                diagnosis_results.do_not,
                diagnosis_results.next_check,
                diagnosis_results.follow_up,
                diagnosis_results.model_label,
                diagnosis_results.model_note
            FROM scans
            JOIN diagnosis_results ON diagnosis_results.scan_id = scans.id
            WHERE scans.id = ?
            """,
            (scan_id,),
        ).fetchone()
        return row_to_scan(row)
    finally:
        if close_connection:
            connection.close()


def list_scans(crop_id=None):
    query = """
        SELECT
            scans.id AS scan_id,
            scans.crop_id,
            scans.scan_date,
            scans.image_path,
            scans.description,
            scans.growth_stage,
            scans.created_at,
            diagnosis_results.crop_name,
            diagnosis_results.diagnosis,
            diagnosis_results.diagnosis_status,
            diagnosis_results.reliability,
            diagnosis_results.model_confidence,
            diagnosis_results.severity,
            diagnosis_results.health_status,
            diagnosis_results.health_score,
            diagnosis_results.evidence,
            diagnosis_results.possible_causes,
            diagnosis_results.recommendations,
            diagnosis_results.visual_indicators,
            diagnosis_results.preventive_measures,
            diagnosis_results.medicine_guidance,
            diagnosis_results.fertilizer_guidance,
            diagnosis_results.natural_remedies,
            diagnosis_results.expert_confirmation,
            diagnosis_results.description_alignment,
            diagnosis_results.top_predictions,
            diagnosis_results.precautions,
            diagnosis_results.do_not,
            diagnosis_results.next_check,
            diagnosis_results.follow_up,
            diagnosis_results.model_label,
            diagnosis_results.model_note
        FROM scans
        JOIN diagnosis_results ON diagnosis_results.scan_id = scans.id
    """
    params = []
    if crop_id:
        query += " WHERE scans.crop_id = ?"
        params.append(crop_id)
    query += " ORDER BY scans.scan_date DESC, scans.id DESC"

    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()
        return [row_to_scan(row) for row in rows]


def get_previous_scan(crop_id, scan_id):
    with get_connection() as connection:
        current = connection.execute(
            "SELECT scan_date, id FROM scans WHERE id = ? AND crop_id = ?",
            (scan_id, crop_id),
        ).fetchone()
        if current is None:
            return None

        row = connection.execute(
            """
            SELECT
                scans.id AS scan_id,
                scans.crop_id,
                scans.scan_date,
                scans.image_path,
                scans.description,
                scans.growth_stage,
                scans.created_at,
                diagnosis_results.crop_name,
                diagnosis_results.diagnosis,
                diagnosis_results.diagnosis_status,
                diagnosis_results.reliability,
                diagnosis_results.model_confidence,
                diagnosis_results.severity,
                diagnosis_results.health_status,
                diagnosis_results.health_score,
                diagnosis_results.evidence,
                diagnosis_results.possible_causes,
                diagnosis_results.recommendations,
                diagnosis_results.visual_indicators,
                diagnosis_results.preventive_measures,
                diagnosis_results.medicine_guidance,
                diagnosis_results.fertilizer_guidance,
                diagnosis_results.natural_remedies,
                diagnosis_results.expert_confirmation,
                diagnosis_results.description_alignment,
                diagnosis_results.top_predictions,
                diagnosis_results.precautions,
                diagnosis_results.do_not,
                diagnosis_results.next_check,
                diagnosis_results.follow_up,
                diagnosis_results.model_label,
                diagnosis_results.model_note
            FROM scans
            JOIN diagnosis_results ON diagnosis_results.scan_id = scans.id
            WHERE scans.crop_id = ?
              AND (
                  scans.scan_date < ?
                  OR (scans.scan_date = ? AND scans.id < ?)
              )
            ORDER BY scans.scan_date DESC, scans.id DESC
            LIMIT 1
            """,
            (crop_id, current["scan_date"], current["scan_date"], current["id"]),
        ).fetchone()
        return row_to_scan(row)


def create_quick_diagnosis(crop_name, image_path, description):
    created_at = utc_now()
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO quick_diagnoses (
                crop_name, image_path, description, diagnosis_status, created_at
            )
            VALUES (?, ?, ?, 'pending_model', ?)
            """,
            (crop_name.strip(), image_path, description or "", created_at),
        )
        return {
            "id": cursor.lastrowid,
            "crop_name": crop_name.strip(),
            "image_path": image_path,
            "image_url": f"/uploads/{Path(image_path).name}",
            "description": description or "",
            "diagnosis_status": "pending_model",
            "created_at": created_at,
        }


def get_setting(setting_key, default=None):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT setting_value FROM app_settings WHERE setting_key = ?", (setting_key,)
        ).fetchone()
    if row is None:
        return default
    try:
        return json.loads(row["setting_value"])
    except (TypeError, json.JSONDecodeError):
        return default


def set_setting(setting_key, value):
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO app_settings (setting_key, setting_value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value, updated_at = excluded.updated_at",
            (setting_key, json.dumps(value, ensure_ascii=False), utc_now()),
        )
