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
        if not LOG_DIR.exists(): return {"state": "offline", "driver": "---", "track": "---"}
        with open(LOG_DIR / "status.json", "r") as f:
            data = json.load(f)
            if time.time() - data.get("last_update", 0) > 10:
                return {"state": "offline", "driver": "---", "track": "---"}
            return data
    except:
        return {"state": "offline", "driver": "---", "track": "---"}

def fetch_cloud_data(url):
    # Header obrigatório para pular o aviso do ngrok
    headers = {'ngrok-skip-browser-warning': 'true'}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if not data: return pd.DataFrame()
            
            df = pd.DataFrame(data)
            
            # Normalização de Colunas
            mapping = {
                "driver": "Piloto", "lap": "Volta", "lap_time": "Tempo",
                "fuel": "Combustivel_Restante", "position": "Pos_Geral",
                "timestamp": "Timestamp", "state": "state"
            }
            df = df.rename(columns={k: v for k, v in mapping.items() if k in df.columns})

            if "Sessao" not in df.columns: df["Sessao"] = "Race"
            
            
            return df
        return pd.DataFrame()
    except Exception as e:
        # Silencia erros de conexão na interface principal para não poluir
        return pd.DataFrame()
    
def normalize_telemetry(df):
    if df.empty: return df
    mapping = {
        'driver': 'Piloto', 'lap': 'Volta', 'lap_time': 'Tempo',
        'fuel': 'Combustivel_Restante', 'position': 'Pos_Geral', 'timestamp': 'Timestamp'
    }
    df = df.rename(columns={k: v for k, v in mapping.items() if k in df.columns})
    if 'Sessao' not in df.columns: df['Sessao'] = 'Race'
    if 'Piloto' not in df.columns: df['Piloto'] = 'Desconhecido'
    if 'Pos_Classe' not in df.columns: df['Pos_Classe'] = df['Pos_Geral'] if 'Pos_Geral' in df.columns else 0

    if 'Media_3_Voltas' not in df.columns and 'Tempo' in df.columns:
        df['Media_3_Voltas'] = df['Tempo'].rolling(3).mean().fillna(df['Tempo'])
    
    if 'Consumo_Volta' not in df.columns and 'Combustivel_Restante' in df.columns:
        df['Consumo_Volta'] = (df['Combustivel_Restante'].shift(1) - df['Combustivel_Restante']).fillna(0).abs()
        df['Media_Consumo_3_Voltas'] = df['Consumo_Volta'].rolling(3).mean().fillna(0)
    return df

# ==============================
# INTERFACE DE STATUS
# ==============================

def render_traffic_light(status_data, is_cloud=False, df=None):
    if is_cloud:
        if df is not None and not df.empty:
            st.subheader("📡 Status da Equipe (Cloud)")
            
            # 1. Agrupa pelo Piloto e pega apenas o último heartbeat de cada um
            df_last_status = df.groupby('Piloto').tail(1)
            
            # 2. Cria colunas dinâmicas (uma para você, uma pro Rodrigo, etc.)
            cols = st.columns(len(df_last_status))
            
            colors = {"offline": "🔴", "connected": "🟡", "cockpit": "🟢"}
            labels = {"offline": "OFFLINE", "connected": "BOX / MENU", "cockpit": "NO CARRO"}

            # 3. Renderiza o status individual
            for idx, row in enumerate(df_last_status.itertuples()):
                state = getattr(row, "state", "offline")
                driver = getattr(row, "Piloto", "Unknown")
                timestamp_str = getattr(row, "Timestamp", "00:00:00")
                
                # Cálculo de latência para detectar se a internet do piloto caiu
                try:
                    last_ts = datetime.strptime(timestamp_str, "%H:%M:%S")
                    now_ts = datetime.strptime(datetime.now().strftime("%H:%M:%S"), "%H:%M:%S")
                    diff = abs((now_ts - last_ts).total_seconds())
                except:
                    diff = 0
                
                # Se o piloto não manda heartbeat há mais de 15s, consideramos que ele fechou o script
                if diff > 15:
                    state = "offline"

                with cols[idx]:
                    st.markdown(f"**{colors.get(state, '⚪')} {driver}**")
                    st.caption(f"{labels.get(state, '---')} | Latência: {int(diff)}s")
        else:
            st.info("⚪ AGUARDANDO CONEXÃO DA EQUIPE...")
    else:
        # Lógica original mantida para o modo Local
        state = status_data.get("state", "offline")
        colors = {"offline": "🔴", "connected": "🟡", "cockpit": "🟢"}
        labels = {"offline": "DESCONECTADO", "connected": "MENU", "cockpit": "READY (COCKPIT)"}
        col1, col2 = st.columns([1, 4])
        with col1: st.subheader(f"{colors.get(state, '⚪')} {labels.get(state, '---')}")
        with col2:
            if state == "cockpit":
                st.caption(f"👤 Piloto: {status_data.get('driver', '---')} | 📍 Pista: {status_data.get('track', '---')}")
            else:
                st.caption("Aguardando iRacing local...")

