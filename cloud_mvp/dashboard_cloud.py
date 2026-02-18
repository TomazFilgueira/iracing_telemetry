import streamlit as st
import pandas as pd
import altair as alt
import requests
import time
from pathlib import Path 

# ==============================
# CONFIGURAÇÃO DE DIRETÓRIOS (Conforme seu config.py)
# ==============================
BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "Data_Logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Arquivo padrão que o read_iracing.py gera
DEFAULT_CSV = LOG_DIR / "telemetry_data.csv"


# ==============================
# CONFIG
# ==============================

SERVER_URL = "http://127.0.0.1:8000/session/Daytona_Test"
REFRESH_RATE = 2

st.set_page_config(page_title="Strategy & Analysis Deck", layout="wide")

# Inicializa a fonte de dados se não existir
if 'data_source' not in st.session_state:
    st.session_state.data_source = "Local (CSV)"

# --- SIDEBAR DE CONFIGURAÇÃO ---
st.sidebar.title("⚙️ Configurações de Conexão")

st.session_state.data_source = st.sidebar.radio(
    "Selecione a fonte de dados:",
    ("Local (CSV)", "Cloud (Server API)")
)

# Configurações dependentes da fonte
if st.session_state.data_source == "Cloud (Server API)":
    server_ip = st.sidebar.text_input("Endereço do Servidor", "127.0.0.1")
    session_name = st.sidebar.text_input("ID da Sessão", "Daytona_Test")
    FETCH_URL = f"http://{server_ip}:8000/session/{session_name}"
    st.sidebar.success(f"Conectado à Nuvem")
else:
    # Garantimos que o caminho inicial seja o arquivo correto dentro de Data_Logs
    # Usamos .as_posix() para evitar problemas de barras invertidas no Windows
    default_path = (LOG_DIR / "telemetry_data.csv").as_posix()
    
    file_path = st.sidebar.text_input(
        "Caminho do CSV Local", 
        value=default_path
    )
    st.sidebar.info(f"Monitorando: {Path(file_path).name}")

REFRESH_RATE = st.sidebar.slider("Taxa de Atualização (seg)", 1, 10, 2)

st.markdown("""
<style>
.metric-align-top {
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    height: 100%;
}
</style>
""", unsafe_allow_html=True)

# ==============================
# FUNÇÃO DE CAPTURA HÍBRIDA
# ==============================

def fetch_data():
    if st.session_state.data_source == "Cloud (Server API)":
        try:
            response = requests.get(FETCH_URL, timeout=1)
            if response.status_code == 200:
                return pd.DataFrame(response.json())
            return pd.DataFrame()
        except:
            st.sidebar.error("Nuvem offline ☁️")
            return pd.DataFrame()
    else:
        # Busca no LOG_DIR definido
        p = Path(file_path)
        if p.exists():
            try:
                # O usecols ajuda a garantir que só pegamos o que o dashboard precisa
                return pd.read_csv(p)
            except Exception as e:
                st.sidebar.error(f"Erro ao ler CSV: {e}")
                return pd.DataFrame()
        else:
            st.sidebar.warning("Arquivo não encontrado em Data_Logs")
            return pd.DataFrame()
        

# ==============================
# FUNÇÕES AUXILIARES
# ==============================

