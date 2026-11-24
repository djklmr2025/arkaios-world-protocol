"""Public, explicit visitor feedback for ARKAIOS World.

This store is intentionally separate from agent chat and private mail.  It
contains only the name a visitor chose to display, a category, and the text
they submitted in the clearly labelled public feedback panel.
"""
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path


DB_PATH = Path(__file__).parent / 'db' / 'visitor_feedback.db'
MAX_NAME = 40
MAX_MESSAGE = 600
CATEGORIES = {'idea', 'duda', 'inquietud', 'reporte'}


def init_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                category TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')


def _clean_text(value, limit):
    text = str(value or '').strip()
    if not text or len(text) > limit or any(ord(char) < 32 for char in text):
        raise ValueError('invalid_text')
    return text


def create_feedback(display_name, category, message):
    name = str(display_name or 'Visitante').strip() or 'Visitante'
    if len(name) > MAX_NAME or any(ord(char) < 32 for char in name):
        raise ValueError('invalid_name')
    category = str(category or '').strip().lower()
    if category not in CATEGORIES:
        raise ValueError('invalid_category')
    message = _clean_text(message, MAX_MESSAGE)
    record = {
        'id': f'feedback:{uuid.uuid4().hex}',
        'display_name': name,
        'category': category,
        'message': message,
        'created_at': datetime.now(timezone.utc).isoformat(),
    }
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            INSERT INTO feedback (id, display_name, category, message, created_at)
            VALUES (:id, :display_name, :category, :message, :created_at)
        ''', record)
    return record


def get_public_feedback(limit=30):
    limit = max(1, min(int(limit), 50))
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute('''
            SELECT id, display_name, category, message, created_at
            FROM feedback ORDER BY created_at DESC LIMIT ?
        ''', (limit,)).fetchall()
    return [dict(zip(('id', 'display_name', 'category', 'message', 'created_at'), row)) for row in reversed(rows)]


def feedback_summary():
    with sqlite3.connect(DB_PATH) as conn:
        total = conn.execute('SELECT COUNT(*) FROM feedback').fetchone()[0]
        by_category = dict(conn.execute('SELECT category, COUNT(*) FROM feedback GROUP BY category').fetchall())
    return {'total': total, 'by_category': {category: by_category.get(category, 0) for category in sorted(CATEGORIES)}}
