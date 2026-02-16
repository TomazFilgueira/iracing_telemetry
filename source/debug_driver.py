import irsdk
import time
import os

ir = irsdk.IRSDK()

print("🔎 DEBUG DRIVER + LAP TIME (REAL TIME)")
print("Pressione CTRL+C para sair\n")

last_driver_id = None
last_lap_completed = -1

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

        # ===== PILOTO ATIVO =====
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
        lap_completed = ir['LapCompleted']
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

        # ===== DETECTA NOVA VOLTA FINALIZADA =====
        if lap_completed > last_lap_completed:
            print("\n--------------------------------------------------")
            print("🏁 VOLTA FINALIZADA")
            print(f"Nº Volta: {lap_completed}")
            print(f"Piloto registrado: {current_driver}")
            print(f"Tempo da volta: {format_time(lap_last_time)}")
            print("--------------------------------------------------\n")

            last_lap_completed = lap_completed

        # ===== PRINT EM TEMPO REAL =====
        os.system('cls' if os.name == 'nt' else 'clear')

        print("🔎 DEBUG TEMPO EM TEMPO REAL")
        print("------------------------------------------")
        print(f"Piloto ativo: {current_driver}")
        print(f"UserID: {current_user_id}")
        print(f"Equipe: {team_name}")
        print(f"LapCompleted: {lap_completed}")
        print(f"Tempo volta atual: {format_time(lap_current_time)}")
        print(f"Última volta: {format_time(lap_last_time)}")
        print(f"SessionState: {session_state}")
        print("------------------------------------------")

        time.sleep(0.2)

except KeyboardInterrupt:
    print("\n🛑 Debug encerrado.")

finally:
    ir.shutdown()
