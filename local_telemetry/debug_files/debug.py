import irsdk
import time

def log_event(message):
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")

ir = irsdk.IRSDK()

print("🔍 Monitoramento de Conexão Ativo (Inicie no Menu!)")

was_connected = False
in_cockpit = False

try:
    while True:
        # Tenta inicializar a conexão se ela ainda não estiver ativa
        if not ir.is_connected:
            ir.startup()
        
        if ir.is_connected:
            if not was_connected:
                log_event("✅ SDK CONECTADO: Link estabelecido.")
                was_connected = True

            # Verifica se o piloto já "sentou" no carro
            my_car_idx = ir['DriverInfo']['DriverCarIdx']

            if my_car_idx >= 0:
                if not in_cockpit:
                    try:
                        name = ir['DriverInfo']['Drivers'][my_car_idx]['UserName']
                        log_event(f"🏎️ PILOTO NO COCKPIT: {name}")
                        in_cockpit = True
                    except:
                        pass
            else:
                if in_cockpit:
                    log_event("🚪 SAÍDA DO CARRO: Voltando ao menu/replay.")
                    in_cockpit = False
        else:
            if was_connected:
                log_event("❌ CONEXÃO PERDIDA: Simulador fechado.")
                was_connected = False
                in_cockpit = False
        
        time.sleep(1)
except KeyboardInterrupt:
    print("🛑 Encerrado.")
finally:
    ir.shutdown()