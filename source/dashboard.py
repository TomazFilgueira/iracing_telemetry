import streamlit as st
import pandas as pd
import altair as alt
import glob
import os
import time
from config import LOG_DIR, REFRESH_RATE_ST

st.set_page_config(page_title="Strategy & Analysis Deck", layout="wide")

def format_time(seconds):
    """Formata segundos para o padrão de telemetria mm:ss:ms."""
    if seconds <= 0: return "00:00:000"
    minutes = int(seconds // 60)
    rem_seconds = seconds % 60
    return f"{minutes:02d}:{rem_seconds:06.3f}".replace('.', ':')

def get_latest_file():
    files = glob.glob(str(LOG_DIR / "stint_*.csv"))
    return max(files, key=os.path.getctime) if files else None

def render_metrics(df):
    if df.empty:
        st.warning("Dados insuficientes.")
        return

    last_row = df.iloc[-1]
    
    # --- SELETOR DE POSIÇÃO COM CORES DINÂMICAS ---
    pos_mode = st.radio(
        "Filtro de Posição (Troca a cor do banner abaixo):",
        ["Classe (Categoria)", "Geral (Overall)"],
        horizontal=True
    )
    
    if pos_mode == "Classe (Categoria)":
        msg = f"🔹 **MODO CLASSE ATIVO** | Equipe: {last_row['Equipe']} | Pista: {last_row['Pista']} | Posição: P{int(last_row.get('Pos_Classe', 0))}"
        st.info(msg)
    else:
        msg = f"🔴 **MODO GERAL ATIVO** | Equipe: {last_row['Equipe']} | Pista: {last_row['Pista']} | Posição: P{int(last_row.get('Pos_Geral', 0))}"
        st.error(msg)

    st.divider()

    # --- SELEÇÃO DE PILOTO E PERFORMANCE ---
    piloto = st.selectbox("Selecione o Piloto", sorted(df['Piloto'].unique()))
    df_p = df[df['Piloto'] == piloto].copy()
    df_p['Tempo_Fmt'] = df_p['Tempo'].apply(format_time)
    df_p['Media_Fmt'] = df_p['Media_3_Voltas'].apply(format_time)

    st.subheader("⏱️ Performance & Estratégia")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Última Volta", format_time(df_p.iloc[-1]['Tempo']))
    k2.metric("Melhor Volta", format_time(df_p['Tempo'].min()))
    k3.metric("Consumo Médio", f"{df_p['Consumo_Volta'].mean():.3f} L")
    k4.metric("No Tanque", f"{df_p.iloc[-1]['Combustivel_Restante']:.2f} L")

    st.divider()

    # --- GRÁFICOS COM ZOOM ---
    st.subheader("📈 Análise Técnica")
    g1, g2 = st.columns(2)

    df_valid = df_p[df_p['Volta'] > 1].copy()
    if not df_valid.empty:
        y_min = min(df_valid['Tempo'].min(), df_valid['Media_3_Voltas'].min()) - 0.2
        y_max = max(df_valid['Tempo'].max(), df_valid['Media_3_Voltas'].max()) + 0.2
        
        base = alt.Chart(df_p).encode(x=alt.X('Volta:O', title='Volta'))
        line_raw = base.mark_line(point=True, opacity=0.3, color='#1f77b4').encode(
            y=alt.Y('Tempo:Q', title='Tempo (s)', scale=alt.Scale(domain=[y_min, y_max])),
            tooltip=[alt.Tooltip('Volta'), alt.Tooltip('Tempo_Fmt', title='Tempo')]
        )
        line_avg = base.mark_line(color='#FFD700', strokeWidth=3).encode(
            y=alt.Y('Media_3_Voltas:Q'),
            tooltip=[alt.Tooltip('Volta'), alt.Tooltip('Media_Fmt', title='Média (3v)')]
        )
        # Atualizado para width='stretch' conforme nova documentação
        g1.altair_chart(alt.layer(line_raw, line_avg).properties(height=350, title="Ritmo: Volta vs Média Móvel"), width='stretch')

    y_min_f = max(0, df_p['Consumo_Volta'].min() - 0.1)
    y_max_f = df_p['Consumo_Volta'].max() + 0.1
    chart_fuel = alt.Chart(df_p).mark_bar(color='#FF4B4B').encode(
        x=alt.X('Volta:O'),
        y=alt.Y('Consumo_Volta:Q', title='Consumo (L)', scale=alt.Scale(domain=[y_min_f, y_max_f])),
        tooltip=['Volta', 'Consumo_Volta']
    ).properties(height=350, title="Consumo por Volta")
    
    # Atualizado para width='stretch' conforme nova documentação
    g2.altair_chart(chart_fuel, width='stretch')

# --- EXECUÇÃO PRINCIPAL ---
st.title("🏎️ Real-Time Strategy & Analysis")
st.sidebar.header("🛠️ Configurações")
mode = st.sidebar.radio("Modo", ["📡 Live Telemetry", "📂 Post-Race Analysis"])

if mode == "📡 Live Telemetry":
    live_file = get_latest_file()
    if live_file:
        render_metrics(pd.read_csv(live_file))
        time.sleep(REFRESH_RATE_ST)
        st.rerun()
else:
    uploaded = st.sidebar.file_uploader("Upload de Sessão (CSV)", type="csv")
    if uploaded:
        render_metrics(pd.read_csv(uploaded))