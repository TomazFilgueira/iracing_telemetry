import irsdk
import time
import pandas as pd
import json
from collections import deque
from config import LOG_DIR, WINDOW_SIZE

# Configuração de caminhos e arquivos
STATUS_PATH = LOG_DIR / "status.json"
timestamp = time.strftime("%Y%m%d_%H%M%S")
CSV_PATH = LOG_DIR / f"stint_{timestamp}.csv"

ir = irsdk.IRSDK()

def update_status(state, driver="---", track="---"):
    """Atualiza o Traffic Light para o Dashboard."""
    status_data = {
        "state": state,
        "driver": driver,
        "track": track,
        "last_update": time.time()
    }
    with open(STATUS_PATH, "w") as f:
        json.dump(status_data, f)

# Variáveis de controle
last_completed_lap = -1
last_recorded_val = -1.0
fuel_at_lap_start = -1.0
file_initialized = False
grid_recorded = False  # Gatilho para a Volta 0
laps_window = deque(maxlen=WINDOW_SIZE)

print(f"📡 Telemetria Online - Monitorando Estado 4 (Racing)...")

try:
    while True:
        if not ir.is_connected:
            ir.startup()
            update_status("offline")
            file_initialized = False
            grid_recorded = False
            time.sleep(1)
            continue
        
        my_car_idx = ir['DriverInfo']['DriverCarIdx']
        
        if my_car_idx < 0:
            update_status("connected")
            time.sleep(1)
            continue

        # ESTADO ATUAL DO SIMULADOR
        current_driver = ir['DriverInfo']['Drivers'][my_car_idx]['UserName']
        track_name = ir['WeekendInfo']['TrackDisplayName']
        session_state = ir['SessionState'] 
        update_status("cockpit", current_driver, track_name)

        # 1. INICIALIZAÇÃO DO CSV (Ao entrar no cockpit)
        if not file_initialized:
            header_df = pd.DataFrame(columns=[
                "Timestamp", "Pista", "Equipe", "Piloto", "Volta", "Tempo", 
                "Media_3_Voltas", "Consumo_Volta", "Combustivel_Restante", 
                "Pos_Geral", "Pos_Classe", "Voltas_Restantes_Estimadas"
            ])
            header_df.to_csv(CSV_PATH, index=False)
            file_initialized = True
            last_completed_lap = ir['LapCompleted']
            fuel_at_lap_start = ir['FuelLevel']
            print(f"✅ CSV Criado. Aguardando Estado 4 para Volta 0...")

        # 2. REGISTRO DA VOLTA 0 (Baseado no seu Debug: Estado 4)
        if not grid_recorded and session_state == 4:
            pos_g = ir['PlayerCarPosition']
            pos_c = ir['PlayerCarClassPosition']
            
            # Garante que as posições já foram calculadas pelo simulador
            if pos_g > 0:
                grid_data = {
                    "Timestamp": time.strftime("%H:%M:%S"),
                    "Pista": track_name,
                    "Equipe": ir['DriverInfo']['Drivers'][my_car_idx]['TeamName'],
                    "Piloto": current_driver,
                    "Volta": 0,
                    "Tempo": 0.0,
                    "Media_3_Voltas": 0.0,
                    "Consumo_Volta": 0.0,
                    "Combustivel_Restante": round(ir['FuelLevel'], 3),
                    "Pos_Geral": pos_g,
                    "Pos_Classe": pos_c,
                    "Voltas_Restantes_Estimadas": 0
                }
                pd.DataFrame([grid_data]).to_csv(CSV_PATH, mode='a', index=False, header=False)
                grid_recorded = True
                print(f"🏁 LARGADA DETECTADA (Estado 4)! Posição Inicial: P{int(pos_c)}")

        # 3. LÓGICA DE VOLTAS COMPLETADAS (A partir da Volta 1)
        completed_laps = ir['LapCompleted']
        if completed_laps > last_completed_lap:
            time.sleep(0.3) 
            new_time = ir['LapLastLapTime']
            
            if new_time > 0 and new_time != last_recorded_val:
                try:
                    laps_window.append(new_time)
                    avg_lap_time = sum(laps_window) / len(laps_window)
                    fuel_now = ir['FuelLevel']
                    consumo = max(0.0, fuel_at_lap_start - fuel_now) if fuel_at_lap_start > fuel_now else 0.0
                    
                    data = {
                        "Timestamp": time.strftime("%H:%M:%S"),
                        "Pista": track_name,
                        "Equipe": ir['DriverInfo']['Drivers'][my_car_idx]['TeamName'],
                        "Piloto": current_driver,
                        "Volta": completed_laps,
                        "Tempo": round(new_time, 3),
                        "Media_3_Voltas": round(avg_lap_time, 3),
                        "Consumo_Volta": round(consumo, 3),
                        "Combustivel_Restante": round(fuel_now, 3),
                        "Pos_Geral": ir['PlayerCarPosition'],
                        "Pos_Classe": ir['PlayerCarClassPosition'],
                        "Voltas_Restantes_Estimadas": round(ir['SessionTimeRemain'] / avg_lap_time, 2) if avg_lap_time > 0 else 0
                    }
                    pd.DataFrame([data]).to_csv(CSV_PATH, mode='a', index=False, header=False)
                    print(f"🏁 Volta {completed_laps} gravada: {new_time:.3f}s")
                    
                    last_recorded_val, last_completed_lap = new_time, completed_laps
                    fuel_at_lap_start = fuel_now 
                except:
                    continue
        
        time.sleep(0.5)
except KeyboardInterrupt:
    update_status("offline")
finally:
    ir.shutdown()