"""
db.py — SQLite + ChromaDB
ChromaDB stores vectors and metadata, for similarity search.
SQLite stores the full Note record. 
query_engine returns IDs → db.get_notes_by_ids() fetches the full rows → into the LLM context and Discord embeds.
The two stores stay in sync because both writes happen together in ingestion.py right after the Note is created.
"""
import sqlite3
from typing import Optional
from config import DB_PATH
from models import Note


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS notes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     TEXT NOT NULL,
                content_text TEXT NOT NULL,
                image_path  TEXT,
                source_type TEXT NOT NULL,
                timestamp   TEXT NOT NULL,
                ocr_failed  INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS reminders (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     TEXT NOT NULL,
                note_id     INTEGER REFERENCES notes(id),
                remind_at   TEXT NOT NULL,
                message     TEXT,
                sent        INTEGER DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_notes_user ON notes(user_id);
            CREATE INDEX IF NOT EXISTS idx_reminders_due ON reminders(remind_at, sent);
        """)


def insert_note(note: Note) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO notes (user_id, content_text, image_path, source_type, timestamp, ocr_failed)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (note.user_id, note.content_text, note.image_path,
             note.source_type, note.timestamp, int(note.ocr_failed))
        )
        return cur.lastrowid


def get_notes_by_ids(note_ids: list[int]) -> list[dict]:
    if not note_ids:
        return []

    placeholders = ",".join("?" * len(note_ids))
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT * FROM notes WHERE id IN ({placeholders})", note_ids
        ).fetchall()

    row_map = {r["id"]: dict(r) for r in rows}
    return [row_map[nid] for nid in note_ids if nid in row_map]

def insert_reminder(user_id: str, note_id: int, remind_at: str, message: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO reminders (user_id, note_id, remind_at, message) VALUES (?,?,?,?)",
            (user_id, note_id, remind_at, message)
        )


def get_due_reminders() -> list[dict]:
    from datetime import datetime
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM reminders WHERE remind_at <= ? AND sent = 0", (now,)
        ).fetchall()
    return [dict(r) for r in rows]


def mark_reminder_sent(reminder_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE reminders SET sent=1 WHERE id=?", (reminder_id,))
