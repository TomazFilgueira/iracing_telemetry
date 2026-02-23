import requests
import time
import random
from datetime import datetime

SERVER_URL = "https://iracingcloud.loca.lt/telemetry"
SESSION_ID = "Daytona_Test"

driver_name = "Rodrigo"
user_id = 739024

lap = 0
fuel = 20.0

print("🚀 Simulador de Telemetria iniciado...")

while True:
    lap += 1
    lap_time = round(random.uniform(16.8, 18.2), 3)
    fuel -= round(random.uniform(0.1, 0.2), 3)

    data = {
        "session_id": SESSION_ID,
        "driver": driver_name,
        "user_id": user_id,
        "lap": lap,
        "lap_time": lap_time,
        "fuel": round(fuel, 3),
        "position": random.randint(1, 5),
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "state": "cockpit" 
    }   

    # --- O SEGREDO ESTÁ AQUI: O CRACHÁ PARA PULAR A TELA DO LOCALTUNNEL ---
    headers = {
        "Bypass-Tunnel-Reminder": "true",
        "User-Agent": "iRacingTelemetryClient/1.0"
    }

    try:
        # Passando os headers na requisição
        response = requests.post(SERVER_URL, json=data, headers=headers)
        print(f"🏁 Lap {lap} enviada | {lap_time}s | Fuel: {fuel:.2f} | Status: {data['state']} | HTTP: {response.status_code}")
    except Exception as e:
        print("❌ Erro ao enviar:", e)

    time.sleep(2)