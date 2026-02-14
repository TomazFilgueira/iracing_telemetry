import streamlit as st
import pandas as pd
import altair as alt
import glob
import os
import time
from config import LOG_DIR, REFRESH_RATE_ST

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Strategy & Analysis Deck", layout="wide")

def get_latest_file():
    """Busca o arquivo CSV mais recente na pasta de logs."""
    files = glob.glob(str(LOG_DIR / "stint_*.csv"))
    return max(files, key=os.path.getctime) if files else None

def render_metrics(df):
    """Renderiza toda a interface de KPIs e Gráficos."""
    if df.empty:
        st.warning("O arquivo selecionado não contém dados suficientes.")
        return

    # --- CABEÇALHO DE EQUIPE E POSIÇÃO ---
    # Opção para ocultar dados de posição para foco total no ritmo.
    show_team = st.checkbox("Exibir Detalhes de Equipe e Posição", value=True)
    last_row = df.iloc[-1]

    if show_team and 'Equipe' in df.columns:
        with st.container():
            st.info(f"🚩 **Equipe:** {last_row['Equipe']} | "
                    f"**Posição Geral:** P{int(last_row['Pos_Geral'])} | "
                    f"**Posição na Classe:** P{int(last_row['Pos_Classe'])}")
        st.divider()

    # --- SELEÇÃO DE PILOTO (SUPORTE ENDURANCE) ---
    # Permite analisar individualmente cada piloto que passou pelo carro.
    pilotos_disponiveis = sorted(df['Piloto'].unique())
    selected_pilot = st.selectbox("Selecione o Piloto para Análise", pilotos_disponiveis)
    df_p = df[df['Piloto'] == selected_pilot].copy()
    
    if df_p.empty:
        st.error("Sem dados para o piloto selecionado.")
        return

    last_p = df_p.iloc[-1]

    # --- PAINEL DE MÉTRICAS (KPIs) ---
    col_perf, col_fuel = st.columns(2)

    with col_perf:
        st.subheader("⏱️ Performance")
        p1, p2, p3 = st.columns(3)
        p1.metric("Última Volta", f"{last_p['Tempo']:.3f}s")
        p2.metric("Melhor Volta", f"{df_p['Tempo'].min():.3f}s")
        # Desvio padrão ajuda a entender a consistência estocástica do piloto.
        p3.metric("Consistência (σ)", f"{df_p['Tempo'].std():.3f}s")

    with col_fuel:
        st.subheader("⛽ Estratégia")
        f1, f2, f3 = st.columns(3)
        avg_cons = df_p['Consumo_Volta'].mean()
        f1.metric("Consumo Médio", f"{avg_cons:.3f} L")
        f2.metric("Tanque Atual", f"{last_p['Combustivel_Restante']:.2f} L")
        f3.metric("Voltas no Stint", len(df_p))

    st.divider()

    # --- ANÁLISE VISUAL (GRÁFICOS COM ZOOM DINÂMICO) ---
    # O zoom dinâmico evita que o eixo Y comece em zero, destacando variações mínimas.
    st.subheader("📈 Análise de Dados (Zoom Otimizado)")
    g1, g2 = st.columns(2)

    # Gráfico de Tempos: Filtra outliers (como pit stops) para não achatar a escala.
    df_filtered = df_p[df_p['Tempo'] < df_p['Tempo'].median() * 1.2].copy()
    y_min_lap = df_filtered['Tempo'].min() - 0.2
    y_max_lap = df_filtered['Tempo'].max() + 0.2

    chart_laps = alt.Chart(df_p).mark_line(point=True, color='#1f77b4').encode(
        x=alt.X('Volta:O', title='Volta'),
        y=alt.Y('Tempo:Q', title='Tempo (s)', scale=alt.Scale(domain=[y_min_lap, y_max_lap])),
        tooltip=['Volta', 'Tempo', 'Piloto']
    ).properties(height=350, title="Evolução do Ritmo")

    g1.altair_chart(chart_laps, use_container_width=True)

    # Gráfico de Consumo: Reintrodução do gráfico de barras para estratégia.
    y_min_fuel = max(0, df_p['Consumo_Volta'].min() - 0.1)
    y_max_fuel = df_p['Consumo_Volta'].max() + 0.1

    chart_fuel = alt.Chart(df_p).mark_bar(color='#FF4B4B').encode(
        x=alt.X('Volta:O', title='Volta'),
        y=alt.Y('Consumo_Volta:Q', title='Consumo (L)', scale=alt.Scale(domain=[y_min_fuel, y_max_fuel])),
        tooltip=['Volta', 'Consumo_Volta']
    ).properties(height=350, title="Consumo por Volta")

    g2.altair_chart(chart_fuel, use_container_width=True)

# --- LÓGICA PRINCIPAL DO APP ---
st.title("🏎️ Real-Time Strategy & Analysis")

# Sidebar para alternar entre Live e Histórico.
st.sidebar.header("🛠️ Configurações")
app_mode = st.sidebar.radio("Modo de Operação", ["📡 Live Telemetry", "📂 Post-Race Analysis"])

if app_mode == "📡 Live Telemetry":
    current_file = get_latest_file()
    if current_file:
        st.caption(f"📡 Monitorando: {os.path.basename(current_file)}")
        live_data = pd.read_csv(current_file)
        render_metrics(live_data)
        # Atualização automática conforme taxa definida no config.py.
        time.sleep(REFRESH_RATE_ST)
        st.rerun()
    else:
        st.warning("Aguardando gravação de dados em 'Data_Logs'...")
        time.sleep(5)
        st.rerun()

else:
    # Modo de Análise Pós-Corrida via Upload de CSV.
    uploaded_file = st.sidebar.file_uploader("Upload de Stint (CSV)", type="csv")
    if uploaded_file:
        df_history = pd.read_csv(uploaded_file)
        st.success(f"Analisando Sessão: {uploaded_file.name}")
        render_metrics(df_history)
    else:
        st.info("Faça o upload de um arquivo da pasta 'concluded_sessions' para analisar.")