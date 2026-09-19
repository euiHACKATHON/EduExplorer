"""Connection helper and schema bootstrap.

Still SQLite for the classroom prototype. When this moves to PostgreSQL,
`connect()` becomes a session dependency and only this file changes.
"""
import sqlite3
from contextlib import closing

from .config import DB


def connect(timeout: float = 10):
    """Use as: `with connect() as db:` -- closes on exit."""
    return closing(sqlite3.connect(DB, timeout=timeout))


def init_db() -> None:
    with connect() as db:
        db.execute(
            'CREATE TABLE IF NOT EXISTS students ('
            'student_id TEXT PRIMARY KEY, display_name TEXT, grade_level TEXT, '
            'password_hash TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)'
        )
        # Backfill for DBs created before auth was added, so nobody has to
        # manually delete their local sqlite file after pulling this change.
        cols = [row[1] for row in db.execute('PRAGMA table_info(students)').fetchall()]
        if 'password_hash' not in cols:
            db.execute('ALTER TABLE students ADD COLUMN password_hash TEXT')
        # Mastery is keyed per (student, mission, context) rather than one score
        # per mission -- this is what surfaces "solves numerically, fails on
        # transfer", the core fake-mastery signal from the design doc.
        db.execute(
            'CREATE TABLE IF NOT EXISTS mastery ('
            'student TEXT, mission TEXT, context TEXT, xp INTEGER, score REAL, '
            'attempts INTEGER DEFAULT 0, difficulty INTEGER DEFAULT 1, '
            'PRIMARY KEY(student,mission,context))'
        )

        mastery_cols = [
            row[1] for row in db.execute('PRAGMA table_info(mastery)').fetchall()
        ]
        if 'difficulty' not in mastery_cols:
            db.execute(
                'ALTER TABLE mastery ADD COLUMN difficulty INTEGER DEFAULT 1'
            )
        db.execute(
            'CREATE TABLE IF NOT EXISTS attempts ('
            'id INTEGER PRIMARY KEY AUTOINCREMENT, student TEXT, mission TEXT, '
            'context TEXT, question_id TEXT, correct INTEGER, hints_used INTEGER, '
            'time_taken REAL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)'
        )
        db.execute(
            'CREATE TABLE IF NOT EXISTS predictions ('
            'id INTEGER PRIMARY KEY AUTOINCREMENT, student TEXT, mission TEXT, '
            'question_id TEXT, predicted TEXT, actual TEXT, matched INTEGER, '
            'created_at TEXT DEFAULT CURRENT_TIMESTAMP)'
        )
        db.execute('CREATE INDEX IF NOT EXISTS idx_attempts_student ON attempts(student, created_at)')
        db.execute('CREATE INDEX IF NOT EXISTS idx_mastery_student ON mastery(student)')
        db.commit()
