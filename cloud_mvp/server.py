from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict
from datetime import datetime

app = FastAPI()

# ===============================
# Banco em memória
# ===============================

telemetry_db: Dict[str, List[dict]] = {}

# ===============================
# Modelo de Dados
# ===============================

class TelemetryData(BaseModel):
    session_id: str
    driver: str
    user_id: int
    lap: int
    lap_time: float
    fuel: float
    position: int
    timestamp: str
    state: str # <--- OBRIGATÓRIO: Para o semáforo funcionar

# ===============================
# Endpoint para receber dados
# ===============================

@app.post("/telemetry")
def receive_telemetry(data: TelemetryData):

    if data.session_id not in telemetry_db:
        telemetry_db[data.session_id] = []

    telemetry_db[data.session_id].append(data.dict())

    return {"status": "ok"}

# ===============================
# Endpoint para consultar sessão
# ===============================

@app.get("/session/{session_id}")
def get_session(session_id: str):

    if session_id not in telemetry_db:
        return []

    return telemetry_db[session_id]

# ===============================
# Health Check
# ===============================

@app.get("/")
def root():
    return {"message": "Cloud Telemetry Server Running"}
