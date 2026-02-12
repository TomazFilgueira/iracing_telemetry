import irsdk
import time
import pandas as pd
from collections import deque
from config import LOG_DIR, WINDOW_SIZE # Importa do config.py

# Gera um nome único para a sessão atual
timestamp = time.strftime("%Y%m%d_%H%M%S")
CSV_PATH = LOG_DIR / f"stint_{timestamp}.csv"

ir = irsdk.IRSDK()
ir.startup()

# Variáveis de controle
last_completed_lap = -1
last_recorded_val = -1.0
fuel_at_lap_start = -1.0
driver_name = "Conectando..."
laps_window = deque(maxlen=WINDOW_SIZE)

print(f"🏎️ Captura ativa! Gravando em: {CSV_PATH.name}")

try:
    while True:
        if ir.is_connected:
            if driver_name == "Conectando...":
                try:
                    idx = ir['DriverInfo']['DriverCarIdx']
                    driver_name = ir['DriverInfo']['Drivers'][idx]['UserName']
                    fuel_at_lap_start = ir['FuelLevel']
                    print(f"✅ Piloto: {driver_name}")
                except: pass

            completed_laps = ir['LapCompleted']
            
            if completed_laps > last_completed_lap:
                new_time = ir['LapLastLapTime']
                if new_time > 0 and new_time != last_recorded_val:
                    laps_window.append(new_time)
                    avg_lap_time = sum(laps_window) / len(laps_window)
                    
                    fuel_now = ir['FuelLevel']
                    consumo = max(0.0, fuel_at_lap_start - fuel_now)
                    tempo_restante = ir['SessionTimeRemain']
                    voltas_est = tempo_restante / avg_lap_time if avg_lap_time > 0 else 0

                    data = {
                        "Timestamp": time.strftime("%H:%M:%S"),
                        "Piloto": driver_name,
                        "Volta": completed_laps,
                        "Tempo": round(new_time, 3),
                        "Media_3_Voltas": round(avg_lap_time, 3),
                        "Consumo_Volta": round(consumo, 3),
                        "Combustivel_Restante": round(fuel_now, 3),
                        "Tempo_Prova_Restante_s": round(tempo_restante, 1),
                        "Voltas_Restantes_Estimadas": round(voltas_est, 2),
                        "Pista": ir['WeekendInfo']['TrackName']
                    }
                    
                    pd.DataFrame([data]).to_csv(CSV_PATH, mode='a', index=False, header=not CSV_PATH.exists())
                    print(f"🏁 Volta {completed_laps}: {new_time:.3f}s")
                    
                    last_recorded_val, last_completed_lap, fuel_at_lap_start = new_time, completed_laps, fuel_now

            time.sleep(0.1)
        else:
            driver_name, last_completed_lap = "Conectando...", -1
            laps_window.clear()
            time.sleep(2)
except KeyboardInterrupt:
    print("🛑 Encerrado.")
finally:
    ir.shutdown()