# ==============================
# RENDERIZAÇÃO DE MÉTRICAS
# ==============================

def render_metrics(df):
    if df.empty: return

    # --- SELEÇÃO AUTOMÁTICA DE PILOTO E SESSÃO ---
    col_driver, col_race = st.columns(2)
    
    # 1. Identifica os pilotos disponíveis
    pilotos_disponiveis = df['Piloto'].unique().tolist()
    piloto_ativo = pilotos_disponiveis[0] if pilotos_disponiveis else "---"
    
    # 2. Descobre quem está fisicamente no carro (último state == 'cockpit')
    if 'state' in df.columns:
        df_cockpit = df[df['state'] == 'cockpit']
        if not df_cockpit.empty:
            piloto_ativo = df_cockpit.iloc[-1]['Piloto']
            
    # 3. Define o índice padrão do selectbox dinamicamente
    default_driver_idx = pilotos_disponiveis.index(piloto_ativo) if piloto_ativo in pilotos_disponiveis else 0
    
    with col_driver:
        piloto_selected = st.selectbox("Analisar dados de:", pilotos_disponiveis, index=default_driver_idx)
        
    with col_race:
        sessions = df['Sessao'].unique().tolist()
        default_index = sessions.index("Race") if "Race" in sessions else 0
        session_selected = st.selectbox("Sessão:", sessions, index=default_index)

    st.divider()
    st.divider()

    df_session = df[df['Sessao'] == session_selected].copy()
    df_session['stint_change'] = (df_session['Piloto'] != df_session['Piloto'].shift()) | \
                                 (df_session['Combustivel_Restante'] > df_session['Combustivel_Restante'].shift() + 0.5)
    df_session['global_stint_id'] = df_session['stint_change'].cumsum()

    df_p = df_session[df_session['Piloto'] == piloto_selected].copy()
    if df_p.empty:
        st.warning("Sem dados para este piloto.")
        return

    last_global_id = df_p['global_stint_id'].iloc[-1]
    df_this_stint = df_p[df_p['global_stint_id'] == last_global_id]
    stint_laps = len(df_this_stint[df_this_stint['Tempo'] > 0])
    
    # 1. Filtramos apenas as voltas de corrida válidas primeiro
    df_valid = df_p[df_p['Tempo'] > 0].copy().sort_values("Volta")

    # 2. A MÁGICA ACONTECE AQUI: Recalculamos as estatísticas apenas nas voltas reais
    if not df_valid.empty:
        df_valid["Media_3_Voltas"] = df_valid["Tempo"].rolling(3).mean().fillna(df_valid["Tempo"])
        
        # Consumo real isolando os "heartbeats" parados
        df_valid["Consumo_Volta"] = df_valid["Combustivel_Restante"].shift(1) - df_valid["Combustivel_Restante"]
        # Limpa o consumo se houver pitstop (reabastecimento gera números negativos)
        df_valid["Consumo_Volta"] = df_valid["Consumo_Volta"].apply(lambda x: x if 0 < x < 20 else 0)
        df_valid["Media_Consumo_3_Voltas"] = df_valid["Consumo_Volta"].rolling(3).mean().fillna(df_valid["Consumo_Volta"])

    last_row = df_p.iloc[-1] # Mantém para ler a posição global e combustível bruto atual

    # 3. Métricas do Topo da Tela extraídas dos dados limpos
    avg_cons_3v = df_valid.iloc[-1].get('Media_Consumo_3_Voltas', 0) if not df_valid.empty else 0
    fuel_remaining = last_row['Combustivel_Restante']
    fuel_laps_est = fuel_remaining / avg_cons_3v if avg_cons_3v > 0 else 0

    # Blocos de Métricas Visuais
    st.subheader("🏎️ Dados Gerais da Equipe")
    col_e1, col_e2, col_e3 = st.columns(3)
    col_e1.metric("Voltas Totais (Sessão)", int(df_session["Volta"].max()) if not df_session.empty else 0)
    col_e2.metric("Posição Geral", f"P{int(last_row.get('Pos_Geral', 0))}")
    col_e3.metric("Posição Classe", f"P{int(last_row.get('Pos_Classe', 0))}")
    
    st.subheader(f"👤 Piloto: {piloto_selected}")
    col_p1, col_p2, col_p3 = st.columns(3)
    col_p1.metric("Voltas Piloto", len(df_valid))
    col_p2.metric("Stint Atual", f"{stint_laps} v")
    col_p3.metric("Consumo Médio (3v)", f"{avg_cons_3v:.3f} L")

    col_p4, col_p5, col_p6 = st.columns(3)
    col_p4.metric("Última Volta", format_time(df_valid.iloc[-1]['Tempo'] if not df_valid.empty else 0))
    col_p5.metric("Melhor Volta", format_time(df_valid['Tempo'].min() if not df_valid.empty else 0))
    col_p6.metric("Autonomia Estimada", f"{fuel_laps_est:.1f} v")

    # Gráficos com Escalas Unificadas
    st.subheader("📈 Análise de Ritmo e Consumo")
    g1, g2 = st.columns(2)
    
    if not df_valid.empty:
        # AQUI FORÇAMOS A MESMA ESCALA PARA AS DUAS LINHAS
        y_min, y_max = df_valid['Tempo'].min() - 0.5, df_valid['Tempo'].max() + 0.5
        c_max = df_valid['Consumo_Volta'].max() + 0.5
        
        base = alt.Chart(df_valid).encode(x=alt.X('Volta:O', title='Nº da Volta'))

        # Gráfico 1: Consistência
        line = base.mark_line(point=True, opacity=0.4).encode(
            y=alt.Y('Tempo:Q', scale=alt.Scale(domain=[y_min, y_max]), title='Tempo (s)')
        )
        avg_line = base.mark_line(color='#FFD700', strokeWidth=3).encode(
            y=alt.Y('Media_3_Voltas:Q', scale=alt.Scale(domain=[y_min, y_max]))
        )
        g1.altair_chart(alt.layer(line, avg_line).properties(title="Consistência de Ritmo", height=300), use_container_width=True)

        # Gráfico 2: Consumo
        f_line = base.mark_line(point=True, color='#FF4B4B').encode(
            y=alt.Y('Consumo_Volta:Q', scale=alt.Scale(domain=[0, c_max]), title='Consumo (L)')
        )
        f_avg = base.mark_line(color='#FFD700', strokeWidth=3).encode(
            y=alt.Y('Media_Consumo_3_Voltas:Q', scale=alt.Scale(domain=[0, c_max]))
        )
        g2.altair_chart(alt.layer(f_line, f_avg).properties(title="Histórico de Consumo", height=300), use_container_width=True)
        
