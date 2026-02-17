import streamlit as st
import pandas as pd
import altair as alt
import json
import os
import time
from config import LOG_DIR, REFRESH_RATE_ST

# ==============================
# Configuração da Página
# ==============================
st.set_page_config(page_title="Strategy & Analysis Deck", layout="wide")
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
# FUNÇÕES DE UTILIDADE
# ==============================

def get_status():
    try:
        with open(LOG_DIR / "status.json", "r") as f:
            data = json.load(f)
            segundos_desde_update = time.time() - data.get("last_update", 0)
            if segundos_desde_update > 10:
                return {"state": "offline", "driver": "---", "track": "---"}
            return data
    except Exception:
        return {"state": "offline", "driver": "---", "track": "---"}

def format_time(seconds):
    if seconds <= 0: return "00:00:000"
    minutes = int(seconds // 60)
    rem_seconds = seconds % 60
    return f"{minutes:02d}:{rem_seconds:06.3f}".replace('.', ':')

def render_traffic_light(status):
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

# ==============================
# LÓGICA PRINCIPAL
# ==============================

def render_metrics(df):
    if df.empty:
        st.warning("Aguardando gravação da primeira volta...")
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

    # --- NOVA LÓGICA DE STINT (CORREÇÃO) ---
    # 1. Filtramos apenas a sessão para identificar trocas globais de pilotos
    df_s = df[df['Sessao'] == session_selected].copy()
    
    # 2. Identificamos as quebras (Troca de piloto OU Reabastecimento)
    df_s['stint_change'] = (df_s['Piloto'] != df_s['Piloto'].shift()) | \
                           (df_s['Combustivel_Restante'] > df_s['Combustivel_Restante'].shift() + 0.5)
    
    # 3. Criamos um ID global para cada stint que ocorreu no carro
    df_s['global_stint_id'] = df_s['stint_change'].cumsum()
    
    # 4. Agora sim filtramos pelo piloto selecionado
    df_p = df_s[df_s['Piloto'] == piloto_selected].copy()
    
    if df_p.empty:
        st.warning("Sem dados válidos para este piloto nesta sessão.")
        return

    # 5. Pegamos o ID do último stint que este piloto fez
    last_global_id = df_p['global_stint_id'].iloc[-1]
    stint_number = int(last_global_id)
    
    # 6. Voltas do stint atual
    df_this_stint = df_p[df_p['global_stint_id'] == last_global_id]
    stint_laps = len(df_this_stint[df_this_stint['Tempo'] > 0])

    # --- PREPARAÇÃO DE DADOS PARA GRÁFICOS E KPIs ---
    last_row = df_p.iloc[-1]
    df_valid = df_p[df_p['Tempo'] > 0].copy().reset_index(drop=True)
    df_valid["Volta"] = df_valid.index + 1
    
    laps_completed = len(df_valid)
    session_laps_est = last_row.get('Voltas_Restantes_Estimadas', 0)
    total_estimated = laps_completed + session_laps_est

    # --- CÁLCULOS DE COMBUSTÍVEL ---
    avg_cons_3v = last_row['Media_Consumo_3_Voltas']
    fuel_remaining = last_row['Combustivel_Restante']
    fuel_laps_est = fuel_remaining / avg_cons_3v if avg_cons_3v > 0 else 0

    # --- ALERTAS ---
    if fuel_laps_est > 0 and fuel_laps_est < 2.5:
        st.error(f"⚠️ BOX BOX BOX! Combustível crítico: ~{fuel_laps_est:.1f} voltas restantes!")
    elif fuel_laps_est > 0 and fuel_laps_est < session_laps_est:
        st.warning(f"⛽ Combustível ({fuel_laps_est:.1f} v) menor que necessário ({session_laps_est:.1f} v).")

    # --- POSIÇÃO ---
    col_pos1, col_pos2, col_pos3 = st.columns([1,0.5,2])
    with col_pos1:
        st.markdown('<div class="metric-align-top">', unsafe_allow_html=True)
        st.error(f"🔴 GERAL | Posição: P{int(last_row.get('Pos_Geral', 0))}")
        st.info(f"🔵 CLASSE | Posição: P{int(last_row.get('Pos_Classe', 0))}")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- VOLTAS E STINT ---
    with col_pos2:
        st.metric("🏁 Voltas", f"{laps_completed} / {int(total_estimated)}")
        st.metric(f"🔥 Voltas do Stint {stint_number}", f"{stint_laps}")

    # --- KPIs ---
    with col_pos3:
        k1, k2 = st.columns(2)
        k3, k4, k5 = st.columns(3)
        last_v_time = df_valid.iloc[-1]['Tempo'] if not df_valid.empty else 0
        best_lap = df_valid['Tempo'].min() if not df_valid.empty else 0
        
        k1.metric("Última Volta", format_time(last_v_time))
        k2.metric("Melhor Volta", format_time(best_lap))
        k3.metric("Consumo Médio (3v)", f"{avg_cons_3v:.3f} L")
        k4.metric("No Tanque", f"{fuel_remaining:.2f} L")
        k5.metric("Autonomia", f"{fuel_laps_est:.1f} v")

    st.divider()

    # --- GRÁFICOS ---
    st.subheader("📈 Análise de Ritmo e Consumo")
    g1, g2 = st.columns(2)
    if not df_valid.empty:
        y_min, y_max = df_valid['Tempo'].min() - 0.5, df_valid['Tempo'].max() + 0.5
        base = alt.Chart(df_valid).encode(x=alt.X('Volta:O', title='Nº da Volta'))
        line = base.mark_line(point=True, opacity=0.4).encode(
            y=alt.Y('Tempo:Q', title='Tempo (s)', scale=alt.Scale(domain=[y_min, y_max])),
            tooltip=['Volta', 'Tempo']
        )
        avg = base.mark_line(color='#FFD700', strokeWidth=3).encode(y='Media_3_Voltas:Q')
        g1.altair_chart(alt.layer(line, avg).properties(height=350, title="Consistência de Ritmo"), use_container_width=True)

        base_fuel = alt.Chart(df_valid).encode(
    x=alt.X('Volta:O', title='Nº da Volta')
)

    fuel_line = base_fuel.mark_line(point=True).encode(
        y=alt.Y('Consumo_Volta:Q', title='Consumo (Litros)'),
        tooltip=['Volta', 'Consumo_Volta']
    )

    fuel_avg = base_fuel.mark_line(
        color='#FFD700',
        strokeWidth=3
    ).encode(
        y='Media_Consumo_3_Voltas:Q'
    )

    chart_fuel = alt.layer(
        fuel_line,
        fuel_avg
    ).properties(
        height=350,
        title="Consistência de Consumo"
    )

    g2.altair_chart(chart_fuel, use_container_width=True)


    # --- TABELA ---
    st.subheader("📝 Histórico da Sessão")
    df_display = df_valid.copy()
    df_display['Tempo'] = df_display['Tempo'].apply(format_time)
    st.dataframe(df_display[['Volta', 'Tempo', 'Consumo_Volta', 'Pos_Classe', 'Timestamp']], use_container_width=True, hide_index=True)

# ==============================
# EXECUÇÃO PRINCIPAL
# ==============================
st.title("🏎️ Real-Time Strategy & Analysis")
status = get_status()
render_traffic_light(status)
st.divider()

mode = st.sidebar.radio("Modo de Operação", ["📡 Live Telemetry", "📂 Post-Race Analysis"])

if mode == "📡 Live Telemetry":
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
    time.sleep(REFRESH_RATE_ST)
    st.rerun()
else:
    uploaded = st.sidebar.file_uploader("Carregar Arquivo de Telemetria (CSV)", type="csv")
    if uploaded:
        render_metrics(pd.read_csv(uploaded))