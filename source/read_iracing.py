import irsdk
import time
import pandas as pd
from collections import deque
from config import LOG_DIR, WINDOW_SIZE

# Configuração de arquivo
timestamp = time.strftime("%Y%m%d_%H%M%S")
CSV_PATH = LOG_DIR / f"stint_{timestamp}.csv"

ir = irsdk.IRSDK()
ir.startup()

last_completed_lap = -1
fuel_at_lap_start = -1.0
laps_window = deque(maxlen=WINDOW_SIZE)

print(f"🏎️ Captura de Endurance com Dados de Equipe!")

try:
    while True:
        if ir.is_connected:
            try:
                my_car_idx = ir['DriverInfo']['DriverCarIdx']
                current_driver = ir['DriverInfo']['Drivers'][my_car_idx]['UserName']
                # Captura nome da equipe e posições
                team_name = ir['DriverInfo']['Drivers'][my_car_idx]['TeamName']
                pos_geral = ir['PlayerCarPosition']
                pos_classe = ir['PlayerCarClassPosition']
            except:
                current_driver, team_name = "Desconhecido", "Equipe Indefinida"
                pos_geral, pos_classe = 0, 0

            completed_laps = ir['LapCompleted']
            
            if completed_laps > last_completed_lap:
                new_time = ir['LapLastLapTime']
                if new_time > 0:
                    fuel_now = ir['FuelLevel']
                    consumo = 0.0 if (fuel_at_lap_start == -1.0 or fuel_now > fuel_at_lap_start) else max(0.0, fuel_at_lap_start - fuel_now)
                    
                    data = {
                        "Timestamp": time.strftime("%H:%M:%S"),
                        "Equipe": team_name, # Novo dado
                        "Piloto": current_driver,
                        "Volta": completed_laps,
                        "Pos_Geral": pos_geral, # Novo dado
                        "Pos_Classe": pos_classe, # Novo dado
                        "Tempo": round(new_time, 3),
                        "Consumo_Volta": round(consumo, 3),
                        "Combustivel_Restante": round(fuel_now, 3),
                        "Voltas_Restantes_Estimadas": round(ir['SessionTimeRemain'] / new_time, 2) if new_time > 0 else 0
                    }
                    
                    pd.DataFrame([data]).to_csv(CSV_PATH, mode='a', index=False, header=not CSV_PATH.exists())
                    last_completed_lap, fuel_at_lap_start = completed_laps, fuel_now

            time.sleep(0.5)
        else:
            time.sleep(2)
except KeyboardInterrupt:
    print("🛑 Encerrado.")
finally:
    ir.shutdown()