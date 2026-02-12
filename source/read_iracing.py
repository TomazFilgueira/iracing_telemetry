import irsdk
import time
import pandas as pd
from pathlib import Path
from collections import deque # Para gerenciar a janela das últimas 3 voltas

# --- CONFIGURAÇÃO ---
CSV_PATH = Path("C:/Users/to_fi/OneDrive/Documents/GitHub/MyProjects/iracing_telemetry/Data_Logs/stint_telemetry.csv")
CSV_PATH.parent.mkdir(parents=True, exist_ok=True)

ir = irsdk.IRSDK()
ir.startup()

# Variáveis de controle
last_completed_lap = -1
last_recorded_val = -1.0
fuel_at_lap_start = -1.0
driver_name = "Conectando..."

# Janela deslizante para as últimas 3 voltas
laps_window = deque(maxlen=3)

print(f"🏎️ Monitoramento com Média Móvel (3 voltas) iniciado.")
print(f"Salvando em: {CSV_PATH}")

try:
    while True:
        if ir.is_connected:
            if driver_name == "Conectando...":
                try:
                    idx = ir['DriverInfo']['DriverCarIdx']
                    driver_name = ir['DriverInfo']['Drivers'][idx]['UserName']
                    fuel_at_lap_start = ir['FuelLevel']
                    print(f"✅ Piloto Identificado: {driver_name}")
                except: pass

            completed_laps = ir['LapCompleted']
            
            if completed_laps > last_completed_lap:
                new_time = ir['LapLastLapTime']
                attempts = 0
                
                while new_time == last_recorded_val and attempts < 10:
                    time.sleep(0.1)
                    new_time = ir['LapLastLapTime']
                    attempts += 1

                if new_time > 0 and new_time != last_recorded_val:
                    # 1. Adiciona o tempo da nova volta na janela de 3
                    laps_window.append(new_time)
                    
                    # 2. Calcula a média da janela (1, 2 ou 3 voltas dependendo do início)
                    avg_lap_time = sum(laps_window) / len(laps_window)
                    
                    fuel_now = ir['FuelLevel']
                    consumo_volta = fuel_at_lap_start - fuel_now
                    if consumo_volta < 0: consumo_volta = 0.0

                    tempo_restante_s = ir['SessionTimeRemain']
                    
                    # 3. Cálculo de voltas restantes baseado na MÉDIA
                    if avg_lap_time > 0:
                        voltas_restantes_estimadas = tempo_restante_s / avg_lap_time
                    else:
                        voltas_restantes_estimadas = 0

                    data_row = {
                        "Timestamp": time.strftime("%H:%M:%S"),
                        "Piloto": driver_name,
                        "Volta": completed_laps,
                        "Tempo": round(new_time, 3),
                        "Media_3_Voltas": round(avg_lap_time, 3), # Nova coluna para análise
                        "Consumo_Volta": round(consumo_volta, 3),
                        "Combustivel_Restante": round(fuel_now, 3),
                        "Tempo_Prova_Restante_s": round(tempo_restante_s, 1),
                        "Voltas_Restantes_Estimadas": round(voltas_restantes_estimadas, 2),
                        "Pista": ir['WeekendInfo']['TrackName']
                    }
                    
                    df = pd.DataFrame([data_row])
                    df.to_csv(CSV_PATH, mode='a', index=False, header=not CSV_PATH.exists())
                    
                    print(f"🏁 Volta {completed_laps} | Tempo: {new_time:.3f}s | Média(3v): {avg_lap_time:.3f}s | Restam ~{voltas_restantes_estimadas:.1f} vts")
                    
                    last_recorded_val = new_time
                    last_completed_lap = completed_laps
                    fuel_at_lap_start = fuel_now

            elif completed_laps < last_completed_lap:
                last_completed_lap = completed_laps
                last_recorded_val = -1.0
                fuel_at_lap_start = ir['FuelLevel']
                laps_window.clear() # Limpa a média se a sessão reiniciar

            time.sleep(0.1)
        else:
            driver_name = "Conectando..."
            laps_window.clear()
            time.sleep(2)

except KeyboardInterrupt:
    print("\n🛑 Monitoramento encerrado.")
finally:
    ir.shutdown()