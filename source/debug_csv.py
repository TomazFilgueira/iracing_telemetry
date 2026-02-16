import irsdk
import time
import os
import csv
from datetime import datetime

ir = irsdk.IRSDK()

print("🔎 DEBUG DRIVER + LAP LOGGER (LapLastLapTime Trigger)")
print("Pressione CTRL+C para sair\n")

# ============================
# Arquivo CSV
# ============================

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
CSV_FILE = f"debug_team_laps_{timestamp}.csv"

with open(CSV_FILE, mode='w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow([
        "Timestamp",
        "DriverName",
        "UserID",
        "Team",
        "LapTime"
    ])

print(f"📁 Salvando voltas em: {CSV_FILE}\n")

# ============================
# Controle
# ============================

last_driver_id = None
last_lap_time_saved = -1.0

def format_time(seconds):
    if seconds <= 0:
        return "00:00.000"
    minutes = int(seconds // 60)
    rem = seconds % 60
    return f"{minutes:02d}:{rem:06.3f}"

try:
    while True:

        if not ir.is_connected:
            print("⏳ Aguardando conexão com iRacing...")
            ir.startup()
            time.sleep(1)
            continue

        car_idx = ir['DriverInfo']['DriverCarIdx']
        if car_idx < 0:
            time.sleep(0.2)
            continue

        # ===== PILOTO ATIVO (MESMA LÓGICA DO SEU DEBUG FUNCIONAL) =====
        try:
            driver_data = ir['DriverInfo']['Drivers'][car_idx]
            current_driver = driver_data.get('UserName', 'Unknown')
            current_user_id = driver_data.get('UserID', -1)
            team_name = driver_data.get('TeamName', 'N/A')
        except:
            current_driver = "Unknown"
            current_user_id = -1
            team_name = "N/A"

        # ===== TEMPOS =====
        lap_current_time = ir['LapCurrentLapTime']
        lap_last_time = ir['LapLastLapTime']
        session_state = ir['SessionState']

        # ===== DETECTA TROCA =====
        if current_user_id != last_driver_id:
            print("\n==================================================")
            print("🔄 TROCA DE PILOTO DETECTADA")
            print(f"Piloto atual: {current_driver}")
            print(f"UserID: {current_user_id}")
            print(f"Equipe: {team_name}")
            print("==================================================\n")
            last_driver_id = current_user_id

        # ===== DETECTA NOVA VOLTA (SEM LapCompleted) =====
        if lap_last_time > 0 and lap_last_time != last_lap_time_saved:

            time.sleep(0.8)  # consolidação leve

            timestamp_now = datetime.now().strftime("%H:%M:%S")

            print("\n--------------------------------------------------")
            print("🏁 VOLTA FINALIZADA")
            print(f"Piloto registrado: {current_driver}")
            print(f"Tempo da volta: {format_time(lap_last_time)}")
            print("--------------------------------------------------\n")

            # ===== SALVA NO CSV =====
            with open(CSV_FILE, mode='a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    timestamp_now,
                    current_driver,
                    current_user_id,
                    team_name,
                    round(lap_last_time, 3)
                ])

            last_lap_time_saved = lap_last_time

        # ===== PRINT EM TEMPO REAL =====
        os.system('cls' if os.name == 'nt' else 'clear')

        print("🔎 DEBUG TEMPO EM TEMPO REAL")
        print("------------------------------------------")
        print(f"Piloto ativo: {current_driver}")
        print(f"UserID: {current_user_id}")
        print(f"Equipe: {team_name}")
        print(f"Tempo volta atual: {format_time(lap_current_time)}")
        print(f"Última volta registrada: {format_time(lap_last_time)}")
        print(f"SessionState: {session_state}")
        print("------------------------------------------")

        time.sleep(0.2)

except KeyboardInterrupt:
    print("\n🛑 Debug encerrado.")
    print(f"📁 Arquivo salvo: {CSV_FILE}")

finally:
    ir.shutdown()
