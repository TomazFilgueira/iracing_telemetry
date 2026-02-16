import irsdk
import time
import pandas as pd
import json
from collections import deque
from config import LOG_DIR, WINDOW_SIZE

# ==============================
# Configuração
# ==============================
STATUS_PATH = LOG_DIR / "status.json"
timestamp = time.strftime("%Y%m%d_%H%M%S")
CSV_PATH = LOG_DIR / f"stint_{timestamp}.csv"

ir = irsdk.IRSDK()

# ==============================
# Funções auxiliares
# ==============================

def update_status(state, driver="---", track="---"):
    status_data = {
        "state": state,
        "driver": driver,
        "track": track,
        "last_update": time.time()
    }
    with open(STATUS_PATH, "w") as f:
        json.dump(status_data, f)

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
            last_valid_pos_g = pos_g
            last_valid_pos_c = pos_c

        return last_valid_pos_g, last_valid_pos_c
    except:
        return last_valid_pos_g, last_valid_pos_c

# ==============================
# Controle
# ==============================

last_session_num = -1
last_recorded_lap_time = -1.0
fuel_at_lap_start = -1.0
file_initialized = False
grid_recorded = False

laps_window = deque(maxlen=WINDOW_SIZE)
fuel_window = deque(maxlen=WINDOW_SIZE)

print("📡 Telemetria Dinâmica Ativa - LapLastLapTime Trigger")

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
            time.sleep(0.2)
            continue

        # ===== PILOTO ATIVO (MESMA LÓGICA DO DEBUG FUNCIONAL) =====
        try:
            driver_data = ir['DriverInfo']['Drivers'][car_idx]
            current_driver = driver_data.get('UserName', 'Unknown')
            current_user_id = driver_data.get('UserID', -1)
            team_name = driver_data.get('TeamName', 'N/A')
        except:
            current_driver = "Unknown"
            current_user_id = -1
            team_name = "N/A"

        # ===== Sessão =====
        session_num = ir['SessionNum']
        session_name = get_session_type(session_num)

        if session_num != last_session_num:
            laps_window.clear()
            fuel_window.clear()
            grid_recorded = False
            last_recorded_lap_time = -1.0
            last_session_num = session_num
            print(f"🔄 Nova Sessão: {session_name}")

        track_name = ir['WeekendInfo']['TrackDisplayName']
        update_status("cockpit", current_driver, track_name)

        fuel_now = ir['FuelLevel']
        pos_g, pos_c = get_valid_position()

        # ===== Inicializa CSV =====
        if not file_initialized:
            pd.DataFrame(columns=[
                "Timestamp", "Sessao", "Pista", "Equipe",
                "Piloto", "UserID",
                "Tempo",
                "Media_3_Voltas",
                "Consumo_Volta",
                "Media_Consumo_3_Voltas",
                "Combustivel_Restante",
                "Pos_Geral",
                "Pos_Classe",
                "Voltas_Restantes_Estimadas"
            ]).to_csv(CSV_PATH, index=False)
            file_initialized = True

        # ===== GRID =====
        if (
            not grid_recorded
            and ir['SessionState'] == 4
            and fuel_now > 0.5
        ):
            fuel_at_lap_start = fuel_now
            grid_recorded = True
            print(f"🏁 GRID | {current_driver}")

        # ===== DETECÇÃO DE VOLTA (LapLastLapTime Trigger) =====
        lap_last_time = ir['LapLastLapTime']

        if lap_last_time > 0 and lap_last_time != last_recorded_lap_time:

            time.sleep(0.8)  # consolidação leve

            # Revalida piloto após consolidação
            driver_data = ir['DriverInfo']['Drivers'][car_idx]
            current_driver = driver_data.get('UserName', 'Unknown')
            current_user_id = driver_data.get('UserID', -1)
            fuel_now = ir['FuelLevel']

            laps_window.append(lap_last_time)
            avg_lap_time = sum(laps_window) / len(laps_window)

            consumo = max(0.0, fuel_at_lap_start - fuel_now)
            if 0 < consumo < 20:
                fuel_window.append(consumo)

            avg_fuel = sum(fuel_window) / len(fuel_window) if fuel_window else consumo

            data = {
                "Timestamp": time.strftime("%H:%M:%S"),
                "Sessao": session_name,
                "Pista": track_name,
                "Equipe": team_name,
                "Piloto": current_driver,
                "UserID": current_user_id,
                "Tempo": round(lap_last_time, 3),
                "Media_3_Voltas": round(avg_lap_time, 3),
                "Consumo_Volta": round(consumo, 3),
                "Media_Consumo_3_Voltas": round(avg_fuel, 3),
                "Combustivel_Restante": round(fuel_now, 3),
                "Pos_Geral": pos_g,
                "Pos_Classe": pos_c,
                "Voltas_Restantes_Estimadas": 0
            }

            pd.DataFrame([data]).to_csv(
                CSV_PATH, mode='a', index=False, header=False
            )

            print(f"🏁 Volta | {current_driver} | {lap_last_time:.3f}s")

            last_recorded_lap_time = lap_last_time
            fuel_at_lap_start = fuel_now

        time.sleep(0.2)

except KeyboardInterrupt:
    update_status("offline")

finally:
    ir.shutdown()
