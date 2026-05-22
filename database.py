import os
import json
from datetime import datetime
from urllib.parse import urlparse

# ── Detecta o backend (PostgreSQL se DATABASE_URL estiver definida) ────────
DATABASE_URL = os.environ.get('DATABASE_URL', '')

# Remove parâmetros não suportados pelo pg8000
if DATABASE_URL:
    DATABASE_URL = (DATABASE_URL
                    .replace('&channel_binding=require', '')
                    .replace('?channel_binding=require&', '?')
                    .replace('?channel_binding=require', ''))

USE_PG = bool(DATABASE_URL)

if not USE_PG:
    import sqlite3
    DATABASE = 'cbmerj_ac.db'


# ── Conexão PostgreSQL via pg8000 ──────────────────────────────────────────
def _pg_connect():
    import pg8000.dbapi
    p = urlparse(DATABASE_URL)
    db_name = p.path.lstrip('/').split('?')[0]
    use_ssl = 'sslmode=require' in DATABASE_URL
    return pg8000.dbapi.connect(
        host=p.hostname,
        port=p.port or 5432,
        database=db_name,
        user=p.username,
        password=p.password,
        ssl_context=use_ssl,
    )


def _to_dict(cursor, row):
    """Converte uma linha do pg8000 (tupla) em dict usando cursor.description."""
    if row is None:
        return None
    cols = [d[0] for d in cursor.description]
    return dict(zip(cols, row))


def _to_dicts(cursor, rows):
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in rows]


# ── Conexão SQLite (fallback local) ───────────────────────────────────────
def get_db():
    if USE_PG:
        return _pg_connect()
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# ── Inicialização do banco ─────────────────────────────────────────────────
def init_db():
    if USE_PG:
        conn = _pg_connect()
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
        conn.close()
    else:
        conn = sqlite3.connect(DATABASE)
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
    if USE_PG:
        conn = _pg_connect()
        cur = conn.cursor()
        cur.execute('SELECT id FROM submissions WHERE obm_code = %s', (obm_code,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result is not None
    else:
        conn = sqlite3.connect(DATABASE)
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
    if USE_PG:
        conn = _pg_connect()
        cur = conn.cursor()
        cur.execute(
            '''INSERT INTO submissions
               (obm_code, obm_name, commander_name, contact_email, contact_phone,
                rooms_json, observations, submitted_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
               RETURNING id''',
            params
        )
        sub_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
    else:
        conn = sqlite3.connect(DATABASE)
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
    if USE_PG:
        conn = _pg_connect()
        cur = conn.cursor()
        cur.execute('SELECT * FROM submissions ORDER BY submitted_at DESC')
        rows = _to_dicts(cur, cur.fetchall())
        cur.close()
        conn.close()
        return rows
    else:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        rows = [dict(r) for r in conn.execute(
            'SELECT * FROM submissions ORDER BY submitted_at DESC'
        ).fetchall()]
        conn.close()
        return rows


# ── Buscar envio por ID ────────────────────────────────────────────────────
def get_submission(sub_id):
    if USE_PG:
        conn = _pg_connect()
        cur = conn.cursor()
        cur.execute('SELECT * FROM submissions WHERE id = %s', (sub_id,))
        row = _to_dict(cur, cur.fetchone())
        cur.close()
        conn.close()
        return row
    else:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            'SELECT * FROM submissions WHERE id = ?', (sub_id,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None


# ── Remover envio ──────────────────────────────────────────────────────────
def delete_submission(obm_code):
    if USE_PG:
        conn = _pg_connect()
        cur = conn.cursor()
        cur.execute('DELETE FROM submissions WHERE obm_code = %s', (obm_code,))
        conn.commit()
        cur.close()
        conn.close()
    else:
        conn = sqlite3.connect(DATABASE)
        conn.execute('DELETE FROM submissions WHERE obm_code = ?', (obm_code,))
        conn.commit()
        conn.close()
