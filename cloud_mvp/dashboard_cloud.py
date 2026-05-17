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
import pytz

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
    headers = {
        'ngrok-skip-browser-warning': 'true',
        'Bypass-Tunnel-Reminder': 'true',
        'User-Agent': 'iRacingTelemetryDashboard/1.0'
    }
    try:
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        if response.status_code == 200:
            data = response.json()
            if not data: return pd.DataFrame()
            df = pd.DataFrame(data)
            mapping = {
                "driver":         "Piloto",
                "lap":            "Volta",
                "lap_time":       "Tempo",
                "fuel":           "Combustivel_Restante",
                "position":       "Pos_Geral",
                "class_position": "Pos_Classe",
                "session_type":   "Sessao",    # FIX: Practice/Qualify/Race real
                "timestamp":      "Timestamp",
                "state":          "state"
            }
            df = df.rename(columns={k: v for k, v in mapping.items() if k in df.columns})
            if "Sessao" not in df.columns: df["Sessao"] = "Race"
            return df
        return pd.DataFrame()
    except Exception as e:
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
    if 'Piloto' not in df.columns:
        df['Piloto'] = 'Desconhecido'
    else:
        # FIX #1: normaliza espaços para evitar mismatch no filtro por piloto
        df['Piloto'] = df['Piloto'].astype(str).str.strip()
    # FIX #8: só faz fallback de Pos_Classe → Pos_Geral se a coluna não veio da nuvem
    if 'Pos_Classe' not in df.columns:
        df['Pos_Classe'] = df['Pos_Geral'] if 'Pos_Geral' in df.columns else 0
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
            df_last_status = df.groupby('Piloto').tail(1)
            cols = st.columns(len(df_last_status))
            colors = {"offline": "🔴", "connected": "🟡", "cockpit": "🟢"}
            labels = {"offline": "OFFLINE", "connected": "BOX / MENU", "cockpit": "NO CARRO"}
            for idx, row in enumerate(df_last_status.itertuples()):
                state = getattr(row, "state", "offline")
                driver = getattr(row, "Piloto", "Unknown")
                timestamp_str = getattr(row, "Timestamp", "00:00:00")
                try:
                    last_ts = datetime.strptime(timestamp_str, "%H:%M:%S")
                    fuso_br = pytz.timezone('America/Sao_Paulo')
                    hora_atual_br = datetime.now(fuso_br).strftime("%H:%M:%S")
                    now_ts = datetime.strptime(hora_atual_br, "%H:%M:%S")
                    diff = abs((now_ts - last_ts).total_seconds())
                except:
                    diff = 0
                if diff > 15:
                    state = "offline"
                with cols[idx]:
                    st.markdown(f"**{colors.get(state, '⚪')} {driver}**")
                    st.caption(f"{labels.get(state, '---')} | Latência: {int(diff)}s")
        else:
            st.info("⚪ AGUARDANDO CONEXÃO DA EQUIPE...")
    else:
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

    col_driver, col_race = st.columns(2)

    pilotos_disponiveis = df['Piloto'].unique().tolist()
    piloto_ativo = pilotos_disponiveis[0] if pilotos_disponiveis else "---"

    if 'state' in df.columns:
        df_cockpit = df[df['state'] == 'cockpit']
        if not df_cockpit.empty:
            piloto_ativo = df_cockpit.iloc[-1]['Piloto']

    default_driver_idx = pilotos_disponiveis.index(piloto_ativo) if piloto_ativo in pilotos_disponiveis else 0

    with col_driver:
        piloto_selected = st.selectbox("Analisar dados de:", pilotos_disponiveis, index=default_driver_idx)

    with col_race:
        sessions = df['Sessao'].unique().tolist()
        default_index = sessions.index("Race") if "Race" in sessions else 0
        session_selected = st.selectbox("Sessão:", sessions, index=default_index)

    st.divider()

    # ── Filtragem base ─────────────────────────────────────────────────────────
    df_session = df[df['Sessao'] == session_selected].copy()

    # FIX #4 STINT: ordena cronologicamente ANTES do shift() para garantir que
    # a comparação entre linhas respeite a ordem real das voltas.
    # .fillna(True) marca a primeira linha sempre como início de stint.
    df_session_laps = df_session[df_session['Tempo'] > 0].copy()
    if not df_session_laps.empty:
        df_session_laps = (
            df_session_laps
            .sort_values(['Volta', 'Timestamp'])
            .reset_index(drop=True)
        )
        df_session_laps['stint_change'] = (
            (df_session_laps['Piloto'] != df_session_laps['Piloto'].shift()) |
            (df_session_laps['Combustivel_Restante'] > df_session_laps['Combustivel_Restante'].shift() + 1.0)
        ).fillna(True)
        df_session_laps['global_stint_id'] = df_session_laps['stint_change'].cumsum()

    df_p = df_session[df_session['Piloto'] == piloto_selected].copy()
    if df_p.empty:
        st.warning("Sem dados para este piloto.")
        return

    # FIX #4: conta voltas apenas no último stint contínuo do piloto selecionado
    df_p_laps = (
        df_session_laps[df_session_laps['Piloto'] == piloto_selected]
        if not df_session_laps.empty
        else pd.DataFrame()
    )
    if not df_p_laps.empty:
        last_stint_id = df_p_laps['global_stint_id'].iloc[-1]
        stint_laps = int((df_p_laps['global_stint_id'] == last_stint_id).sum())
    else:
        stint_laps = 0

    # Voltas válidas — df_valid é EXCLUSIVO do piloto selecionado (FIX #1)
    df_valid = df_p[df_p['Tempo'] > 0].copy().sort_values('Volta').reset_index(drop=True)

    # Recalcula métricas isoladas do piloto (sem contaminação de rolling entre pilotos)
    if not df_valid.empty:
        df_valid['Media_3_Voltas'] = df_valid['Tempo'].rolling(3).mean().fillna(df_valid['Tempo'])
        df_valid['Consumo_Volta'] = df_valid['Combustivel_Restante'].shift(1) - df_valid['Combustivel_Restante']
        df_valid['Consumo_Volta'] = df_valid['Consumo_Volta'].apply(lambda x: x if 0 < x < 20 else 0)
        df_valid['Media_Consumo_3_Voltas'] = df_valid['Consumo_Volta'].rolling(3).mean().fillna(df_valid['Consumo_Volta'])

    last_row = df_p.iloc[-1]
    avg_cons_3v = float(df_valid.iloc[-1]['Media_Consumo_3_Voltas']) if not df_valid.empty else 0
    # FIX #7: usa consumo da última volta (= lógica do iRacing), fallback para média 3v
    last_cons   = float(df_valid.iloc[-1]['Consumo_Volta'])         if not df_valid.empty else 0
    fuel_remaining = float(last_row['Combustivel_Restante'])
    cons_for_autonomia = last_cons if last_cons > 0 else avg_cons_3v
    fuel_laps_est = fuel_remaining / cons_for_autonomia if cons_for_autonomia > 0 else 0

    # FIX #2: congela Autonomia Estimada entre recarregamentos;
    # só atualiza quando uma nova volta é fechada.
    _ak  = f"autonomia_{piloto_selected}_{session_selected}"
    _alk = f"autonomia_lap_{piloto_selected}_{session_selected}"
    if not df_valid.empty:
        current_last_lap = int(df_valid.iloc[-1]['Volta'])
        if st.session_state.get(_alk) != current_last_lap:
            st.session_state[_ak]  = fuel_laps_est
            st.session_state[_alk] = current_last_lap
    fuel_laps_display = st.session_state.get(_ak, fuel_laps_est)

    total_session_laps = int(df_session_laps['Volta'].max()) if not df_session_laps.empty else 0

    # ── Métricas da equipe ─────────────────────────────────────────────────────
    st.subheader("🏎️ Dados Gerais da Equipe")
    col_e1, col_e2, col_e3 = st.columns(3)
    col_e1.metric("Voltas Totais (Sessão)", total_session_laps)
    col_e2.metric("Posição Geral",  f"P{int(last_row.get('Pos_Geral', 0))}")
    col_e3.metric("Posição Classe", f"P{int(last_row.get('Pos_Classe', 0))}")

    # ── Métricas do piloto ─────────────────────────────────────────────────────
    st.subheader(f"👤 Piloto: {piloto_selected}")
    col_p1, col_p2, col_p3 = st.columns(3)
    col_p1.metric("Voltas Piloto",      len(df_valid))
    col_p2.metric("Stint Atual",        f"{stint_laps} v")
    col_p3.metric("Consumo Médio (3v)", f"{avg_cons_3v:.2f} L")   # FIX #3: 2dp

    col_p4, col_p5, col_p6 = st.columns(3)
    col_p4.metric("Última Volta",       format_time(float(df_valid.iloc[-1]['Tempo'])) if not df_valid.empty else "---")
    # FIX #1: df_valid já é filtrado por piloto_selected — Tempo.min() = melhor DESTE piloto
    col_p5.metric("Melhor Volta",       format_time(float(df_valid['Tempo'].min()))    if not df_valid.empty else "---")
    col_p6.metric("Autonomia Estimada", f"{fuel_laps_display:.1f} v")  # FIX #2 + #7

    if df_valid.empty:
        st.info("Aguardando voltas válidas...")
        return

    # ── Gráfico 1 e 2: Ritmo e Consumo ────────────────────────────────────────
    st.subheader("📈 Análise de Ritmo e Consumo")

    df_valid['Tempo_Tooltip']  = df_valid['Tempo'].apply(format_time)
    df_valid['Media_Tooltip']  = df_valid['Media_3_Voltas'].apply(format_time)

    y_min  = max(0, df_valid['Tempo'].min() - 1.0)
    y_max  = df_valid['Tempo'].max() + 1.0
    c_max  = max(df_valid['Consumo_Volta'].max(), 0.1) + 0.5

    base = alt.Chart(df_valid).encode(x=alt.X('Volta:O', title='Nº da Volta'))

    g1, g2 = st.columns(2)

    # Gráfico 1: Consistência de Ritmo
    line     = base.mark_line(point=True, opacity=0.4).encode(
        y=alt.Y('Tempo:Q', scale=alt.Scale(domain=[y_min, y_max]), title='Tempo (s)'),
        tooltip=[alt.Tooltip('Volta:O'), alt.Tooltip('Tempo_Tooltip:N', title='Tempo')]
    )
    avg_line = base.mark_line(color='#FFD700', strokeWidth=3, point=True).encode(
        y=alt.Y('Media_3_Voltas:Q', scale=alt.Scale(domain=[y_min, y_max])),
        tooltip=[alt.Tooltip('Volta:O'), alt.Tooltip('Media_Tooltip:N', title='Média (3v)')]
    )
    g1.altair_chart(
        alt.layer(line, avg_line).resolve_scale(y='shared').properties(title="Consistência de Ritmo", height=300),
        use_container_width=True
    )

    # Gráfico 2: Histórico de Consumo — FIX #3: tooltips 2dp
    f_line = base.mark_line(point=True, color='#FF4B4B').encode(
        y=alt.Y('Consumo_Volta:Q', scale=alt.Scale(domain=[0, c_max]), title='Consumo (L)'),
        tooltip=[alt.Tooltip('Volta:O'), alt.Tooltip('Consumo_Volta:Q', format='.2f')]
    )
    f_avg  = base.mark_line(color='#FFD700', strokeWidth=3, point=True).encode(
        y=alt.Y('Media_Consumo_3_Voltas:Q', scale=alt.Scale(domain=[0, c_max])),
        tooltip=[alt.Tooltip('Volta:O'), alt.Tooltip('Media_Consumo_3_Voltas:Q', format='.2f')]
    )
    g2.altair_chart(
        alt.layer(f_line, f_avg).resolve_scale(y='shared').properties(title="Histórico de Consumo", height=300),
        use_container_width=True
    )

    # ── Gráfico 3: Volume do Tanque ────────────────────────────────────────────
    st.subheader("⛽ Volume do Tanque por Volta")

    tank_col   = 'Combustivel_no_Inicio_Volta' if 'Combustivel_no_Inicio_Volta' in df_valid.columns else 'Combustivel_Restante'
    tank_label = 'Combustível no início da volta (L)' if tank_col == 'Combustivel_no_Inicio_Volta' else 'Combustível restante (L)'

    df_tank  = df_valid[['Volta', tank_col]].copy().reset_index(drop=True)
    tank_max = float(df_tank[tank_col].max()) + 2.0

    # FIX PROJEÇÃO: reconstrói stint-a-stint para respeitar reabastecimentos.
    # Detecta início de novo stint quando combustível SOBE mais de 1L (refuel).
    # Dentro de cada bloco projeta linearmente a partir do pico daquele bloco.
    if cons_for_autonomia > 0:
        projecao = []
        stint_start_idx = 0
        values = df_tank[tank_col].tolist()
        for i in range(len(values)):
            # Reabastecimento: valor atual > anterior + 1L → reseta âncora
            if i > 0 and values[i] > values[i - 1] + 1.0:
                stint_start_idx = i
            laps_into_stint = i - stint_start_idx
            proj_val = max(0.0, values[stint_start_idx] - cons_for_autonomia * laps_into_stint)
            projecao.append(proj_val)
        df_tank['Projecao'] = projecao

    base_t    = alt.Chart(df_tank).encode(x=alt.X('Volta:O', title='Nº da Volta'))
    tank_real = base_t.mark_line(point=True, color='#00BFFF', strokeWidth=2).encode(
        y=alt.Y(f'{tank_col}:Q', scale=alt.Scale(domain=[0, tank_max]), title=tank_label),
        tooltip=[alt.Tooltip('Volta:O'), alt.Tooltip(f'{tank_col}:Q', title='Tanque (L)', format='.2f')]
    )

    if 'Projecao' in df_tank.columns:
        tank_proj = base_t.mark_line(color='#FFD700', strokeWidth=2, strokeDash=[6, 3]).encode(
            y=alt.Y('Projecao:Q', scale=alt.Scale(domain=[0, tank_max])),
            tooltip=[alt.Tooltip('Volta:O'), alt.Tooltip('Projecao:Q', title='Projeção (L)', format='.2f')]
        )
        tank_final = alt.layer(tank_real, tank_proj).resolve_scale(y='shared').properties(
            title="Volume do Tanque  (azul = real | amarelo tracejado = projeção)", height=280
        )
    else:
        tank_final = tank_real.properties(title="Volume do Tanque por Volta", height=280)

    st.altair_chart(tank_final, use_container_width=True)

    # ── Tabela de Histórico ────────────────────────────────────────────────────
    st.subheader("📋 Histórico Detalhado")

    table_cols = ['Volta', 'Tempo', 'Media_3_Voltas', 'Consumo_Volta', 'Media_Consumo_3_Voltas', 'Combustivel_Restante']
    if 'Combustivel_no_Inicio_Volta' in df_valid.columns:
        table_cols.insert(-1, 'Combustivel_no_Inicio_Volta')

    df_table = df_valid[table_cols].copy()
    df_table['Tempo']              = df_table['Tempo'].apply(format_time)
    df_table['Media_3_Voltas']     = df_table['Media_3_Voltas'].apply(format_time)
    df_table['Consumo_Volta']      = df_table['Consumo_Volta'].round(2)          # FIX #3
    df_table['Media_Consumo_3_Voltas'] = df_table['Media_Consumo_3_Voltas'].round(2)  # FIX #3
    df_table['Combustivel_Restante'] = df_table['Combustivel_Restante'].round(2)
    if 'Combustivel_no_Inicio_Volta' in df_table.columns:
        df_table = df_table.rename(columns={'Combustivel_no_Inicio_Volta': 'Tanque_Início'})
        df_table['Tanque_Início'] = df_table['Tanque_Início'].round(2)

    st.dataframe(df_table.sort_values('Volta', ascending=False), use_container_width=True, hide_index=True)


