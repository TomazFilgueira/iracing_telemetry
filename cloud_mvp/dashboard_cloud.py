import streamlit as st
import pandas as pd
import altair as alt
import json
import os
import time
import requests
from pathlib import Path
from config import LOG_DIR, REFRESH_RATE_ST
from datetime import datetime 

# ==============================
# Configuração da Página
# ==============================
st.set_page_config(page_title="iRacing Cloud Strategy", layout="wide")
st.markdown("""
<style>
.metric-align-top { display: flex; flex-direction: column; justify-content: space-between; height: 100%; }
</style>
""", unsafe_allow_html=True)

# ==============================
# FUNÇÕES DE UTILIDADE E CONEXÃO
# ==============================

def format_time(seconds):
    if seconds <= 0: return "00:00:000"
    minutes = int(seconds // 60)
    rem_seconds = seconds % 60
    return f"{minutes:02d}:{rem_seconds:06.3f}".replace('.', ':')

def get_status_local():
    try:
        with open(LOG_DIR / "status.json", "r") as f:
            data = json.load(f)
            if time.time() - data.get("last_update", 0) > 10:
                return {"state": "offline", "driver": "---", "track": "---"}
            return data
    except:
        return {"state": "offline", "driver": "---", "track": "---"}

def fetch_cloud_data(url):
    try:
        response = requests.get(url, timeout=2)
        if response.status_code == 200:
            data = response.json()
            if not data: return pd.DataFrame()
            # Mapeamento para garantir que os nomes das colunas batam com sua render_metrics
            df = pd.DataFrame(data)
            df = df.rename(columns={
                "driver": "Piloto", "lap": "Volta", "lap_time": "Tempo",
                "fuel": "Combustivel_Restante", "position": "Pos_Geral",
                "timestamp": "Timestamp"
            })
            # Adiciona colunas calculadas básicas se não existirem
            df["Sessao"] = "Race"
            df["Pos_Classe"] = df["Pos_Geral"]
            df["Media_3_Voltas"] = df["Tempo"].rolling(3).mean().fillna(df["Tempo"])
            df["Consumo_Volta"] = df["Combustivel_Restante"].shift(1) - df["Combustivel_Restante"]
            df["Consumo_Volta"] = df["Consumo_Volta"].fillna(0).abs()
            df["Media_Consumo_3_Voltas"] = df["Consumo_Volta"].rolling(3).mean().fillna(0)
            df["Voltas_Restantes_Estimadas"] = 0 # Valor placeholder para Cloud
            return df
        return pd.DataFrame()
    except:
        return pd.DataFrame()
    
def normalize_telemetry(df):
    """Garante que o DataFrame tenha as colunas esperadas pelo render_metrics"""
    if df.empty:
        return df
    
    # Mapeamento de nomes antigos/cloud para o padrão do Dashboard
    mapping = {
        'driver': 'Piloto',
        'lap': 'Volta',
        'lap_time': 'Tempo',
        'fuel': 'Combustivel_Restante',
        'position': 'Pos_Geral',
        'timestamp': 'Timestamp'
    }
    
    # Renomeia apenas se a coluna de origem existir
    df = df.rename(columns={k: v for k, v in mapping.items() if k in df.columns})

    # Cria colunas obrigatórias caso não existam nos arquivos antigos
    if 'Sessao' not in df.columns:
        df['Sessao'] = 'Race'
    
    if 'Piloto' not in df.columns:
        df['Piloto'] = 'Desconhecido'
        
    if 'Pos_Classe' not in df.columns:
        df['Pos_Classe'] = df['Pos_Geral'] if 'Pos_Geral' in df.columns else 0

    # Garante que os cálculos de média existam para o gráfico não quebrar
    if 'Media_3_Voltas' not in df.columns and 'Tempo' in df.columns:
        df['Media_3_Voltas'] = df['Tempo'].rolling(3).mean().fillna(df['Tempo'])
    
    if 'Consumo_Volta' not in df.columns and 'Combustivel_Restante' in df.columns:
        df['Consumo_Volta'] = df['Combustivel_Restante'].shift(1) - df['Combustivel_Restante']
        df['Consumo_Volta'] = df['Consumo_Volta'].fillna(0).abs()
        df['Media_Consumo_3_Voltas'] = df['Consumo_Volta'].rolling(3).mean().fillna(0)

    return df

# ==============================
# INTERFACE DE STATUS
# ==============================

def render_traffic_light(status_data, is_cloud=False, df=None):
    if is_cloud:
        if df is not None and not df.empty:
            last_entry = df.iloc[-1]
            
            # --- LÓGICA DE HEARTBEAT ---
            # Verifica se o último dado tem mais de 10 segundos
            try:
                last_ts = datetime.strptime(last_entry['Timestamp'], "%H:%M:%S")
                now_ts = datetime.strptime(datetime.now().strftime("%H:%M:%S"), "%H:%M:%S")
                diff = (now_ts - last_ts).total_seconds()
            except:
                diff = 0 # Fallback caso o formato de hora falhe

            if diff > 10: # Se houver um buraco de 10s sem dados
                st.subheader("🔴 CLOUD DISCONNECTED")
                st.caption(f"⚠️ Sem sinal do client há {int(diff)}s. Verifique o fake_client.")
                return

            # Se os dados estiverem frescos, mostra o estado real
            state = last_entry.get("state", "cockpit") 
            driver = last_entry.get("Piloto", "---")
            
            colors = {"offline": "🔴", "connected": "🟡", "cockpit": "🟢"}
            labels = {"offline": "OFFLINE", "connected": "NO MENU", "cockpit": "READY (PISTA)"}
            
            col1, col2 = st.columns([1, 4])
            with col1:
                st.subheader(f"{colors.get(state, '⚪')} {labels.get(state, 'CLOUD')}")
            with col2:
                st.caption(f"👤 Piloto: {driver} | 🛰️ Sinal: Forte ({int(diff)}s delay)")
        else:
            st.subheader("⚪ AGUARDANDO CLOUD")
            st.caption("Conectado ao servidor, mas sem pacotes ativos...")
    else:
        # Lógica Local
        state = status_data.get("state", "offline")
        colors = {"offline": "🔴", "connected": "🟡", "cockpit": "🟢"}
        labels = {"offline": "DESCONECTADO", "connected": "SDK LINK (MENU)", "cockpit": "READY (COCKPIT)"}
        col1, col2 = st.columns([1, 4])
        with col1: st.subheader(f"{colors[state]} {labels[state]}")
        with col2:
            if state == "cockpit":
                st.caption(f"👤 Piloto: {status_data.get('driver', '---')} | 📍 Pista: {status_data.get('track', '---')}")
            else:
                st.caption("Aguardando entrada no cockpit local...")

# ==============================
# SUA LÓGICA DE RENDERIZAÇÃO (PRESERVADA)
# ==============================

def render_metrics(df):
    if df.empty:
        st.warning("Aguardando dados para análise...")
        return

    # --- SELEÇÃO DE PILOTO E SESSÃO ---
    col_driver, col_race = st.columns(2)
    with col_driver:
        piloto_selected = st.selectbox("Analisar dados de:", df['Piloto'].unique())
    with col_race:
        sessions = df['Sessao'].unique().tolist()
        default_index = sessions.index("Race") if "Race" in sessions else 0
        session_selected = st.selectbox("Sessão:", sessions, index=default_index)

    st.divider()

    # --- PROCESSAMENTO E FILTROS ---
    df_session = df[df['Sessao'] == session_selected].copy()
    
    # Lógica de Stint Global (Detecta troca de piloto ou reabastecimento)
    df_session['stint_change'] = (df_session['Piloto'] != df_session['Piloto'].shift()) | \
                                 (df_session['Combustivel_Restante'] > df_session['Combustivel_Restante'].shift() + 0.5)
    df_session['global_stint_id'] = df_session['stint_change'].cumsum()

    # Filtra dados do piloto selecionado
    df_p = df_session[df_session['Piloto'] == piloto_selected].copy()
    if df_p.empty:
        st.warning("Sem dados para este piloto nesta sessão.")
        return

    # Identificação do Stint Atual do Piloto
    last_global_id = df_p['global_stint_id'].iloc[-1]
    stints_p = df_p['global_stint_id'].unique()
    stint_number = list(stints_p).index(last_global_id) + 1
    
    df_this_stint = df_p[df_p['global_stint_id'] == last_global_id]
    stint_laps = len(df_this_stint[df_this_stint['Tempo'] > 0])

    # DataFrame validado para cálculos e gráficos
    df_valid = df_p[df_p['Tempo'] > 0].copy().sort_values("Volta")
    last_row = df_p.iloc[-1]

    # --- MÉTRICAS DE CONSUMO ---
    avg_cons_3v = last_row.get('Media_Consumo_3_Voltas', 0)
    fuel_remaining = last_row['Combustivel_Restante']
    fuel_laps_est = fuel_remaining / avg_cons_3v if avg_cons_3v > 0 else 0

    # --- BLOCO 1: EQUIPE ---
    st.subheader("🏎️ Dados Gerais da Equipe")
    laps_total_session = int(df_session[df_session['Tempo'] > 0]["Volta"].max()) if not df_session[df_session['Tempo'] > 0].empty else 0
    
    col_e1, col_e2, col_e3 = st.columns(3)
    col_e1.metric("Voltas Totais (Sessão)", f"{laps_total_session}")
    col_e2.metric("Posição Geral", f"P{int(last_row.get('Pos_Geral', 0))}")
    col_e3.metric("Posição Classe", f"P{int(last_row.get('Pos_Classe', 0))}")
    st.divider()

    # --- BLOCO 2: PILOTO ---
    st.subheader(f"👤 Dados do Piloto: {piloto_selected}")
    col_p1, col_p2, col_p3 = st.columns(3)
    col_p1.metric("Total Voltas Piloto", len(df_valid))
    col_p2.metric(f"Stint {stint_number}", f"{stint_laps} v")
    col_p3.metric("Consumo Médio (3v)", f"{avg_cons_3v:.3f} L")

    col_p4, col_p5, col_p6 = st.columns(3)
    last_v_time = df_valid.iloc[-1]['Tempo'] if not df_valid.empty else 0
    best_lap = df_valid['Tempo'].min() if not df_valid.empty else 0
    col_p4.metric("Última Volta", format_time(last_v_time))
    col_p5.metric("Melhor Volta", format_time(best_lap))
    col_p6.metric("Autonomia Estimada", f"{fuel_laps_est:.1f} v")
    st.divider()

    # --- GRÁFICOS (REINTEGRADOS) ---
    st.subheader("📈 Análise de Ritmo e Consumo")
    g1, g2 = st.columns(2)

    if not df_valid.empty:
        # Gráfico de Desempenho (Tempo de Volta)
        y_min, y_max = df_valid['Tempo'].min() - 0.5, df_valid['Tempo'].max() + 0.5
        base = alt.Chart(df_valid).encode(x=alt.X('Volta:O', title='Nº da Volta'))
        
        line = base.mark_line(point=True, opacity=0.4).encode(
            y=alt.Y('Tempo:Q', scale=alt.Scale(domain=[y_min, y_max]), title='Tempo (s)'),
            tooltip=['Volta', 'Tempo']
        )
        avg_line = base.mark_line(color='#FFD700', strokeWidth=3).encode(y='Media_3_Voltas:Q')
        g1.altair_chart(alt.layer(line, avg_line).properties(title="Consistência de Ritmo", height=350), use_container_width=True)

        # Gráfico de Consumo de Combustível
        base_fuel = alt.Chart(df_valid).encode(x=alt.X('Volta:O', title='Nº da Volta'))
        f_line = base_fuel.mark_line(point=True, color='#FF4B4B').encode(
            y=alt.Y('Consumo_Volta:Q', title='Litros por Volta'),
            tooltip=['Volta', 'Consumo_Volta']
        )
        f_avg = base_fuel.mark_line(color='#FFD700', strokeWidth=3).encode(y='Media_Consumo_3_Voltas:Q')
        g2.altair_chart(alt.layer(f_line, f_avg).properties(title="Histórico de Consumo", height=350), use_container_width=True)

    # --- TABELA ---
    st.subheader("📝 Histórico Detalhado")
    df_display = df_valid.copy().sort_values("Volta", ascending=False)
    df_display['Tempo'] = df_display['Tempo'].apply(format_time)
    st.dataframe(
        df_display[['Volta', 'Tempo', 'Consumo_Volta', 'Pos_Classe', 'Timestamp']], 
        use_container_width=True, 
        hide_index=True
    )

# ==============================
# EXECUÇÃO PRINCIPAL
# ==============================


# 1. SIDEBAR - Definimos tudo primeiro
st.sidebar.title("⚙️ Configurações")
app_mode = st.sidebar.radio("Operação", ["📡 Live Telemetry", "📂 Post-Race Analysis"])

# Inicializamos variáveis de controle para evitar o NameError
df_live = pd.DataFrame()
is_cloud_active = False

if app_mode == "📡 Live Telemetry":
    conn_mode = st.sidebar.selectbox("Fonte de Dados", ["Local (Pasta/CSV)", "Cloud (API Server)"])
    
    if conn_mode == "Cloud (API Server)":
        server_ip = st.sidebar.text_input("IP do Servidor", "127.0.0.1")
        session_id = st.sidebar.text_input("ID Sessão", "Daytona_Test")
        CLOUD_URL = f"http://{server_ip}:8000/session/{session_id}"
        
        df_live = fetch_cloud_data(CLOUD_URL)
        is_cloud_active = True
        render_traffic_light({}, is_cloud=True, df=df_live)
    else:
        # Busca automática do stint mais recente (Local)
        if LOG_DIR.exists():
            files = [f for f in os.listdir(LOG_DIR) if f.startswith("stint_")]
            if files:
                latest = LOG_DIR / max(files, key=lambda x: os.path.getctime(LOG_DIR / x))
                try:
                    df_live = pd.read_csv(latest)
                except:
                    st.sidebar.warning("🔄 Arquivo travado pelo iRacing...")
        is_cloud_active = False
        status_local = get_status_local()
        render_traffic_light(status_local, is_cloud=False)

else: # 📂 Post-Race Analysis
    st.sidebar.subheader("Análise de Arquivo")
    uploaded = st.sidebar.file_uploader("Carregar CSV de Telemetria", type="csv")
    if uploaded:
        df_live = pd.read_csv(uploaded)
    is_cloud_active = False

# 2. CORPO DO DASHBOARD - Agora as variáveis já existem
st.title(f"🏎️ {app_mode}")

if is_cloud_active and app_mode == "📡 Live Telemetry":
    st.subheader("☁️ MODO CLOUD ATIVO")
    st.caption("Recebendo telemetria via API remota.")
elif app_mode == "📂 Post-Race Analysis":
    st.subheader("📂 Análise Estática")
    st.caption("Processando dados de arquivo carregado.")
else:
    # Mostra o semáforo apenas se estiver no modo Live Local
    status = get_status_local()
    render_traffic_light(status)

st.divider()

# 3. RENDERIZAÇÃO DOS DADOS
if not df_live.empty:
    # Chamamos a normalização antes de renderizar (ajustado conforme conversamos)
    df_normalized = normalize_telemetry(df_live) 
    render_metrics(df_normalized)
else:
    st.info("Aguardando entrada de dados para iniciar a análise...")

# 4. AUTO-REFRESH (Apenas no modo Live)
if app_mode == "📡 Live Telemetry":
    time.sleep(REFRESH_RATE_ST)
    st.rerun()