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
import pytz # Para lidar com fusos horários corretamente 

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
    # Headers obrigatórios para pular os bloqueios do Ngrok e do LocalTunnel
    headers = {
        'ngrok-skip-browser-warning': 'true',
        'Bypass-Tunnel-Reminder': 'true',
        'User-Agent': 'iRacingTelemetryDashboard/1.0'
    }
    try:
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status() # Faz o painel avisar se o link estiver quebrado
        
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
        # Se der erro de conexão, mostra um aviso vermelho no topo da tela
        st.error(f"⚠️ Erro de conexão com o servidor de telemetria: Verifique a URL.")
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
                
                # Cálculo de latência corrigido com Fuso Horário do Brasil - identificar se o piloto caiu
                try:
                    last_ts = datetime.strptime(timestamp_str, "%H:%M:%S")
                    
                    # Ensina o servidor da nuvem a usar o horário de Brasília
                    fuso_br = pytz.timezone('America/Sao_Paulo')
                    hora_atual_br = datetime.now(fuso_br).strftime("%H:%M:%S")
                    now_ts = datetime.strptime(hora_atual_br, "%H:%M:%S")
                    
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
        # 1. CRIAMOS COLUNAS FORMATADAS PARA O TOOLTIP
        df_valid['Tempo_Tooltip'] = df_valid['Tempo'].apply(format_time)
        df_valid['Media_Tooltip'] = df_valid['Media_3_Voltas'].apply(format_time)

        # FORÇAMOS A MESMA ESCALA PARA AS DUAS LINHAS
        # Garantindo que o limite inferior não seja negativo
        y_min = max(0, df_valid['Tempo'].min() - 1.0)
        y_max = df_valid['Tempo'].max() + 1.0
        c_max = df_valid['Consumo_Volta'].max() + 0.5
        
        base = alt.Chart(df_valid).encode(x=alt.X('Volta:O', title='Nº da Volta'))

        # Gráfico 1: Consistência (Eixo Y em Segundos, Tooltip em mm:ss)
        line = base.mark_line(point=True, opacity=0.4).encode(
            y=alt.Y('Tempo:Q', scale=alt.Scale(domain=[y_min, y_max]), title='Tempo (s)'),
            tooltip=[alt.Tooltip('Volta:O'), alt.Tooltip('Tempo_Tooltip:N', title='Tempo')]
        )
        
        avg_line = base.mark_line(color='#FFD700', strokeWidth=3, point=True).encode(
            y=alt.Y('Media_3_Voltas:Q', scale=alt.Scale(domain=[y_min, y_max])),
            tooltip=[alt.Tooltip('Volta:O'), alt.Tooltip('Media_Tooltip:N', title='Média (3v)')]
        )
        
        # O resolve_scale(y='shared') é o segredo para as duas linhas não brigarem no mesmo gráfico
        pace_chart = alt.layer(line, avg_line).resolve_scale(y='shared').properties(title="Consistência de Ritmo", height=300)
        g1.altair_chart(pace_chart, width='stretch')

        # Gráfico 2: Consumo
        f_line = base.mark_line(point=True, color='#FF4B4B').encode(
            y=alt.Y('Consumo_Volta:Q', scale=alt.Scale(domain=[0, c_max]), title='Consumo (L)'),
            tooltip=['Volta:O', 'Consumo_Volta:Q']
        )
        f_avg = base.mark_line(color='#FFD700', strokeWidth=3, point=True).encode(
            y=alt.Y('Media_Consumo_3_Voltas:Q', scale=alt.Scale(domain=[0, c_max])),
            tooltip=['Volta:O', 'Media_Consumo_3_Voltas:Q']
        )
        
        fuel_chart = alt.layer(f_line, f_avg).resolve_scale(y='shared').properties(title="Histórico de Consumo", height=300)
        g2.altair_chart(fuel_chart, width='stretch')

        # ==========================================
        # TABELA DE HISTÓRICO DE VOLTAS
        # ==========================================
        st.subheader("📋 Histórico Detalhado")
        
        # Seleciona apenas as colunas mais importantes para a tabela
        df_table = df_valid[['Volta', 'Tempo', 'Media_3_Voltas', 'Consumo_Volta', 'Media_Consumo_3_Voltas', 'Combustivel_Restante']].copy()
        
        # Formata as colunas de tempo para ficar amigável (mm:ss) igual no topo da tela
        df_table['Tempo'] = df_table['Tempo'].apply(format_time)
        df_table['Media_3_Voltas'] = df_table['Media_3_Voltas'].apply(format_time)
        
        # Arredonda o consumo para 3 casas decimais para não poluir a tela
        df_table['Consumo_Volta'] = df_table['Consumo_Volta'].round(3)
        df_table['Media_Consumo_3_Voltas'] = df_table['Media_Consumo_3_Voltas'].round(3)
        df_table['Combustivel_Restante'] = df_table['Combustivel_Restante'].round(2)
        
        # Ordena para a volta mais recente aparecer sempre no topo
        df_table = df_table.sort_values('Volta', ascending=False)
        
        # Renderiza a tabela tela cheia e sem o índice (0, 1, 2...) do Pandas
        st.dataframe(df_table, width='stretch', hide_index=True)

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
        # Já deixa o seu túnel padrão preenchido
        server_ip = st.sidebar.text_input("URL Base do Servidor", "https://iracing-telemetry-vfak.onrender.com")
        session_id = st.sidebar.text_input("ID Sessão", "Daytona_Test")
        
        # Limpeza simples: remove barras invertidas sobrando no final, se houver
        base_url = server_ip.strip().rstrip('/')
        
        # Monta a URL perfeita sem forçar a porta 8000
        CLOUD_URL = f"{base_url}/session/{session_id}"
        
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