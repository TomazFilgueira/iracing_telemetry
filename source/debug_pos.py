import irsdk
import time
import numpy as np

ir = irsdk.IRSDK()

print("🔬 DEBUG COMPLETO DE POSIÇÃO - iRacing")
print("Comparando 3 métodos de posição\n")

last_print_time = 0

try:
    while True:
        if not ir.is_connected:
            print("⏳ Conectando ao iRacing...")
            ir.startup()
            time.sleep(1)
            continue

        # ==============================
        # Variáveis básicas
        # ==============================
        session_state = ir['SessionState']
        session_time = ir['SessionTime']
        lap_completed = ir['LapCompleted']
        lap_dist = ir['LapDistPct']

        player_idx = ir['PlayerCarIdx']

        # ==============================
        # MÉTODO 1 — PlayerCarPosition
        # ==============================
        pos_player = ir['PlayerCarPosition']

        # ==============================
        # MÉTODO 2 — CarIdxPosition (RECOMENDADO)
        # ==============================
        pos_vector = ir['CarIdxPosition']
        pos_vector_player = pos_vector[player_idx]

        # ==============================
        # MÉTODO 3 — Ranking por distância real
        # ==============================
        lap_dist_vector = np.array(ir['CarIdxLapDistPct'])
        lap_completed_vector = np.array(ir['CarIdxLapCompleted'])

        # Combina volta + distância
        race_progress = lap_completed_vector + lap_dist_vector

        # Remove carros inválidos
        valid_mask = lap_dist_vector >= 0
        race_progress_valid = race_progress[valid_mask]
        idx_valid = np.where(valid_mask)[0]

        # Ranking
        ranking = idx_valid[np.argsort(-race_progress_valid)]

        if player_idx in ranking:
            pos_calc = np.where(ranking == player_idx)[0][0] + 1
        else:
            pos_calc = -1

        # ==============================
        # Verificação de posição válida
        # ==============================
        position_valid = (
            session_state == 4 and
            pos_vector_player > 0
        )

        # ==============================
        # Print a cada 0.5s
        # ==============================
        if time.time() - last_print_time > 0.5:

            print("=" * 70)
            print(f"⏱️  Tempo: {session_time:8.2f}s")
            print(f"🏁 Estado Sessão: {session_state} | Volta: {lap_completed} | Dist: {lap_dist*100:.1f}%")
            print("-" * 70)

            print(f"📊 PlayerCarPosition      : P{pos_player}")
            print(f"📊 CarIdxPosition         : P{pos_vector_player}")
            print(f"📊 Calculado (distância)  : P{pos_calc}")

            if pos_player == 0:
                print("⚠️ PlayerCarPosition ainda inválido")

            if position_valid:
                print("✅ Posição oficialmente válida (SessionState == 4)")
            else:
                print("⏳ Aguardando sessão entrar em RACING ou posição atualizar")

            last_print_time = time.time()

        time.sleep(0.05)

except KeyboardInterrupt:
    print("\n🛑 Debug encerrado.")

finally:
    ir.shutdown()
