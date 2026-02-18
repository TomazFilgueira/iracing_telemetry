import irsdk
import time
import pandas as pd
import json
import requests
from collections import deque
from config import LOG_DIR, WINDOW_SIZE

# ==============================
# Configuração Cloud
# ==============================
SERVER_URL = "https://spondylitic-junior-obedient.ngrok-free.dev/telemetry" 
SESSION_ID = "Daytona_Test"

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
        data["session_id"] = SESSION_ID
        cloud_payload = {
            "session_id": SESSION_ID,
            "driver": data["Piloto"],
            "user_id": data["UserID"],
            "lap": int(data["Volta"]),
            "lap_time": data["Tempo"],
            "fuel": data["Combustivel_Restante"],
            "position": data["Pos_Geral"],
            "timestamp": data["Timestamp"],
            "state": data["state"]
        }
        # Timeout curto para não travar a telemetria
        requests.post(SERVER_URL, json=cloud_payload, timeout=0.5)
        return True
    except:
        return False

# Variável global para controlar a frequência do Heartbeat
last_heartbeat_time = 0

def update_status_and_heartbeat(state, driver, track, fuel_current, pos_g):
    """
    Atualiza status local e envia Heartbeat para manter o sinal verde na nuvem.
    CORREÇÃO: Envia o combustível REAL, não zero.
    """
    global last_heartbeat_time
    
    # 1. Atualização Local (Status.json)
    status_data = {
        "state": state,
        "driver": driver,
        "track": track,
        "last_update": time.time()
    }
    with open(STATUS_PATH, "w") as f:
        json.dump(status_data, f)
    
    # 2. Heartbeat Cloud (Apenas a cada 2 segundos para não sujar o log)
    if state != "offline" and (time.time() - last_heartbeat_time) > 2.0:
        heartbeat = {
            "Piloto": driver, 
            "UserID": -1, 
            "Volta": 0, 
            "Tempo": 0.0, # Mantemos 0.0 para o Dashboard filtrar fora dos gráficos
            "Combustivel_Restante": float(fuel_current), # <--- CORREÇÃO: Envia valor real
            "Pos_Geral": pos_g, 
            "Timestamp": time.strftime("%H:%M:%S"), 
            "state": state
        }
        send_to_cloud(heartbeat)
        last_heartbeat_time = time.time()

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
grid_recorded = False # <--- Recuperado da versão Local

laps_window = deque(maxlen=WINDOW_SIZE)
fuel_window = deque(maxlen=WINDOW_SIZE)

print(f"📡 Telemetria Cloud Ativa - Enviando para: {SERVER_URL}")

