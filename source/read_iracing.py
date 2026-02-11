import irsdk
import time
import pandas as pd
from pathlib import Path

# --- CONFIGURAÇÃO ---
CSV_PATH = Path("C:/Users/PC/Documents/GitHub/Racing4all/Iracing/Data_Logs/stint_telemetry.csv")
CSV_PATH.parent.mkdir(parents=True, exist_ok=True)

ir = irsdk.IRSDK()
ir.startup()

# Variáveis de controle
last_completed_lap = -1
last_recorded_val = -1.0
driver_name = "Conectando..."

print("🏎️ Monitoramento iniciado. Aguardando conexão...")

try:
    while True:
        if ir.is_connected:
            # 1. Captura o nome do piloto (apenas se ainda não tiver)
            if driver_name == "Conectando...":
                try:
                    idx = ir['DriverInfo']['DriverCarIdx']
                    driver_name = ir['DriverInfo']['Drivers'][idx]['UserName']
                    print(f"✅ Piloto Identificado: {driver_name}")
                except: 
                    pass

            completed_laps = ir['LapCompleted']
            
            # 2. Lógica de fim de volta
            if completed_laps > last_completed_lap:
                
                # Sincronismo: Aguarda o iRacing atualizar o tempo da última volta
                new_time = ir['LapLastLapTime']
                attempts = 0
                
                while new_time == last_recorded_val and attempts < 10:
                    time.sleep(0.1)
                    new_time = ir['LapLastLapTime']
                    attempts += 1

                if new_time > 0 and new_time != last_recorded_val:
                    data_row = {
                        "Timestamp": time.strftime("%H:%M:%S"),
                        "Piloto": driver_name,  # Nome de volta ao log
                        "Volta": completed_laps,
                        "Tempo": round(new_time, 3),
                        "Consumo": round(ir['FuelLevel'], 3),
                        "Pista": ir['WeekendInfo']['TrackName']
                    }
                    
                    # Salva no CSV
                    df = pd.DataFrame([data_row])
                    df.to_csv(CSV_PATH, mode='a', index=False, header=not CSV_PATH.exists())
                    
                    print(f"✅ Volta {completed_laps} registrada para {driver_name}: {new_time:.3f}s")
                    
                    last_recorded_val = new_time
                    last_completed_lap = completed_laps

            # Reset se o piloto sair do carro ou reiniciar a sessão
            elif completed_laps < last_completed_lap:
                last_completed_lap = completed_laps
                last_recorded_val = -1.0

            time.sleep(0.1)
        else:
            driver_name = "Conectando..."
            last_completed_lap = -1
            time.sleep(2)

except KeyboardInterrupt:
    print("\n🛑 Monitoramento encerrado pelo usuário.")
finally:
    ir.shutdown()