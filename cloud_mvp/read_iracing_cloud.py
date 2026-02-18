import irsdk
import time
import pandas as pd
import json
import requests  # <--- NOVO: Necessário para nuvem
from collections import deque
from config import LOG_DIR, WINDOW_SIZE

# ==============================
# Configuração Cloud
# ==============================
# Substitua pelo seu IP Público ou endereço do servidor hospedado
SERVER_URL = "https://spondylitic-junior-obedient.ngrok-free.dev/telemetry" 
SESSION_ID = "Daytona_Test" # Deve ser igual ao que você digita no Dashboard

# ==============================
# Configuração Local
# ==============================
STATUS_PATH = LOG_DIR / "status.json"
timestamp = time.strftime("%Y%m%d_%H%M%S")
CSV_PATH = LOG_DIR / f"stint_{timestamp}.csv"

ir = irsdk.IRSDK()

# ==============================
# Funções auxiliares
# ==============================

def send_to_cloud(data):
    """Envia o pacote de telemetria para o servidor FastAPI"""
    try:
        # Adiciona o ID da sessão global ao pacote
        data["session_id"] = SESSION_ID
        # Mapeia os campos para o formato que o Servidor espera (TelemetryData)
        cloud_payload = {
            "session_id": SESSION_ID,
            "driver": data["Piloto"],
            "user_id": data["UserID"],
            "lap": int(data["Volta"]),
            "lap_time": data["Tempo"],
            "fuel": data["Combustivel_Restante"],
            "position": data["Pos_Geral"],
            "timestamp": data["Timestamp"],
            "state": data["state"] # Enviando o estado dinâmico
        }
        response = requests.post(SERVER_URL, json=cloud_payload, timeout=1)
        return response.status_code == 200
    except Exception as e:
        # Não trava o script se a internet oscilar
        return False

def update_status(state, driver="---", track="---"):
    status_data = {
        "state": state,
        "driver": driver,
        "track": track,
        "last_update": time.time()
    }
    # Salva localmente para o dash local
    with open(STATUS_PATH, "w") as f:
        json.dump(status_data, f)
    
    # Envia um "Heartbeat" para a nuvem mesmo sem completar volta
    if state != "offline":
        heartbeat = {
            "Piloto": driver, "UserID": -1, "Volta": 0, "Tempo": 0.0,
            "Combustivel_Restante": 0.0, "Pos_Geral": 0, 
            "Timestamp": time.strftime("%H:%M:%S"), "state": state
        }
        send_to_cloud(heartbeat)

def get_session_type(session_num):
    try:
        return ir['SessionInfo']['Sessions'][session_num]['SessionType']
    except:
        return "Sessão"

# ==============================
# Posição robusta
# ==============================
last_valid_pos_g = 0
last_valid_pos_c = 0

def get_valid_position():
    global last_valid_pos_g, last_valid_pos_c
    try:
        idx = ir['DriverInfo']['DriverCarIdx']
        pos_g = ir['CarIdxPosition'][idx]
        pos_c = ir['CarIdxClassPosition'][idx]
        if pos_g > 0:
            last_valid_pos_g = int(pos_g)
            last_valid_pos_c = int(pos_c)
        return last_valid_pos_g, last_valid_pos_c
    except:
        return last_valid_pos_g, last_valid_pos_c

# ==============================
# Controle Principal
# ==============================
last_session_num = -1
last_recorded_lap_time = -1.0
fuel_at_lap_start = -1.0
file_initialized = False
grid_recorded = False

laps_window = deque(maxlen=WINDOW_SIZE)
fuel_window = deque(maxlen=WINDOW_SIZE)

print(f"📡 Telemetria Cloud Ativa - Enviando para: {SERVER_URL}")