def format_time(seconds):
    if seconds <= 0:
        return "00:00:000"
    minutes = int(seconds // 60)
    rem_seconds = seconds % 60
    return f"{minutes:02d}:{rem_seconds:06.3f}".replace('.', ':')


# ==============================
# LÓGICA PRINCIPAL
# ==============================

def render_metrics(df):

    if df.empty:
        st.warning("Aguardando dados do servidor...")
        return

    # ==============================
    # Ajuste para compatibilidade com seu dashboard
    # ==============================

    df = df.rename(columns={
        "driver": "Piloto",
        "lap": "Volta",
        "lap_time": "Tempo",
        "fuel": "Combustivel_Restante",
        "position": "Pos_Geral"
    })

    df["Sessao"] = "Race"
    df["Pos_Classe"] = df["Pos_Geral"]
    df["Media_3_Voltas"] = df["Tempo"].rolling(3).mean().fillna(df["Tempo"])
    df["Consumo_Volta"] = df["Combustivel_Restante"].shift(1) - df["Combustivel_Restante"]
    df["Consumo_Volta"] = df["Consumo_Volta"].fillna(0).abs()
    df["Media_Consumo_3_Voltas"] = df["Consumo_Volta"].rolling(3).mean().fillna(0)
    df["Voltas_Restantes_Estimadas"] = 20 - df["Volta"]

    # ==============================
    # Seleção piloto
    # ==============================

    piloto_selected = st.selectbox("Analisar dados de:", df["Piloto"].unique())
    session_selected = "Race"

    st.divider()

    # ==============================
    # DADOS DA EQUIPE
    # ==============================

    df_session = df.copy()
    laps_total_session = int(df_session["Volta"].max())

    last_row_session = df_session.iloc[-1]
    session_laps_est = last_row_session["Voltas_Restantes_Estimadas"]
    pos_g_session = int(last_row_session["Pos_Geral"])
    pos_c_session = int(last_row_session["Pos_Classe"])

    total_estimated = laps_total_session + session_laps_est

    # ==============================
    # FILTRA PILOTO
    # ==============================

    df_p = df[df["Piloto"] == piloto_selected].copy()
    df_valid = df_p.sort_values("Volta")

    laps_completed_pilot = len(df_valid)
    last_row = df_valid.iloc[-1]

    avg_cons_3v = last_row["Media_Consumo_3_Voltas"]
    fuel_remaining = last_row["Combustivel_Restante"]
    fuel_laps_est = fuel_remaining / avg_cons_3v if avg_cons_3v > 0 else 0

    # ==============================
    # BLOCO EQUIPE
    # ==============================

    st.subheader("🏎️ Dados Gerais da Equipe")

    col_e1, col_e2, col_e3 = st.columns(3)
    col_e1.metric("Voltas Totais", f"{laps_total_session} / {int(total_estimated)}")
    col_e2.metric("Posição Geral", f"P{pos_g_session}")
    col_e3.metric("Posição Classe", f"P{pos_c_session}")

    st.divider()

    # ==============================
    # BLOCO PILOTO
    # ==============================

    st.subheader(f"👤 Dados do Piloto: {piloto_selected}")

    col_p1, col_p2, col_p3 = st.columns(3)
    col_p1.metric("Voltas do Piloto", laps_completed_pilot)
    col_p2.metric("Stint Atual", laps_completed_pilot)
    col_p3.metric("Consumo Médio (3v)", f"{avg_cons_3v:.3f} L")

    col_p4, col_p5, col_p6 = st.columns(3)
    col_p4.metric("Última Volta", format_time(last_row["Tempo"]))
    col_p5.metric("Melhor Volta", format_time(df_valid["Tempo"].min()))
    col_p6.metric("Autonomia", f"{fuel_laps_est:.1f} v")

    st.divider()

    # ==============================
    # GRÁFICOS
    # ==============================

    st.subheader("📈 Análise de Ritmo e Consumo")

    g1, g2 = st.columns(2)

    base = alt.Chart(df_valid).encode(
        x=alt.X("Volta:O", title="Nº da Volta")
    )

    ritmo = base.mark_line(point=True).encode(
        y="Tempo:Q",
        tooltip=["Volta", "Tempo"]
    )

    consumo = base.mark_line(point=True).encode(
        y="Consumo_Volta:Q",
        tooltip=["Volta", "Consumo_Volta"]
    )

    g1.altair_chart(ritmo.properties(height=350), use_container_width=True)
    g2.altair_chart(consumo.properties(height=350), use_container_width=True)

    # ==============================
    # TABELA
    # ==============================

    st.subheader("📝 Histórico do Piloto")

    df_display = df_valid.copy()
    df_display["Tempo"] = df_display["Tempo"].apply(format_time)

    st.dataframe(
        df_display[["Volta", "Tempo", "Consumo_Volta", "Pos_Classe", "timestamp"]],
        use_container_width=True,
        hide_index=True
    )

# ==============================
# EXECUÇÃO
# ==============================

st.title("🏎️ Real-Time Strategy & Analysis (Cloud Mode)")

df_live = fetch_data()

render_metrics(df_live)

time.sleep(REFRESH_RATE)
st.rerun()
