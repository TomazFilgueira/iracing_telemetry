from pathlib import Path

# Detecta a pasta onde este config.py está (Raiz do Projeto)
BASE_DIR = Path(__file__).resolve().parent

# Define a pasta de Logs dentro do projeto
LOG_DIR = BASE_DIR / "Data_Logs"

# Garante que a pasta exista (Cria se não houver)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Configurações globais
REFRESH_RATE_ST = 2  # Segundos para atualização do Streamlit
WINDOW_SIZE = 3      # Quantidade de voltas para a média móvel