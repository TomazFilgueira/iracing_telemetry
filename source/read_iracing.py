import irsdk
import time
import pandas as pd
import json
from collections import deque
from config import LOG_DIR, WINDOW_SIZE

# ==============================
# Configuração de caminhos
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


def get_active_driver(car_idx):
    try:
        driver_data = ir['DriverInfo']['Drivers'][car_idx]
        name = driver_data.get('UserName', 'Unknown')
        user_id = driver_data.get('UserID', -1)
        return name.strip(), user_id
    except:
        return "Unknown", -1


# ==============================
# Posição robusta
# ==============================

last_valid_pos_g = 0
last_valid_pos_c = 0

def get_valid_position():
    global last_valid_pos_g, last_valid_pos_c

    try:
        player_idx = ir['DriverInfo']['DriverCarIdx']
        if player_idx < 0:
            return last_valid_pos_g, last_valid_pos_c

        pos_vector = ir['CarIdxPosition']
        class_vector = ir['CarIdxClassPosition']

        pos_g = pos_vector[player_idx]
        pos_c = class_vector[player_idx]

        if pos_g > 0:
            last_valid_pos_g = pos_g
            last_valid_pos_c = pos_c

        return last_valid_pos_g, last_valid_pos_c

    except:
        return last_valid_pos_g, last_valid_pos_c


# ==============================
# Variáveis de controle
# ==============================

last_session_num = -1
last_completed_lap = -1
last_recorded_val = -1.0
fuel_at_lap_start = -1.0
file_initialized = False
grid_recorded = False

laps_window = deque(maxlen=WINDOW_SIZE)
fuel_window = deque(maxlen=WINDOW_SIZE)

print("📡 Telemetria Dinâmica Ativa - Team Swap Safe")

# ==============================
# LOOP PRINCIPAL
# ==============================

try:
    while True:

        if not ir.is_connected:
            ir.startup()
            update_status("offline")
            file_initialized = False
            time.sleep(1)
            continue

        my_car_idx = ir['DriverInfo']['DriverCarIdx']
        if my_car_idx < 0:
            update_status("connected")
            time.sleep(1)
            continue

        # ==============================
        # Sessão
        # ==============================
        current_session_num = ir['SessionNum']
        session_name = get_session_type(current_session_num)

        if current_session_num != last_session_num:
            grid_recorded = False
            last_completed_lap = ir['LapCompleted']
            laps_window.clear()
            fuel_window.clear()
            last_session_num = current_session_num
            print(f"🔄 Nova Sessão Detectada: {session_name}")

        session_state = ir['SessionState']
        track_name = ir['WeekendInfo']['TrackDisplayName']
        team_name = ir['DriverInfo']['Drivers'][my_car_idx]['TeamName']

        # Piloto ativo
        current_driver, current_user_id = get_active_driver(my_car_idx)

        update_status("cockpit", current_driver, track_name)

        # ==============================
        # Inicialização CSV
        # ==============================
        if not file_initialized:
            pd.DataFrame(columns=[
                "Timestamp", "Sessao", "Pista", "Equipe",
                "Piloto", "UserID",
                "Volta", "Tempo",
                "Media_3_Voltas", "Consumo_Volta",
                "Media_Consumo_3_Voltas",
                "Combustivel_Restante",
                "Pos_Geral", "Pos_Classe",
                "Voltas_Restantes_Estimadas"
            ]).to_csv(CSV_PATH, index=False)
            file_initialized = True

        fuel_now = ir['FuelLevel']
        pos_g, pos_c = get_valid_position()

        # ==============================
        # GRID (Volta 0)
        # ==============================
        if (
            not grid_recorded
            and session_state == 4
            and fuel_now > 0.5
            and pos_g > 0
        ):
            fuel_at_lap_start = fuel_now

            grid_data = {
                "Timestamp": time.strftime("%H:%M:%S"),
                "Sessao": session_name,
                "Pista": track_name,
                "Equipe": team_name,
                "Piloto": current_driver,
                "UserID": current_user_id,
                "Volta": 0,
                "Tempo": 0.0,
                "Media_3_Voltas": 0.0,
                "Consumo_Volta": 0.0,
                "Media_Consumo_3_Voltas": 0.0,
                "Combustivel_Restante": round(fuel_now, 3),
                "Pos_Geral": pos_g,
                "Pos_Classe": pos_c,
                "Voltas_Restantes_Estimadas": 0
            }

            pd.DataFrame([grid_data]).to_csv(
                CSV_PATH, mode='a', index=False, header=False
            )

            grid_recorded = True
            print(f"🏁 GRID GRAVADO - {current_driver}")

        # ==============================
        # GRAVAÇÃO DE VOLTAS
        # ==============================
        completed_laps = ir['LapCompleted']

        if completed_laps > last_completed_lap:

            # Espera consolidação completa do SDK
            time.sleep(1.8)

            # Revalida piloto após consolidação
            current_driver, current_user_id = get_active_driver(my_car_idx)

            new_time = ir['LapLastLapTime']

            if new_time <= 0:
                continue

            if new_time == last_recorded_val:
                continue

            try:

                laps_window.append(new_time)
                avg_lap_time = sum(laps_window) / len(laps_window)

                consumo_imediato = (
                    max(0.0, fuel_at_lap_start - ir['FuelLevel'])
                    if fuel_at_lap_start > ir['FuelLevel'] else 0.0
                )

                if 0 < consumo_imediato < 20:
                    fuel_window.append(consumo_imediato)

                avg_fuel_cons = (
                    sum(fuel_window) / len(fuel_window)
                    if fuel_window else consumo_imediato
                )

                pos_g, pos_c = get_valid_position()

                data = {
                    "Timestamp": time.strftime("%H:%M:%S"),
                    "Sessao": session_name,
                    "Pista": track_name,
                    "Equipe": team_name,
                    "Piloto": current_driver,
                    "UserID": current_user_id,
                    "Volta": completed_laps,
                    "Tempo": round(new_time, 3),
                    "Media_3_Voltas": round(avg_lap_time, 3),
                    "Consumo_Volta": round(consumo_imediato, 3),
                    "Media_Consumo_3_Voltas": round(avg_fuel_cons, 3),
                    "Combustivel_Restante": round(ir['FuelLevel'], 3),
                    "Pos_Geral": pos_g,
                    "Pos_Classe": pos_c,
                    "Voltas_Restantes_Estimadas": (
                        round(ir['SessionTimeRemain'] / avg_lap_time, 2)
                        if avg_lap_time > 0 else 0
                    )
                }

                pd.DataFrame([data]).to_csv(
                    CSV_PATH, mode='a', index=False, header=False
                )

                print(f"🏁 Volta {completed_laps} | {current_driver} | {new_time:.3f}s")

                last_recorded_val = new_time
                last_completed_lap = completed_laps
                fuel_at_lap_start = ir['FuelLevel']

            except:
                continue

        time.sleep(0.3)

except KeyboardInterrupt:
    update_status("offline")

finally:
    ir.shutdown()