try:
    while True:
        if not ir.is_connected:
            ir.startup()
            update_status("offline")
            file_initialized = False
            time.sleep(1)
            continue

        car_idx = ir['DriverInfo']['DriverCarIdx']
        if car_idx < 0:
            update_status("connected") # No menu
            time.sleep(0.5)
            continue

        # ===== DADOS DO PILOTO E SESSÃO =====
        try:
            driver_data = ir['DriverInfo']['Drivers'][car_idx]
            current_driver = driver_data.get('UserName', 'Unknown')
            current_user_id = driver_data.get('UserID', -1)
            team_name = driver_data.get('TeamName', 'N/A')
        except:
            current_driver, current_user_id, team_name = "Unknown", -1, "N/A"

        session_num = ir['SessionNum']
        session_name = get_session_type(session_num)
        track_name = ir['WeekendInfo']['TrackDisplayName']
        
        # Define se está no cockpit (state dinâmico)
        current_state = "cockpit" if ir['SessionState'] > 3 else "connected"
        update_status(current_state, current_driver, track_name)

        if session_num != last_session_num:
            laps_window.clear()
            fuel_window.clear()
            grid_recorded = False
            last_recorded_lap_time = -1.0
            last_session_num = session_num
            print(f"🔄 Nova Sessão Detectada: {session_name}")

        fuel_now = ir['FuelLevel']
        pos_g, pos_c = get_valid_position()

        # ===== Inicializa CSV Local =====
        if not file_initialized:
            pd.DataFrame(columns=[
                "Timestamp", "Sessao", "Pista", "Equipe",
                "Piloto", "UserID", "Volta", "Tempo",
                "Media_3_Voltas", "Consumo_Volta",
                "Media_Consumo_3_Voltas", "Combustivel_Restante",
                "Pos_Geral", "Pos_Classe", "Voltas_Restantes_Estimadas"
            ]).to_csv(CSV_PATH, index=False)
            file_initialized = True

        # ===== DETECÇÃO DE VOLTA =====
        lap_last_time = ir['LapLastLapTime']

        if lap_last_time > 0 and lap_last_time != last_recorded_lap_time:
            time.sleep(0.8) # Sincronização de posição

            current_car_lap = ir['CarIdxLap'][car_idx] - 1
            
            # Recalcula médias
            laps_window.append(lap_last_time)
            avg_lap_time = sum(laps_window) / len(laps_window)

            # Consumo com proteção contra swap
            consumo = 0.0
            if fuel_now > 0.1 and fuel_at_lap_start > fuel_now:
                consumo = max(0.0, fuel_at_lap_start - fuel_now)
                if consumo < 20: fuel_window.append(consumo)
            
            avg_fuel = sum(fuel_window) / len(fuel_window) if fuel_window else consumo

            # Monta Pacote de Dados
            data = {
                "Timestamp": time.strftime("%H:%M:%S"),
                "Sessao": session_name, "Pista": track_name,
                "Equipe": team_name, "Piloto": current_driver,
                "UserID": current_user_id, "Volta": current_car_lap,
                "Tempo": round(lap_last_time, 3), "Media_3_Voltas": round(avg_lap_time, 3),
                "Consumo_Volta": round(consumo, 3), "Media_Consumo_3_Voltas": round(avg_fuel, 3),
                "Combustivel_Restante": round(fuel_now, 3),
                "Pos_Geral": pos_g, "Pos_Classe": pos_c, "state": current_state
            }

            # 1. Salva Local (Segurança)
            pd.DataFrame([data]).to_csv(CSV_PATH, mode='a', index=False, header=False)
            
            # 2. Envia para Nuvem (Estratégia)
            success = send_to_cloud(data)
            status_cloud = "✅ Cloud OK" if success else "❌ Cloud Fail"

            print(f"🏁 Volta {current_car_lap} | {current_driver} | {lap_last_time:.3f}s | {status_cloud}")

            last_recorded_lap_time = lap_last_time
            fuel_at_lap_start = fuel_now

        time.sleep(0.5)

except KeyboardInterrupt:
    update_status("offline")
finally:
    ir.shutdown()