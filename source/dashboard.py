import streamlit as st
import pandas as pd
import glob
import os
import time
from config import LOG_DIR, REFRESH_RATE_ST

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Strategy & Analysis Deck", layout="wide")

def get_latest_file():
    files = glob.glob(str(LOG_DIR / "stint_*.csv"))
    return max(files, key=os.path.getctime) if files else None

def render_metrics(df, is_live=True):
    """Função reutilizável para renderizar os KPIs e Gráficos"""
    if df.empty:
        st.warning("O arquivo selecionado está vazio.")
        return

    last = df.iloc[-1]
    
    # --- CHECKBOX DE EQUIPE ---
    show_team = st.checkbox("Mostrar Detalhes da Equipe e Posição", value=True)
    if show_team and 'Equipe' in df.columns:
        st.info(f"🚩 **Equipe:** {last['Equipe']} | **Posição Classe:** P{int(last['Pos_Classe'])}")
        st.divider()

    # Seleção de Piloto (Importante para Endurance)
    piloto = st.selectbox("Selecione o Piloto", sorted(df['Piloto'].unique()))
    df_p = df[df['Piloto'] == piloto].copy()
    last_p = df_p.iloc[-1]

    # --- PERFORMANCE ---
    st.subheader("⏱️ Performance de Volta")
    c1, c2, c3 = st.columns(3)
    c1.metric("Última Volta", f"{last_p['Tempo']:.3f}s")
    c2.metric("Melhor Volta", f"{df_p['Tempo'].min():.3f}s")
    c3.metric("Consistência (Desvio Padrão)", f"{df_p['Tempo'].std():.3f}s")

    st.divider()

    # --- ESTRATÉGIA ---
    st.subheader("⛽ Gestão de Combustível")
    f1, f2, f3 = st.columns(3)
    f1.metric("Consumo Médio", f"{df_p['Consumo_Volta'].mean():.3f} L")
    f2.metric("Tanque Final", f"{last_p['Combustivel_Restante']:.2f} L")
    f3.metric("Voltas Est. no Stint", f"{len(df_p)}")

    # --- GRÁFICOS ---
    st.divider()
    st.subheader("📈 Análise de Ritmo")
    st.line_chart(df_p, x='Volta', y='Tempo', width="stretch")

# --- INTERFACE PRINCIPAL ---
st.title("🏎️ Real-Time Strategy & Analysis")

# Sidebar para Upload e Modo de Operação
st.sidebar.header("🛠️ Configurações")
app_mode = st.sidebar.radio("Modo do Dashboard", ["📡 Live Telemetry", "📂 Post-Race Analysis"])

if app_mode == "📂 Post-Race Analysis":
    uploaded_file = st.sidebar.file_uploader("Upload de Stint (CSV)", type="csv")
    if uploaded_file is not None:
        df_uploaded = pd.read_csv(uploaded_file)
        st.success(f"Analisando: {uploaded_file.name}")
        render_metrics(df_uploaded, is_live=False)
    else:
        st.info("Por favor, faça o upload de um arquivo CSV da pasta 'concluded_sessions' para começar.")

else:
    # MODO LIVE
    latest_file = get_latest_file()
    if latest_file:
        st.caption(f"📡 Monitorando: {os.path.basename(latest_file)}")
        df_live = pd.read_csv(latest_file)
        render_metrics(df_live, is_live=True)
        time.sleep(REFRESH_RATE_ST)
        st.rerun()
    else:
        st.warning("Nenhuma telemetria ativa detectada em Data_Logs. Inicie o coletor ou mude para o modo de Análise.")