# ==============================
# EXECUÇÃO PRINCIPAL
# ==============================

st.sidebar.title("⚙️ Configurações")
app_mode = st.sidebar.radio("Operação", ["📡 Live Telemetry", "📂 Post-Race Analysis"])

df_live = pd.DataFrame()
is_cloud_active = False
base_url = ""
session_id = ""

if app_mode == "📡 Live Telemetry":
    conn_mode = st.sidebar.selectbox("Fonte de Dados", ["Local (Pasta/CSV)", "Cloud (API Server)"])

    if conn_mode == "Cloud (API Server)":
        server_ip  = st.sidebar.text_input("URL Base do Servidor", "https://iracing-telemetry-vfak.onrender.com")
        session_id = st.sidebar.text_input("ID Sessão", "Daytona_Test")
        base_url   = server_ip.strip().rstrip('/')
        CLOUD_URL  = f"{base_url}/session/{session_id}"
        df_live    = fetch_cloud_data(CLOUD_URL)
        is_cloud_active = True
        render_traffic_light({}, is_cloud=True, df=df_live)

        # FIX #6: reset de sessão — requer endpoint DELETE /session/{id} no FastAPI
        st.sidebar.divider()
        if st.sidebar.button("🗑️ Resetar Dados da Sessão", type="secondary",
                             help="Apaga todos os dados desta Session ID no servidor (útil para testes)"):
            try:
                r = requests.delete(f"{base_url}/session/{session_id}", timeout=5)
                if r.status_code == 200:
                    st.sidebar.success("✅ Sessão resetada com sucesso!")
                    st.rerun()
                else:
                    st.sidebar.error(f"Servidor retornou {r.status_code}. Verifique se o endpoint DELETE existe.")
            except Exception as e:
                st.sidebar.error("⚠️ Falha ao conectar com o servidor.")
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