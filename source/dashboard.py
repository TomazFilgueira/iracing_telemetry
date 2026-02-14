import streamlit as st
import pandas as pd
import altair as alt
import json
import os
import time
from config import LOG_DIR, REFRESH_RATE_ST

# Configuração da Página
st.set_page_config(page_title="Strategy & Analysis Deck", layout="wide")

# --- FUNÇÕES DE UTILIDADE ---

def get_status():
    """Lê o estado do Traffic Light do arquivo JSON gerado pelo coletor."""
    try:
        with open(LOG_DIR / "status.json", "r") as f:
            return json.load(f)
    except:
        return {"state": "offline", "driver": "---", "track": "---"}

def format_time(seconds):
    """Converte segundos brutos para o formato mm:ss:ms."""
    if seconds <= 0: return "00:00:000"
    minutes = int(seconds // 60)
    rem_seconds = seconds % 60
    return f"{minutes:02d}:{rem_seconds:06.3f}".replace('.', ':')

def render_traffic_light(status):
    """Renderiza o indicador visual de conexão no topo."""
    state = status.get("state", "offline")
    colors = {"offline": "🔴", "connected": "🟡", "cockpit": "🟢"}
    labels = {"offline": "DESCONECTADO", "connected": "SDK LINK (MENU)", "cockpit": "READY (COCKPIT)"}
    
    col1, col2 = st.columns([1, 4])
    with col1:
        st.subheader(f"{colors[state]} {labels[state]}")
    with col2:
        if state == "cockpit":
            st.caption(f"👤 Piloto: {status['driver']} | 📍 Pista: {status['track']}")
        else:
            st.caption("Aguardando entrada no cockpit para iniciar a telemetria...")

# --- LÓGICA DE MÉTRICAS E GRÁFICOS ---

def render_metrics(df):
    """Renderiza toda a análise técnica quando há dados disponíveis."""
    if df.empty:
        st.warning("Aguardando gravação da primeira volta...")
        return

    # Seleção de Piloto (Importante para stints com Rodrigo ou Morsinaldo)
    piloto_selected = st.selectbox("Analisar dados de:", df['Piloto'].unique())
    df_p = df[df['Piloto'] == piloto_selected].copy()
    last_row = df_p.iloc[-1]

    # --- SELETOR DE POSIÇÃO COM CORES DINÂMICAS ---
    pos_mode = st.radio("Filtro de Posição:", ["Classe (Categoria)", "Geral (Overall)"], horizontal=True)
    
    if pos_mode == "Classe (Categoria)":
        pos_val = int(last_row.get('Pos_Classe', 0))
        st.info(f"🔹 **MODO CLASSE ATIVO** | Posição Atual: P{pos_val}")
    else:
        pos_val = int(last_row.get('Pos_Geral', 0))
        st.error(f"🔴 **MODO GERAL ATIVO** | Posição Atual: P{pos_val}")

    st.divider()

    # --- KPIs DE PERFORMANCE ---
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Última Volta", format_time(last_row['Tempo']))
    k2.metric("Melhor Volta", format_time(df_p['Tempo'].min()))
    k3.metric("Consumo Médio", f"{df_p['Consumo_Volta'].mean():.3f} L")
    k4.metric("No Tanque", f"{last_row['Combustivel_Restante']:.2f} L")

    st.divider()

    # --- GRÁFICOS TÉCNICOS ---
    st.subheader("📈 Análise de Ritmo e Consumo")
    g1, g2 = st.columns(2)

    # Gráfico 1: Ritmo (Volta vs Média Móvel)
    y_min = df_p['Tempo'].min() - 0.5
    y_max = df_p['Tempo'].max() + 0.5
    base = alt.Chart(df_p).encode(x=alt.X('Volta:O', title='Nº da Volta'))
    
    line = base.mark_line(point=True, opacity=0.4).encode(
        y=alt.Y('Tempo:Q', title='Tempo (s)', scale=alt.Scale(domain=[y_min, y_max])),
        tooltip=['Volta', 'Tempo']
    )
    avg = base.mark_line(color='#FFD700', strokeWidth=3).encode(y='Media_3_Voltas:Q')
    
    g1.altair_chart(alt.layer(line, avg).properties(height=350, title="Consistência de Ritmo"), width='stretch')

    # Gráfico 2: Consumo de Combustível
    chart_fuel = alt.Chart(df_p).mark_bar(color='#FF4B4B').encode(
        x='Volta:O',
        y=alt.Y('Consumo_Volta:Q', title='Consumo (Litros)'),
        tooltip=['Volta', 'Consumo_Volta']
    ).properties(height=350, title="Consumo por Volta")
    
    g2.altair_chart(chart_fuel, width='stretch')

    # --- TABELA HISTÓRICA ---
    st.subheader("📝 Histórico da Sessão")
    df_display = df_p.copy()
    df_display['Tempo'] = df_display['Tempo'].apply(format_time)
    st.dataframe(
        df_display[['Volta', 'Tempo', 'Consumo_Volta', 'Pos_Classe', 'Timestamp']], 
        use_container_width=True, 
        hide_index=True
    )

# --- EXECUÇÃO PRINCIPAL ---

st.title("🏎️ Real-Time Strategy & Analysis")

# Traffic Light sempre visível no topo
status = get_status()
render_traffic_light(status)
st.divider()

# Barra Lateral
st.sidebar.header("⚙️ Configurações")
mode = st.sidebar.radio("Modo de Operação", ["📡 Live Telemetry", "📂 Post-Race Analysis"])

if mode == "📡 Live Telemetry":
    # Localiza o arquivo de stint mais recente
    files = [f for f in os.listdir(LOG_DIR) if f.startswith("stint_")]
    if files:
        latest_file = LOG_DIR / max(files, key=lambda x: os.path.getctime(LOG_DIR / x))
        try:
            df_live = pd.read_csv(latest_file)
            render_metrics(df_live)
        except Exception:
            st.info("🔄 Sincronizando dados com o iRacing...")
    else:
        st.warning("Aguardando criação do arquivo de telemetria...")
    
    # Loop de atualização automática
    time.sleep(REFRESH_RATE_ST)
    st.rerun()

else:
    # Modo de Análise Pós-Corrida
    uploaded = st.sidebar.file_uploader("Carregar Arquivo de Telemetria (CSV)", type="csv")
    if uploaded:
        render_metrics(pd.read_csv(uploaded))