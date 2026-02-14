import irsdk
import time
import pandas as pd
from collections import deque
from config import LOG_DIR, WINDOW_SIZE

# Configuração de arquivo única por sessão
timestamp = time.strftime("%Y%m%d_%H%M%S")
CSV_PATH = LOG_DIR / f"stint_{timestamp}.csv"

ir = irsdk.IRSDK()
ir.startup()

# Variáveis de controle e Janela Deslizante (Moving Average)
last_completed_lap = -1
fuel_at_lap_start = -1.0
laps_window = deque(maxlen=WINDOW_SIZE)

print(f"🏎️ Coletor Ativo | Gravando em: {CSV_PATH.name}")

try:
    while True:
        if ir.is_connected:
            try:
                # Captura dinâmica de contexto (suporta trocas de piloto)
                my_car_idx = ir['DriverInfo']['DriverCarIdx']
                current_driver = ir['DriverInfo']['Drivers'][my_car_idx]['UserName']
                team_name = ir['DriverInfo']['Drivers'][my_car_idx]['TeamName']
                track_name = ir['WeekendInfo']['TrackDisplayName']
                
                pos_geral = ir['PlayerCarPosition']
                pos_classe = ir['PlayerCarClassPosition']
            except:
                current_driver, team_name, track_name = "Conectando...", "---", "---"
                pos_geral, pos_classe = 0, 0

            completed_laps = ir['LapCompleted']
            
            if completed_laps > last_completed_lap:
                new_time = ir['LapLastLapTime']
                
                if new_time > 0:
                    # Atualiza a janela e calcula a Média Móvel
                    laps_window.append(new_time)
                    avg_lap_time = sum(laps_window) / len(laps_window)
                    
                    fuel_now = ir['FuelLevel']
                    # Lógica de consumo (detecta reabastecimento no box)
                    consumo = 0.0 if (fuel_at_lap_start == -1.0 or fuel_now > fuel_at_lap_start) else max(0.0, fuel_at_lap_start - fuel_now)
                    
                    data = {
                        "Timestamp": time.strftime("%H:%M:%S"),
                        "Pista": track_name,
                        "Equipe": team_name,
                        "Piloto": current_driver,
                        "Volta": completed_laps,
                        "Tempo": round(new_time, 3),
                        "Media_3_Voltas": round(avg_lap_time, 3),
                        "Consumo_Volta": round(consumo, 3),
                        "Combustivel_Restante": round(fuel_now, 3),
                        "Pos_Geral": pos_geral,
                        "Pos_Classe": pos_classe,
                        "Voltas_Restantes_Estimadas": round(ir['SessionTimeRemain'] / avg_lap_time, 2) if avg_lap_time > 0 else 0
                    }
                    
                    # Salva no CSV imediatamente para evitar perda de dados
                    pd.DataFrame([data]).to_csv(CSV_PATH, mode='a', index=False, header=not CSV_PATH.exists())
                    
                    print(f"🏁 [{current_driver}] Volta {completed_laps}: {new_time:.3f}s | Média: {avg_lap_time:.3f}s")
                    
                    last_completed_lap, fuel_at_lap_start = completed_laps, fuel_now

            time.sleep(0.5)
        else:
            # Reseta estado se o simulador for fechado
            last_completed_lap, fuel_at_lap_start = -1, -1.0
            laps_window.clear()
            time.sleep(2)
except KeyboardInterrupt:
    print("🛑 Captura encerrada pelo usuário.")
finally:
    ir.shutdown()