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

# Variáveis de controle
last_completed_lap = -1
last_recorded_val = -1.0  # Trava para evitar tempos duplicados
fuel_at_lap_start = -1.0
laps_window = deque(maxlen=WINDOW_SIZE)

print(f"🏎️ Sistema de Telemetria Ativo...")

try:
    while True:
        if ir.is_connected:
            # 1. TRAVA DE SEGURANÇA: Só prossegue se o índice do carro for válido
            my_car_idx = ir['DriverInfo']['DriverCarIdx']
            
            if my_car_idx < 0:
                print("⏳ Aguardando você entrar no cockpit/grid...")
                time.sleep(2)
                continue

            completed_laps = ir['LapCompleted']
            
            if completed_laps > last_completed_lap:
                # --- SINCRONIA DE DADOS (CRUCIAL PARA IA E MULTICLASSE) ---
                # Aguarda o iRacing processar os standings e limpar o buffer de tempo
                time.sleep(0.25) 
                
                new_time = ir['LapLastLapTime']
                
                # Só processamos se o tempo for novo e válido
                if new_time > 0 and new_time != last_recorded_val:
                    try:
                        # 2. Captura dinâmica após o delay para garantir dados atualizados
                        current_driver = ir['DriverInfo']['Drivers'][my_car_idx]['UserName']
                        team_name = ir['DriverInfo']['Drivers'][my_car_idx]['TeamName']
                        track_name = ir['WeekendInfo']['TrackDisplayName']
                        
                        # Re-leitura das posições pós-delay
                        pos_geral = ir['PlayerCarPosition']
                        pos_classe = ir['PlayerCarClassPosition']
                    except (KeyError, IndexError, TypeError):
                        time.sleep(1)
                        continue

                    # Cálculo da Média Móvel
                    laps_window.append(new_time)
                    avg_lap_time = sum(laps_window) / len(laps_window)
                    
                    fuel_now = ir['FuelLevel']
                    # Lógica de consumo (detecta reabastecimento)
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
                    
                    pd.DataFrame([data]).to_csv(CSV_PATH, mode='a', index=False, header=not CSV_PATH.exists())
                    print(f"🏁 [{current_driver}] Volta {completed_laps} gravada: {new_time:.3f}s (P{int(pos_classe)})")
                    
                    # Atualiza as travas de segurança
                    last_recorded_val = new_time
                    last_completed_lap = completed_laps
                    fuel_at_lap_start = fuel_now

            time.sleep(0.5)
        else:
            # Reseta estado se a conexão cair
            last_completed_lap, last_recorded_val = -1, -1.0
            fuel_at_lap_start = -1.0
            laps_window.clear()
            time.sleep(2)
except KeyboardInterrupt:
    print("🛑 Encerrado.")
finally:
    ir.shutdown()