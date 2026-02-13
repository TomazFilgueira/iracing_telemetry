from pathlib import Path

# --- CONFIGURAÇÃO DE DIRETÓRIOS ---
BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "Data_Logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# --- CONFIGURAÇÕES DE PERFORMANCE ---
REFRESH_RATE_ST = 2
WINDOW_SIZE = 3

# --- ACESSO REMOTO (NGROK) ---
# Seus amigos devem colar o token obtido em dashboard.ngrok.com aqui
NGROK_AUTH_TOKEN = 39XIFEp1nsVEAFvMxe68Diaune6_6PqdwZPSFwFwdZDKZMteX