# ==============================
# EXECUÇÃO PRINCIPAL
# ==============================

st.sidebar.title("⚙️ Configurações")
app_mode = st.sidebar.radio("Operação", ["📡 Live Telemetry", "📂 Post-Race Analysis"])

df_live = pd.DataFrame()
is_cloud_active = False

if app_mode == "📡 Live Telemetry":
    conn_mode = st.sidebar.selectbox("Fonte de Dados", ["Local (Pasta/CSV)", "Cloud (API Server)"])
    
    if conn_mode == "Cloud (API Server)":
        server_ip = st.sidebar.text_input("IP/URL do Servidor", "spondylitic-junior-obedient.ngrok-free.dev")
        session_id = st.sidebar.text_input("ID Sessão", "Daytona_Test")
        
        # Limpeza inteligente da URL para NGROK
        clean_host = server_ip.strip().replace("https://", "").replace("http://", "")
        if "ngrok-free.dev" in clean_host:
            CLOUD_URL = f"https://{clean_host}/session/{session_id}"
        else:
            CLOUD_URL = f"http://{clean_host}:8000/session/{session_id}"
        
        df_live = fetch_cloud_data(CLOUD_URL)
        is_cloud_active = True
        render_traffic_light({}, is_cloud=True, df=df_live)
    else:
        if LOG_DIR.exists():
            files = [f for f in os.listdir(LOG_DIR) if f.startswith("stint_")]
            if files:
                latest = LOG_DIR / max(files, key=lambda x: os.path.getctime(LOG_DIR / x))
                try: df_live = pd.read_csv(latest)
                except: st.sidebar.warning("🔄 Arquivo travado...")
        render_traffic_light(get_status_local(), is_cloud=False)

else:
    uploaded = st.sidebar.file_uploader("Carregar CSV", type="csv")
    if uploaded: df_live = pd.read_csv(uploaded)

st.title(f"🏎️ {app_mode}")
if is_cloud_active:
    st.subheader("☁️ MODO CLOUD ATIVO")
    st.caption("Recebendo telemetria via API remota.")

if not df_live.empty:
    df_normalized = normalize_telemetry(df_live) 
    render_metrics(df_normalized)
else:
    st.info("Aguardando entrada de dados...")

if app_mode == "📡 Live Telemetry":
    time.sleep(REFRESH_RATE_ST)
    st.rerun()