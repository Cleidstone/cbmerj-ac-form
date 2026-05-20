import sqlite3
import json
from datetime import datetime

DATABASE = 'cbmerj_ac.db'


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        obm_code TEXT UNIQUE NOT NULL,
        obm_name TEXT NOT NULL,
        commander_name TEXT,
        contact_email TEXT,
        contact_phone TEXT,
        rooms_json TEXT NOT NULL,
        observations TEXT,
        submitted_at TEXT NOT NULL
    )''')
    conn.commit()
    conn.close()


def has_submitted(obm_code):
    conn = get_db()
    result = conn.execute(
        'SELECT id FROM submissions WHERE obm_code = ?', (obm_code,)
    ).fetchone()
    conn.close()
    return result is not None


def save_submission(data):
    conn = get_db()
    conn.execute(
        '''INSERT INTO submissions
           (obm_code, obm_name, commander_name, contact_email, contact_phone,
            rooms_json, observations, submitted_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (data['obm_code'], data['obm_name'], data['commander_name'],
         data['contact_email'], data['contact_phone'],
         json.dumps(data['rooms'], ensure_ascii=False),
         data['observations'], datetime.now().strftime('%d/%m/%Y %H:%M:%S'))
    )
    sub_id = conn.lastrowid
    conn.commit()
    conn.close()
    return sub_id


def get_all_submissions():
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM submissions ORDER BY submitted_at DESC'
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_submission(sub_id):
    conn = get_db()
    row = conn.execute(
        'SELECT * FROM submissions WHERE id = ?', (sub_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_submission(obm_code):
    conn = get_db()
    conn.execute('DELETE FROM submissions WHERE obm_code = ?', (obm_code,))
    conn.commit()
    conn.close()
