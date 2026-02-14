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
    """Salva o estado atual para o Dashboard ler em tempo real."""
    status_data = {
        "state": state, # 'offline', 'connected', 'cockpit'
        "driver": driver,
        "track": track,
        "last_update": time.time()
    }
    with open(STATUS_PATH, "w") as f:
        json.dump(status_data, f)

# Variáveis de controle de telemetria
last_completed_lap = -1
last_recorded_val = -1.0
fuel_at_lap_start = -1.0
file_initialized = False
laps_window = deque(maxlen=WINDOW_SIZE)

print(f"📡 Sistema de Telemetria com Traffic Light Ativo...")

try:
    while True:
        # Tenta conectar se o link estiver caído
        if not ir.is_connected:
            ir.startup()
            update_status("offline")
            file_initialized = False
        
        if ir.is_connected:
            my_car_idx = ir['DriverInfo']['DriverCarIdx']
            
            # ESTADO 1: Conectado ao SDK, mas no Menu/Replay
            if my_car_idx < 0:
                update_status("connected")
                file_initialized = False
                time.sleep(1)
                continue

            # ESTADO 2: Piloto no Cockpit
            try:
                current_driver = ir['DriverInfo']['Drivers'][my_car_idx]['UserName']
                track_name = ir['WeekendInfo']['TrackDisplayName']
                update_status("cockpit", current_driver, track_name)
            except:
                continue

            # INICIALIZAÇÃO DO CSV E SINCRONIA INICIAL
            if not file_initialized:
                # Sincroniza voltas e combustível ao entrar no carro para evitar erros de cálculo
                last_completed_lap = ir['LapCompleted']
                fuel_at_lap_start = ir['FuelLevel']
                
                header_df = pd.DataFrame(columns=[
                    "Timestamp", "Pista", "Equipe", "Piloto", "Volta", "Tempo", 
                    "Media_3_Voltas", "Consumo_Volta", "Combustivel_Restante", 
                    "Pos_Geral", "Pos_Classe", "Voltas_Restantes_Estimadas"
                ])
                header_df.to_csv(CSV_PATH, index=False)
                file_initialized = True
                print(f"✅ Telemetria Capturando: {current_driver} em {track_name}")

            # LÓGICA DE PROCESSAMENTO DE VOLTA COMPLETADA
            completed_laps = ir['LapCompleted']
            if completed_laps > last_completed_lap:
                # Delay de sincronia para o buffer do SDK atualizar (essencial para IA/Multiclasse)
                time.sleep(0.3) 
                new_time = ir['LapLastLapTime']
                
                # Validação de tempo para evitar duplicatas (Erro de Summit Point)
                if new_time > 0 and new_time != last_recorded_val:
                    try:
                        # Cálculo de Performance e Média Móvel
                        laps_window.append(new_time)
                        avg_lap_time = sum(laps_window) / len(laps_window)
                        
                        # Cálculo de Consumo (Detecta se houve reabastecimento)
                        fuel_now = ir['FuelLevel']
                        if fuel_at_lap_start == -1.0 or fuel_now > fuel_at_lap_start:
                            consumo = 0.0
                        else:
                            consumo = max(0.0, fuel_at_lap_start - fuel_now)
                        
                        # Montagem do registro para o CSV
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
                        
                        # Gravação Incremental (Append) no CSV
                        pd.DataFrame([data]).to_csv(CSV_PATH, mode='a', index=False, header=False)
                        print(f"🏁 Volta {completed_laps} gravada: {new_time:.3f}s")
                        
                        # Atualização de estados para a próxima volta
                        last_recorded_val = new_time
                        last_completed_lap = completed_laps
                        fuel_at_lap_start = fuel_now 
                    except Exception as e:
                        print(f"⚠️ Erro ao processar dados da volta: {e}")
            
            time.sleep(0.5)
        else:
            time.sleep(2)
except KeyboardInterrupt:
    update_status("offline")
    print("🛑 Coleta encerrada pelo usuário.")
finally:
    ir.shutdown()