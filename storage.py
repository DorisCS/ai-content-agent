"""Small SQLite store for one content workflow per record."""

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(os.getenv("CONTENT_DEMO_DB", Path(__file__).with_name("content_demo.db")))


def _connect():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute(
        """CREATE TABLE IF NOT EXISTS workflows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand TEXT NOT NULL,
            audience TEXT NOT NULL,
            goal TEXT NOT NULL,
            status TEXT NOT NULL,
            topics TEXT NOT NULL DEFAULT '[]',
            selected_topic INTEGER,
            draft TEXT NOT NULL DEFAULT '{}',
            review_note TEXT NOT NULL DEFAULT '',
            metrics TEXT NOT NULL DEFAULT '{}',
            report TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )"""
    )
    connection.commit()
    return connection


def create_workflow(brand, audience, goal):
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as db:
        cursor = db.execute(
            "INSERT INTO workflows (brand,audience,goal,status,created_at,updated_at) VALUES (?,?,?,?,?,?)",
            (brand.strip(), audience.strip(), goal.strip(), "created", now, now),
        )
        return cursor.lastrowid


def get_workflow(workflow_id):
    with _connect() as db:
        row = db.execute("SELECT * FROM workflows WHERE id=?", (workflow_id,)).fetchone()
    if not row:
        return None
    result = dict(row)
    for key in ("topics", "draft", "metrics", "report"):
        result[key] = json.loads(result[key])
    return result


def list_workflows():
    with _connect() as db:
        return [dict(row) for row in db.execute(
            "SELECT id,brand,status,created_at FROM workflows ORDER BY id DESC LIMIT 20"
        ).fetchall()]


def update_workflow(workflow_id, **changes):
    allowed = {"status", "topics", "selected_topic", "draft", "review_note", "metrics", "report"}
    if not changes or set(changes) - allowed:
        raise ValueError("Invalid workflow update")
    values = []
    for key, value in changes.items():
        values.append(json.dumps(value, ensure_ascii=False) if key in {"topics", "draft", "metrics", "report"} else value)
    now = datetime.now(timezone.utc).isoformat()
    fields = ", ".join(f"{key}=?" for key in changes) + ", updated_at=?"
    with _connect() as db:
        db.execute(f"UPDATE workflows SET {fields} WHERE id=?", (*values, now, workflow_id))
