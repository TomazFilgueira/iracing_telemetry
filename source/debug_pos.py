import irsdk
import time

# Inicializa o SDK
ir = irsdk.IRSDK()

def get_color_pos(pos, last_pos):
    """Retorna uma seta visual se a posição mudou."""
    if last_pos == -1 or pos == last_pos:
        return ""
    return " ⬆️" if pos < last_pos else " ⬇️"

print("🔍 DEBUG DE POSIÇÃO EM TEMPO REAL (10Hz)")
print("Pressione Ctrl+C para encerrar.\n")

was_connected = False
last_g = -1
last_c = -1

try:
    while True:
        # Polling de conexão
        if not ir.is_connected:
            ir.startup()
            if was_connected:
                print("🔴 [OFFLINE] Conexão com o simulador perdida.")
                was_connected = False
            time.sleep(1)
            continue

        if not was_connected:
            print("🟢 [ONLINE] Conectado ao iRacing. Aguardando cockpit...")
            was_connected = True

        my_car_idx = ir['DriverInfo']['DriverCarIdx']

        if my_car_idx >= 0:
            # Captura de alta frequência
            state = ir['SessionState']
            session_time = ir['SessionTime']
            pos_geral = ir['PlayerCarPosition']
            pos_classe = ir['PlayerCarClassPosition']

            # Formatação de saída para o CMD
            move_g = get_color_pos(pos_geral, last_g)
            move_c = get_color_pos(pos_classe, last_c)

            # Só imprime se houver dados válidos (evita lixo de carregamento)
            if pos_geral > 0:
                output = f"[{session_time:8.2f}s]  "
                output += f"GERAL: P{pos_geral:<2}{move_g:<3} | "
                output += f"CLASSE: P{pos_classe:<2}{move_c:<3}"
                output += f" | Estado: {state}"
                print(output)

                last_g, last_c = pos_geral, pos_classe
        
        # Frequência de 10Hz para identificar o lag do buffer
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\n🛑 Debug finalizado pelo usuário.")
finally:
    ir.shutdown()