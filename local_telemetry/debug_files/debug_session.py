import irsdk
import time

ir = irsdk.IRSDK()

def log_session(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

print("🔍 MONITOR DE TRANSIÇÃO DE SESSÃO (10Hz)")
print("Aguardando conexão com o iRacing...")

last_num = -1
last_state = -1
last_type = ""

try:
    while True:
        if not ir.is_connected:
            ir.startup()
            time.sleep(1)
            continue

        # Captura de variáveis de infraestrutura
        session_num = ir['SessionNum']
        session_state = ir['SessionState']
        
        # O SessionType vem do dicionário SessionInfo (YAML)
        try:
            session_type = ir['SessionInfo']['Sessions'][session_num]['SessionType']
        except:
            session_type = "Unknown"

        # Só printa se algo mudar para não inundar o terminal
        if session_num != last_num or session_state != last_state:
            log_session(f"SESSÃO: {session_num} ({session_type}) | ESTADO: {session_state}")
            
            # Se a sessão mudou, verifica o combustível disponível imediatamente
            if session_num != last_num:
                fuel = ir['FuelLevel']
                log_session(f"⛽ Combustível detectado na troca: {fuel:.2f}L")
                log_session(f"🏁 Voltas completadas (reset): {ir['LapCompleted']}")
            
            last_num = session_num
            last_state = session_state
            last_type = session_type

        time.sleep(0.1) # Alta frequência para pegar o exato momento da transição

except KeyboardInterrupt:
    print("\n🛑 Debug encerrado.")
finally:
    ir.shutdown()