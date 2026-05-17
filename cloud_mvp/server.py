from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
import os

app = FastAPI()
DB_PATH = 'telemetry.db'

# ─── Cria o banco de dados se não existir ───────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.on_event('startup')
def init_db():
    db = get_db()
    db.execute('''
        CREATE TABLE IF NOT EXISTS telemetry (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id    TEXT,
            driver        TEXT,
            user_id       INTEGER,
            lap           INTEGER,
            lap_time      REAL,
            fuel          REAL,
            position      INTEGER,
            class_position INTEGER DEFAULT 0,
            timestamp     TEXT,
            state         TEXT
        )
    ''')
    db.commit()

# ─── Modelo de dados ────────────────────────────────────
class TelemetryData(BaseModel):
    session_id:     str
    driver:         str
    user_id:        int
    lap:            int
    lap_time:       float
    fuel:           float
    position:       int
    class_position: int = 0   # campo novo; default 0 mantém compatibilidade com clientes antigos
    timestamp:      str
    state:          str

# ─── Recebe telemetria dos pilotos ──────────────────────
@app.post('/telemetry')
def receive_telemetry(data: TelemetryData):
    db = get_db()
    db.execute(
        'INSERT INTO telemetry VALUES (NULL,?,?,?,?,?,?,?,?,?,?)',
        (data.session_id, data.driver, data.user_id, data.lap,
         data.lap_time, data.fuel, data.position, data.class_position,
         data.timestamp, data.state)
    )
    db.commit()
    return {'status': 'ok'}

# ─── Retorna dados da sessão (com paginação) ────────────
@app.get('/session/{session_id}')
def get_session(session_id: str, since_id: int = 0):
    db = get_db()
    rows = db.execute(
        'SELECT * FROM telemetry WHERE session_id=? AND id>? ORDER BY id',
        (session_id, since_id)
    ).fetchall()
    return [dict(r) for r in rows]

# ─── Reseta (apaga) todos os dados de uma sessão ────────
@app.delete('/session/{session_id}')
def reset_session(session_id: str):
    db = get_db()
    result = db.execute(
        'SELECT COUNT(*) as total FROM telemetry WHERE session_id=?',
        (session_id,)
    ).fetchone()
    if result['total'] == 0:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    db.execute('DELETE FROM telemetry WHERE session_id=?', (session_id,))
    db.commit()
    return {'status': 'ok', 'session_id': session_id, 'rows_deleted': result['total']}

# ─── Lista todas as sessões disponíveis ─────────────────
@app.get('/sessions')
def list_sessions():
    db = get_db()
    rows = db.execute(
        'SELECT DISTINCT session_id FROM telemetry ORDER BY session_id'
    ).fetchall()
    return [r['session_id'] for r in rows]

# ─── Health check ────────────────────────────────────────
@app.get('/')
def root():
    return {'status': 'iRacing Telemetry Server Online'}