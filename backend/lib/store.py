"""SQLite storage layer for SENTINEL (analysis history + app settings).

SENTINEL v1 stores no source code — only structured analysis reports. The storage
layer is intentionally tiny and swappable: every function here is the seam a
PostgreSQL adapter would implement (see README "Architecture").
"""

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

_ROOT = Path(__file__).resolve().parent.parent  # backend/
_raw_path = os.environ.get("SENTINEL_DB_PATH", "data/sentinel.db")
DB_PATH = Path(_raw_path) if Path(_raw_path).is_absolute() else _ROOT / _raw_path

DEFAULT_SETTINGS: dict = {
    "max_file_size_bytes": 1_000_000,
    "disabled_rules": [],
}

# Hard clamp so a bad settings write can never balloon the upload budget.
MIN_FILE_SIZE = 10_000
MAX_FILE_SIZE = 10_000_000

_SCHEMA = """
CREATE TABLE IF NOT EXISTS analyses (
    id TEXT PRIMARY KEY,
    sid TEXT NOT NULL,
    created_at TEXT NOT NULL,
    file_name TEXT NOT NULL,
    language TEXT NOT NULL,
    overall_score INTEGER,
    security_score INTEGER,
    total_issues INTEGER NOT NULL DEFAULT 0,
    critical_issues INTEGER NOT NULL DEFAULT 0,
    high_issues INTEGER NOT NULL DEFAULT 0,
    medium_issues INTEGER NOT NULL DEFAULT 0,
    low_issues INTEGER NOT NULL DEFAULT 0,
    info_issues INTEGER NOT NULL DEFAULT 0,
    report TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_analyses_sid_created ON analyses(sid, created_at DESC);
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

_SUMMARY_COLUMNS = (
    "id, created_at, file_name, language, overall_score, security_score, "
    "total_issues, critical_issues, high_issues, medium_issues, low_issues, info_issues"
)


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH, timeout=15.0)
    con.row_factory = sqlite3.Row
    return con


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = _connect()
    try:
        con.executescript(_SCHEMA)
        con.execute("PRAGMA journal_mode=WAL")
        con.commit()
    finally:
        con.close()


def clamp_file_size(size: int) -> int:
    return max(MIN_FILE_SIZE, min(MAX_FILE_SIZE, int(size)))


# --- settings ---------------------------------------------------------------


def get_settings() -> dict:
    con = _connect()
    try:
        row = con.execute("SELECT value FROM app_settings WHERE key = 'global'").fetchone()
    finally:
        con.close()
    merged = dict(DEFAULT_SETTINGS)
    if row is not None:
        try:
            data = json.loads(row["value"])
        except json.JSONDecodeError:
            data = {}
        for key in DEFAULT_SETTINGS:
            if key in data:
                merged[key] = data[key]
    return merged


def update_settings(patch: dict) -> dict:
    current = get_settings()
    current.update(patch)
    con = _connect()
    try:
        con.execute(
            "INSERT INTO app_settings(key, value) VALUES('global', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (json.dumps(current),),
        )
        con.commit()
    finally:
        con.close()
    return current


# --- analysis history -------------------------------------------------------


def save_analysis(sid: str, report: dict) -> dict:
    analysis_id = report["id"]
    counts = report["counts"]
    created_at = datetime.now(timezone.utc).isoformat()
    con = _connect()
    try:
        con.execute(
            "INSERT INTO analyses (id, sid, created_at, file_name, language, overall_score,"
            " security_score, total_issues, critical_issues, high_issues, medium_issues,"
            " low_issues, info_issues, report) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                analysis_id,
                sid,
                created_at,
                report["file_name"],
                report["language"],
                report["overall_score"],
                report["scores"]["security"] if report["scores"] else None,
                counts["total"],
                counts["critical"],
                counts["high"],
                counts["medium"],
                counts["low"],
                counts["info"],
                json.dumps(report),
            ),
        )
        con.commit()
    finally:
        con.close()
    return {
        "id": analysis_id,
        "created_at": created_at,
        "file_name": report["file_name"],
        "language": report["language"],
        "overall_score": report["overall_score"],
        "security_score": report["scores"]["security"] if report["scores"] else None,
        "total_issues": counts["total"],
        "critical_issues": counts["critical"],
        "high_issues": counts["high"],
        "medium_issues": counts["medium"],
        "low_issues": counts["low"],
        "info_issues": counts["info"],
    }


def list_analyses(sid: str) -> list[dict]:
    con = _connect()
    try:
        rows = con.execute(
            f"SELECT {_SUMMARY_COLUMNS} FROM analyses WHERE sid = ? ORDER BY created_at DESC LIMIT 200",
            (sid,),
        ).fetchall()
    finally:
        con.close()
    return [dict(row) for row in rows]


def get_analysis(sid: str, analysis_id: str) -> dict | None:
    con = _connect()
    try:
        row = con.execute(
            f"SELECT {_SUMMARY_COLUMNS}, report FROM analyses WHERE sid = ? AND id = ?",
            (sid, analysis_id),
        ).fetchone()
    finally:
        con.close()
    if row is None:
        return None
    full = dict(row)
    full["report"] = json.loads(full["report"])
    return full


def delete_analysis(sid: str, analysis_id: str) -> bool:
    con = _connect()
    try:
        cur = con.execute("DELETE FROM analyses WHERE sid = ? AND id = ?", (sid, analysis_id))
        con.commit()
    finally:
        con.close()
    return cur.rowcount > 0


def clear_analyses(sid: str) -> int:
    con = _connect()
    try:
        cur = con.execute("DELETE FROM analyses WHERE sid = ?", (sid,))
        con.commit()
    finally:
        con.close()
    return cur.rowcount
