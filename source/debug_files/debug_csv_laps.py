import irsdk
import time

ir = irsdk.IRSDK()
last_lap = -1

print("🏁 Monitor de Voltas de Equipe Ativo...")
print("Buscando dados do carro da equipe no SDK...\n")

try:
    while True:
        if not ir.is_connected:
            ir.startup()
            time.sleep(1)
            continue

        # Pega o ID do carro que você está 'seguindo' (seu colega)
        car_idx = ir['DriverInfo']['DriverCarIdx']
        
        if car_idx >= 0:
            # CarIdxLap: Array que contém a volta de TODOS os carros da pista
            # Usamos o car_idx para pegar especificamente a do seu carro
            current_lap = ir['CarIdxLap'][car_idx]

            if current_lap != last_lap:
                # O iRacing costuma reportar a volta atual, então subtraímos 1 
                # para saber as voltas completadas, se preferir o padrão do dash.
                print(f"[{time.strftime('%H:%M:%S')}] 🏎️ Carro em Pista | Volta Atual: {current_lap}")
                last_lap = current_lap

        time.sleep(0.1)

except KeyboardInterrupt:
    print("\n🛑 Monitor encerrado.")
finally:
    ir.shutdown()