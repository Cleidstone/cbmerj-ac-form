import os
import json
from datetime import datetime

# ── Detecta o backend (PostgreSQL se DATABASE_URL estiver definida) ────────
DATABASE_URL = os.environ.get('DATABASE_URL', '')

# Remove parâmetro channel_binding que o psycopg2 não suporta
if DATABASE_URL:
    DATABASE_URL = (DATABASE_URL
                    .replace('&channel_binding=require', '')
                    .replace('?channel_binding=require&', '?')
                    .replace('?channel_binding=require', ''))

USE_PG = bool(DATABASE_URL)

if USE_PG:
    import psycopg2
    import psycopg2.extras
else:
    import sqlite3
    DATABASE = 'cbmerj_ac.db'


# ── Conexão ────────────────────────────────────────────────────────────────
def get_db():
    if USE_PG:
        return psycopg2.connect(DATABASE_URL,
                                cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        return conn


# ── Inicialização do banco ─────────────────────────────────────────────────
def init_db():
    conn = get_db()
    if USE_PG:
        cur = conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS submissions (
            id             SERIAL PRIMARY KEY,
            obm_code       TEXT UNIQUE NOT NULL,
            obm_name       TEXT NOT NULL,
            commander_name TEXT,
            contact_email  TEXT,
            contact_phone  TEXT,
            rooms_json     TEXT NOT NULL,
            observations   TEXT,
            submitted_at   TEXT NOT NULL
        )''')
        conn.commit()
        cur.close()
    else:
        conn.execute('''CREATE TABLE IF NOT EXISTS submissions (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            obm_code       TEXT UNIQUE NOT NULL,
            obm_name       TEXT NOT NULL,
            commander_name TEXT,
            contact_email  TEXT,
            contact_phone  TEXT,
            rooms_json     TEXT NOT NULL,
            observations   TEXT,
            submitted_at   TEXT NOT NULL
        )''')
        conn.commit()
    conn.close()


# ── Verificar envio anterior ───────────────────────────────────────────────
def has_submitted(obm_code):
    conn = get_db()
    if USE_PG:
        cur = conn.cursor()
        cur.execute('SELECT id FROM submissions WHERE obm_code = %s', (obm_code,))
        result = cur.fetchone()
        cur.close()
    else:
        result = conn.execute(
            'SELECT id FROM submissions WHERE obm_code = ?', (obm_code,)
        ).fetchone()
    conn.close()
    return result is not None


# ── Salvar envio ───────────────────────────────────────────────────────────
def save_submission(data):
    now = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    rooms_json = json.dumps(data['rooms'], ensure_ascii=False)
    params = (
        data['obm_code'], data['obm_name'], data['commander_name'],
        data['contact_email'], data['contact_phone'],
        rooms_json, data['observations'], now
    )
    conn = get_db()
    if USE_PG:
        cur = conn.cursor()
        cur.execute(
            '''INSERT INTO submissions
               (obm_code, obm_name, commander_name, contact_email, contact_phone,
                rooms_json, observations, submitted_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
               RETURNING id''',
            params
        )
        sub_id = cur.fetchone()['id']
        conn.commit()
        cur.close()
    else:
        cur = conn.execute(
            '''INSERT INTO submissions
               (obm_code, obm_name, commander_name, contact_email, contact_phone,
                rooms_json, observations, submitted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            params
        )
        sub_id = cur.lastrowid
        conn.commit()
    conn.close()
    return sub_id


# ── Listar todos os envios ─────────────────────────────────────────────────
def get_all_submissions():
    conn = get_db()
    if USE_PG:
        cur = conn.cursor()
        cur.execute('SELECT * FROM submissions ORDER BY submitted_at DESC')
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()
    else:
        rows = [dict(r) for r in conn.execute(
            'SELECT * FROM submissions ORDER BY submitted_at DESC'
        ).fetchall()]
    conn.close()
    return rows


# ── Buscar envio por ID ────────────────────────────────────────────────────
def get_submission(sub_id):
    conn = get_db()
    if USE_PG:
        cur = conn.cursor()
        cur.execute('SELECT * FROM submissions WHERE id = %s', (sub_id,))
        row = cur.fetchone()
        cur.close()
    else:
        row = conn.execute(
            'SELECT * FROM submissions WHERE id = ?', (sub_id,)
        ).fetchone()
    conn.close()
    return dict(row) if row else None


# ── Remover envio ──────────────────────────────────────────────────────────
def delete_submission(obm_code):
    conn = get_db()
    if USE_PG:
        cur = conn.cursor()
        cur.execute('DELETE FROM submissions WHERE obm_code = %s', (obm_code,))
        conn.commit()
        cur.close()
    else:
        conn.execute('DELETE FROM submissions WHERE obm_code = ?', (obm_code,))
        conn.commit()
    conn.close()
