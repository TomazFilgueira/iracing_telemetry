import streamlit as st
import pandas as pd
import altair as alt
import json
import os
import time
from config import LOG_DIR, REFRESH_RATE_ST

st.set_page_config(page_title="Strategy & Analysis Deck", layout="wide")

def get_status():
    """Lê o estado do Traffic Light."""
    try:
        with open(LOG_DIR / "status.json", "r") as f:
            return json.load(f)
    except:
        return {"state": "offline", "driver": "---", "track": "---"}

def render_traffic_light(status):
    """Renderiza o indicador visual de conexão."""
    state = status.get("state", "offline")
    
    # Mapeamento de Cores e Mensagens
    colors = {"offline": "🔴", "connected": "🟡", "cockpit": "🟢"}
    labels = {"offline": "DESCONECTADO", "connected": "SDK LINK (MENU)", "cockpit": "READY (COCKPIT)"}
    
    col1, col2 = st.columns([1, 4])
    with col1:
        st.subheader(f"{colors[state]} {labels[state]}")
    with col2:
        if state == "cockpit":
            st.caption(f"👤 {status['driver']} | 📍 {status['track']}")
        else:
            st.caption("Aguardando entrada no cockpit para iniciar gravação...")

# (Funções format_time e get_latest_file permanecem iguais)

def render_metrics(df):
    # (Lógica de renderização de KPIs e Gráficos permanece igual)
    pass

# --- EXECUÇÃO PRINCIPAL ---
st.title("🏎️ Real-Time Strategy & Analysis")

status = get_status()
render_traffic_light(status)
st.divider()

mode = st.sidebar.radio("Modo", ["📡 Live Telemetry", "📂 Post-Race Analysis"])

if mode == "📡 Live Telemetry":
    live_file = max([LOG_DIR / f for f in os.listdir(LOG_DIR) if f.startswith("stint_")], 
                    key=os.path.getctime, default=None)
    
    if live_file and status['state'] == "cockpit":
        df_live = pd.read_csv(live_file)
        if not df_live.empty:
            render_metrics(df_live)
    
    time.sleep(REFRESH_RATE_ST)
    st.rerun()
else:
    # Modo de Análise Pós-Corrida
    uploaded = st.sidebar.file_uploader("Upload CSV", type="csv")
    if uploaded:
        render_metrics(pd.read_csv(uploaded))