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
SERVER_URL = "https://iracing-telemetry-vfak.onrender.com/telemetry"
SESSION_ID = "teste2"

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
        headers = {
            "Bypass-Tunnel-Reminder": "true",
            "User-Agent": "iRacingTelemetryClient/1.0"
        }
        requests.post(SERVER_URL, json=cloud_payload, headers=headers, timeout=1.0)
        return True
    except Exception as e:
        print(f"⚠️ Erro no Envio: {e}")
        return False


last_heartbeat_time = 0

def update_status_and_heartbeat(state, driver, track, fuel_current, pos_g):
    global last_heartbeat_time
    status_data = {
        "state": state,
        "driver": driver,
        "track": track,
        "last_update": time.time()
    }
    with open(STATUS_PATH, "w") as f:
        json.dump(status_data, f)

    if state != "offline" and (time.time() - last_heartbeat_time) > 2.0:
        heartbeat = {
            "Piloto": driver,
            "UserID": -1,
            "Volta": 0,
            "Tempo": 0.0,
            "Combustivel_Restante": float(fuel_current),
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
grid_recorded = False

# FIX 1: Grace period para is_driving
# Garante que a in-lap (entrada no pit cruzando a linha) ainda seja registrada
# mesmo que is_driving vire False logo após o cruzamento.
last_on_track_time = 0.0
DRIVING_GRACE_SECONDS = 10.0

laps_window = deque(maxlen=WINDOW_SIZE)
fuel_window = deque(maxlen=WINDOW_SIZE)

print(f"📡 Telemetria Cloud Ativa - Enviando para: {SERVER_URL}")

try:
    while True:
        if not ir.is_connected:
            ir.startup()
            update_status_and_heartbeat("offline", "---", "---", 0.0, 0)
            file_initialized = False
            time.sleep(1)
            continue

        car_idx = ir['DriverInfo']['DriverCarIdx']
        if car_idx < 0:
            update_status_and_heartbeat("connected", "Unknown", "---", 0.0, 0)
            time.sleep(0.5)
            continue

        # ===== DADOS ATUAIS =====
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
        is_driving = ir['IsOnTrack']

        # FIX 1: Atualiza o timestamp da última vez que estava no carro
        if is_driving:
            last_on_track_time = time.time()

        # Grace period: considera "recentemente no carro" por DRIVING_GRACE_SECONDS
        recently_driving = (time.time() - last_on_track_time) < DRIVING_GRACE_SECONDS

        current_state = "cockpit" if is_driving else "connected"
        update_status_and_heartbeat(current_state, current_driver, track_name, fuel_now, pos_g)

        if session_num != last_session_num:
            laps_window.clear()
            fuel_window.clear()
            grid_recorded = False
            last_recorded_lap_time = -1.0
            fuel_at_lap_start = -1.0
            last_on_track_time = 0.0
            last_session_num = session_num
            print(f"🔄 Nova Sessão Detectada: {session_name}")

        # ===== Inicializa CSV =====
        if not file_initialized:
            pd.DataFrame(columns=[
                "Timestamp", "Sessao", "Pista", "Equipe",
                "Piloto", "UserID", "Volta", "Tempo",
                "Media_3_Voltas", "Consumo_Volta",
                "Media_Consumo_3_Voltas", "Combustivel_Restante",
                "Combustivel_no_Inicio_Volta",  # NOVO: tanque no início da volta
                "Pos_Geral", "Pos_Classe", "Voltas_Restantes_Estimadas", "state"
            ]).to_csv(CSV_PATH, index=False)
            file_initialized = True

        # ===== GRID =====
        if not grid_recorded and ir['SessionState'] == 4 and fuel_now > 0.5:
            fuel_at_lap_start = fuel_now
            grid_recorded = True
            print(f"🟢 [GRID] {current_driver} alinhado com {fuel_now:.2f}L")

        # ===== DETECÇÃO DE VOLTA =====
        lap_last_time = ir['LapLastLapTime']

        # FIX 1: Usa grace period em vez de is_driving puro.
        # Isso evita perder a in-lap quando is_driving vira False no cruzamento da linha do pit.
        if lap_last_time > 0 and lap_last_time != last_recorded_lap_time and recently_driving:

            # FIX 2: Captura o combustível ANTES do sleep para ter o valor pré-reabastecimento.
            # O sleep(1.5) pode ocorrer durante o refuel, corrompendo fuel_at_lap_start.
            fuel_before_sleep = ir['FuelLevel']

            time.sleep(1.5)  # Consolidação leve

            # ===== ESTRATÉGIA DE EQUIPE: CONTAGEM GLOBAL =====
            current_car_lap = ir['CarIdxLap'][car_idx] - 1.0

            driver_data = ir['DriverInfo']['Drivers'][car_idx]
            current_driver = driver_data.get('UserName', 'Unknown')
            fuel_now = ir['FuelLevel']  # Valor pós-sleep (pode ser durante/pós-refuel)
            pos_g, pos_c = get_valid_position()

            # FIX 2: Inicialização de fuel_at_lap_start na primeira volta
            # (quando o grid não foi capturado, ex: driver entrou na sessão tarde)
            if fuel_at_lap_start < 0 and fuel_before_sleep > 0.5:
                fuel_at_lap_start = fuel_before_sleep
                print(f"⛽ [INIT] fuel_at_lap_start inicializado: {fuel_before_sleep:.2f}L")

            # Tempo médio das últimas voltas
            laps_window.append(lap_last_time)
            avg_lap_time = sum(laps_window) / len(laps_window)

            # Voltas Estimadas
            session_laps_remain = ir['SessionLapsRemain']
            session_time_remain = ir['SessionTimeRemain']
            if session_laps_remain > 0 and session_laps_remain < 10000:
                voltas_estimadas = session_laps_remain
            elif avg_lap_time > 0 and session_time_remain > 0:
                voltas_estimadas = round(session_time_remain / avg_lap_time, 1)
            else:
                voltas_estimadas = 0

            # FIX 3: Cálculo de consumo com detecção de reabastecimento.
            #
            # Problema original: sleep(1.5) capturava fuel_now durante o refuel
            # (ex: 40L de 60L), fuel_at_lap_start ficava com 40L.
            # Na próxima volta fuel_now=57L > 40L → consumo=0. Duas voltas zeradas.
            #
            # Solução: usa fuel_before_sleep (capturado antes do sleep, sem refuel)
            # para calcular o consumo real da volta. Detecta refuel pela diferença
            # entre fuel_now (pós-sleep) e fuel_before_sleep.
            #
            REFUEL_THRESHOLD = 2.0  # Litros: delta acima disso = reabastecimento

            refuel_happened = (fuel_now - fuel_before_sleep) > REFUEL_THRESHOLD
            consumo_reference = fuel_before_sleep  # Referência limpa pré-refuel

            if refuel_happened:
                print(f"⛽ [REFUEL] Reabastecimento: {fuel_at_lap_start:.1f}L → {fuel_before_sleep:.1f}L → {fuel_now:.1f}L")

            if fuel_at_lap_start > 0.1 and fuel_at_lap_start > consumo_reference:
                consumo = max(0.0, fuel_at_lap_start - consumo_reference)
                if 0 < consumo < 20:
                    fuel_window.append(consumo)
            else:
                # Sem referência válida ou refuel detectado sem consumo calculável
                consumo = 0.0

            avg_fuel = sum(fuel_window) / len(fuel_window) if fuel_window else consumo

            data = {
                "Timestamp": time.strftime("%H:%M:%S"),
                "Sessao": session_name, "Pista": track_name,
                "Equipe": team_name, "Piloto": current_driver,
                "UserID": current_user_id, "Volta": current_car_lap,
                "Tempo": round(lap_last_time, 3),
                "Media_3_Voltas": round(avg_lap_time, 3),
                "Consumo_Volta": round(consumo, 3),
                "Media_Consumo_3_Voltas": round(avg_fuel, 3),
                "Combustivel_Restante": round(fuel_now, 3),
                "Combustivel_no_Inicio_Volta": round(fuel_at_lap_start, 3),  # NOVO
                "Pos_Geral": pos_g, "Pos_Classe": pos_c,
                "Voltas_Restantes_Estimadas": voltas_estimadas,
                "state": current_state
            }

            # 1. Salva Local
            pd.DataFrame([data]).to_csv(CSV_PATH, mode='a', index=False, header=False)

            # 2. Envia para Nuvem
            success = send_to_cloud(data)
            status_cloud = "✅ Cloud OK" if success else "❌ Cloud Fail"
            refuel_tag = " | ⛽ REFUEL" if refuel_happened else ""
            print(f"🏁 Volta {current_car_lap} | {current_driver} | {lap_last_time:.3f}s | Consumo: {consumo:.3f}L{refuel_tag} | {status_cloud}")

            last_recorded_lap_time = lap_last_time
            # FIX 3: Sempre atualiza com fuel_now (pós-refuel se houve)
            fuel_at_lap_start = fuel_now

        time.sleep(0.5)

except KeyboardInterrupt:
    update_status_and_heartbeat("offline", "---", "---", 0.0, 0)
finally:
    ir.shutdown()