from pathlib import Path

# --- CONFIGURAÇÃO DE DIRETÓRIOS ---
BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "Data_Logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# --- CONFIGURAÇÕES DE PERFORMANCE ---
REFRESH_RATE_ST = 2
WINDOW_SIZE = 3

