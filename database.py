import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
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
            """
        )
        ensure_column(connection, "diagnosis_results", "visual_indicators", "TEXT NOT NULL DEFAULT '[]'")
        ensure_column(connection, "diagnosis_results", "preventive_measures", "TEXT NOT NULL DEFAULT '[]'")
        ensure_column(connection, "diagnosis_results", "medicine_guidance", "TEXT NOT NULL DEFAULT '[]'")
        ensure_column(connection, "diagnosis_results", "fertilizer_guidance", "TEXT NOT NULL DEFAULT '[]'")
        ensure_column(connection, "diagnosis_results", "natural_remedies", "TEXT NOT NULL DEFAULT '[]'")
        ensure_column(connection, "diagnosis_results", "expert_confirmation", "TEXT NOT NULL DEFAULT ''")
        ensure_column(connection, "diagnosis_results", "description_alignment", "TEXT NOT NULL DEFAULT ''")
        ensure_column(connection, "diagnosis_results", "top_predictions", "TEXT NOT NULL DEFAULT '[]'")


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
                crop_name, field_name, planting_date, location, notes, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, 'active', ?)
            """,
            (
                crop["crop_name"].strip(),
                crop["field_name"].strip(),
                crop["planting_date"],
                crop.get("location", "").strip(),
                crop.get("notes", "").strip(),
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
        row = connection.execute("SELECT * FROM crops WHERE id = ?", (crop_id,)).fetchone()
        return row_to_crop(row)
    finally:
        if close_connection:
            connection.close()


def list_crops():
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM crops ORDER BY created_at DESC, id DESC"
        ).fetchall()
        return [row_to_crop(row) for row in rows]


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
