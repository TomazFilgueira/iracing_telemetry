import irsdk
import time
import numpy as np
import csv
from datetime import datetime

ir = irsdk.IRSDK()

print("🔬 DEBUG POSIÇÃO + LOGGER CSV (USANDO CALC)")
print("Salvando posição consolidada ao fechar volta\n")

# ==========================
# CSV
# ==========================

timestamp_file = datetime.now().strftime("%Y%m%d_%H%M%S")
CSV_FILE = f"debug_pos_laps_{timestamp_file}.csv"

with open(CSV_FILE, mode="w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "Timestamp",
        "LapNumber",
        "LapTime",
        "Pos_Player",
        "Pos_CarIdx",
        "Pos_Calc"
    ])

print(f"📁 Salvando em: {CSV_FILE}\n")

# ==========================
# Controle
# ==========================

last_lap_completed = -1
last_lap_time = -1.0

def format_time(seconds):
    if seconds <= 0:
        return "00:00.000"
    minutes = int(seconds // 60)
    rem = seconds % 60
    return f"{minutes:02d}:{rem:06.3f}"

try:
    while True:

        if not ir.is_connected:
            print("⏳ Conectando ao iRacing...")
            ir.startup()
            time.sleep(1)
            continue

        session_state = ir['SessionState']
        session_time = ir['SessionTime']
        lap_completed = ir['LapCompleted']
        lap_last_time = ir['LapLastLapTime']

        player_idx = ir['PlayerCarIdx']

        # ==============================
        # POSIÇÕES
        # ==============================

        pos_player = ir['PlayerCarPosition']
        pos_vector = ir['CarIdxPosition']
        pos_caridx = pos_vector[player_idx]

        # ===== CALC =====
        lap_dist_vector = np.array(ir['CarIdxLapDistPct'])
        lap_completed_vector = np.array(ir['CarIdxLapCompleted'])

        race_progress = lap_completed_vector + lap_dist_vector

        valid_mask = lap_dist_vector >= 0
        race_progress_valid = race_progress[valid_mask]
        idx_valid = np.where(valid_mask)[0]

        ranking = idx_valid[np.argsort(-race_progress_valid)]

        if player_idx in ranking:
            pos_calc = np.where(ranking == player_idx)[0][0] + 1
        else:
            pos_calc = -1

        # ==============================
        # DETECTA FECHAMENTO DE VOLTA
        # ==============================

        if (lap_completed > last_lap_completed and lap_last_time > 0 and lap_last_time != last_lap_time):

        # Espera consolidação
            time.sleep(1.5)

            # 🔁 RECALCULA POSIÇÕES APÓS CONSOLIDAÇÃO
            pos_player = ir['PlayerCarPosition']
            pos_vector = ir['CarIdxPosition']
            pos_caridx = pos_vector[player_idx]

            lap_dist_vector = np.array(ir['CarIdxLapDistPct'])
            lap_completed_vector = np.array(ir['CarIdxLapCompleted'])

            race_progress = lap_completed_vector + lap_dist_vector

            valid_mask = lap_dist_vector >= 0
            race_progress_valid = race_progress[valid_mask]
            idx_valid = np.where(valid_mask)[0]

            ranking = idx_valid[np.argsort(-race_progress_valid)]

            if player_idx in ranking:
                pos_calc = np.where(ranking == player_idx)[0][0] + 1
            else:
                pos_calc = -1

            timestamp_now = datetime.now().strftime("%H:%M:%S")

            print("\n" + "="*70)
            print("🏁 VOLTA FINALIZADA (CONSOLIDADA)")
            print(f"Nº Volta: {lap_completed}")
            print(f"Tempo: {format_time(lap_last_time)}")
            print(f"Posições → Player:{pos_player} | CarIdx:{pos_caridx} | Calc:{pos_calc}")
            print("="*70 + "\n")

            with open(CSV_FILE, mode="a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    timestamp_now,
                    lap_completed,
                    round(lap_last_time, 3),
                    pos_player,
                    pos_caridx,
                    pos_calc
                ])

            last_lap_completed = lap_completed
            last_lap_time = lap_last_time


        # ==============================
        # PRINT CONTÍNUO
        # ==============================

        print("-"*70)
        print(f"⏱️  Tempo Sessão: {session_time:8.2f}s")
        print(f"🏁 Estado: {session_state} | Volta: {lap_completed}")
        print(f"Posições atuais → Player:{pos_player} | CarIdx:{pos_caridx} | Calc:{pos_calc}")
        print("-"*70)

        time.sleep(1)

except KeyboardInterrupt:
    print("\n🛑 Debug encerrado.")
    print(f"📁 Arquivo salvo: {CSV_FILE}")

finally:
    ir.shutdown()