try:
    while True:
        if not ir.is_connected:
            ir.startup()
            # Passamos 0.0 de combustivel apenas quando offline
            update_status_and_heartbeat("offline", "---", "---", 0.0, 0)
            file_initialized = False
            time.sleep(1)
            continue

        car_idx = ir['DriverInfo']['DriverCarIdx']
        if car_idx < 0:
            update_status_and_heartbeat("connected", "Unknown", "---", 0.0, 0)
            time.sleep(0.5)
            continue

        # ===== DADOS ATUAIS (Importante pegar antes de tudo) =====
        fuel_now = ir['FuelLevel']
        pos_g, pos_c = get_valid_position()
        
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
        
        # Define Estado e atualiza Heartbeat com DADOS REAIS
        current_state = "cockpit" if ir['SessionState'] > 3 else "connected"
        update_status_and_heartbeat(current_state, current_driver, track_name, fuel_now, pos_g)

        if session_num != last_session_num:
            laps_window.clear()
            fuel_window.clear()
            grid_recorded = False
            last_recorded_lap_time = -1.0
            last_session_num = session_num
            print(f"🔄 Nova Sessão Detectada: {session_name}")

        # ===== Inicializa CSV =====
        if not file_initialized:
            pd.DataFrame(columns=[
                "Timestamp", "Sessao", "Pista", "Equipe",
                "Piloto", "UserID", "Volta", "Tempo",
                "Media_3_Voltas", "Consumo_Volta",
                "Media_Consumo_3_Voltas", "Combustivel_Restante",
                "Pos_Geral", "Pos_Classe", "Voltas_Restantes_Estimadas"
            ]).to_csv(CSV_PATH, index=False)
            file_initialized = True
            
        # ===== GRID (Lógica recuperada do script local) =====
        # Garante que temos um ponto de partida de combustível
        if (not grid_recorded and ir['SessionState'] == 4 and fuel_now > 0.5):
            fuel_at_lap_start = fuel_now
            grid_recorded = True
            print(f"🟢 [GRID] {current_driver} alinhado com {fuel_now:.2f}L")

        # ===== DETECÇÃO DE VOLTA =====
        lap_last_time = ir['LapLastLapTime']

        if lap_last_time > 0 and lap_last_time != last_recorded_lap_time:

            time.sleep(0.8)  # Consolidação leve

            # --- ESTRATÉGIA DE EQUIPE: CONTAGEM GLOBAL ---
            # CarIdxLap pega a volta do carro no servidor, independente de quem pilota
            current_car_lap = ir['CarIdxLap'][car_idx]-1.0  # Ajuste para refletir a volta completa anterior, já que o iRacing atualiza no início da nova volta

            # Revalida dados após consolidação
            driver_data = ir['DriverInfo']['Drivers'][car_idx]
            current_driver = driver_data.get('UserName', 'Unknown')
            fuel_now = ir['FuelLevel']
            pos_g, pos_c = get_valid_position()

            # Tempo médio das últimas voltas
            laps_window.append(lap_last_time)
            avg_lap_time = sum(laps_window) / len(laps_window)

            # Voltas Estimadas (Mantido sua lógica original)
            session_laps_remain = ir['SessionLapsRemain']
            session_time_remain = ir['SessionTimeRemain']
            if session_laps_remain > 0 and session_laps_remain < 10000:
                voltas_estimadas = session_laps_remain
            elif avg_lap_time > 0 and session_time_remain > 0:
                voltas_estimadas = round(session_time_remain / avg_lap_time, 1)
            else:
                voltas_estimadas = 0            

            # --- PROTEÇÃO DRIVER SWAP (Rodrigo) ---
            # Se fuel_now for 0, o Rodrigo está pilotando e o dado local é inválido
            if fuel_now > 0.1 and fuel_at_lap_start > fuel_now:
                consumo = max(0.0, fuel_at_lap_start - fuel_now)
                if 0 < consumo < 20:
                    fuel_window.append(consumo)
            else:
                consumo = 0.0 # Evita picos de 40L no CSV

            avg_fuel = sum(fuel_window) / len(fuel_window) if fuel_window else consumo

            data = {
                "Timestamp": time.strftime("%H:%M:%S"),
                "Sessao": session_name, "Pista": track_name,
                "Equipe": team_name, "Piloto": current_driver,
                "UserID": current_user_id, "Volta": current_car_lap,  # Volta completa é a anterior
                "Tempo": round(lap_last_time, 3), "Media_3_Voltas": round(avg_lap_time, 3),
                "Consumo_Volta": round(consumo, 3), "Media_Consumo_3_Voltas": round(avg_fuel, 3),
                "Combustivel_Restante": round(fuel_now, 3),
                "Pos_Geral": pos_g, "Pos_Classe": pos_c,
                "Voltas_Restantes_Estimadas": voltas_estimadas
            }

            # 1. Salva Local
            pd.DataFrame([data]).to_csv(CSV_PATH, mode='a', index=False, header=False)
            
            # 2. Envia para Nuvem
            success = send_to_cloud(data)
            status_cloud = "✅ Cloud OK" if success else "❌ Cloud Fail"

            print(f"🏁 Volta {current_car_lap} | {current_driver} | {lap_last_time:.3f}s | {status_cloud}")

            last_recorded_lap_time = lap_last_time
            fuel_at_lap_start = fuel_now

        time.sleep(0.5)

except KeyboardInterrupt:
    update_status_and_heartbeat("offline", "---", "---", 0.0, 0)
finally:
    ir.shutdown()