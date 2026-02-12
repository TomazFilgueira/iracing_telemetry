import streamlit as st
import pandas as pd
import time
import os
from pathlib import Path

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Racing4all Strategy", layout="wide")

# Caminho atualizado conforme sua solicitação
CSV_PATH = Path("C:/Users/to_fi/OneDrive/Documents/GitHub/MyProjects/iracing_telemetry/Data_Logs/stint_telemetry.csv")

def load_data():
    if CSV_PATH.exists():
        try:
            return pd.read_csv(CSV_PATH)
        except:
            return pd.DataFrame()
    return pd.DataFrame()

# --- INTERFACE ---
st.title("🏎️ Racing4all: Real-Time Strategy & Telemetry")

# Barra Lateral: Controles e Status
with st.sidebar:
    st.header("⚙️ Configurações")
    if st.button("🗑️ Limpar Dados do Stint"):
        if CSV_PATH.exists():
            os.remove(CSV_PATH)
            st.rerun()
    
    refresh_rate = st.slider("Taxa de Atualização (s)", 1, 10, 2)

df = load_data()

if not df.empty:
    # Filtro de Piloto
    pilotos_disponiveis = sorted(df['Piloto'].unique())
    piloto_selecionado = st.selectbox("Selecione o Piloto", pilotos_disponiveis, key="sb_piloto")
    
    df_p = df[df['Piloto'] == piloto_selecionado].copy()
    
    # --- DADOS DA ÚLTIMA VOLTA ---
    last_row = df_p.iloc[-1]
    
    # --- KPIs DE PERFORMANCE ---
    st.subheader("📊 Performance do Piloto")
    k1, k2, k3, k4 = st.columns(4)
    
    best_lap = df_p['Tempo'].min()
    avg_cons = df_p['Consumo_Volta'].mean()
    
    k1.metric("Última Volta", f"{last_row['Tempo']:.3f}s")
    k2.metric("Média (Últimas 3v)", f"{last_row['Media_3_Voltas']:.3f}s")
    k3.metric("Melhor Volta", f"{best_lap:.3f}s", 
              delta=f"{last_row['Tempo'] - best_lap:.3f}s", delta_color="inverse")
    k4.metric("Consumo Médio", f"{avg_cons:.3f} L")

    # --- ESTRATÉGIA DE COMBUSTÍVEL ---
    st.divider()
    st.subheader("⛽ Estratégia e Autonomia")
    s1, s2, s3, s4 = st.columns(4)
    
    # Cálculos de Projeção
    laps_rem = last_row['Voltas_Restantes_Estimadas']
    fuel_needed = laps_rem * avg_cons
    fuel_left = last_row['Combustivel_Restante']
    balance = fuel_left - fuel_needed
    
    # Tempo de Prova Formatado (mm:ss)
    time_rem_min = int(last_row['Tempo_Prova_Restante_s'] // 60)
    time_rem_sec = int(last_row['Tempo_Prova_Restante_s'] % 60)

    s1.metric("Tempo Restante", f"{time_rem_min:02d}:{time_rem_sec:02d}")
    s2.metric("Voltas p/ o Fim", f"{laps_rem:.1f}")
    s3.metric("Tanque Atual", f"{fuel_left:.2f} L")
    s4.metric("Balanço de Combustível", f"{balance:.2f} L", 
              delta=f"{balance:.2f} L", delta_color="normal")

    if balance < 0:
        st.error(f"⚠️ AVISO: Faltam aproximadamente {abs(balance):.2f} litros para terminar a prova!")
    else:
        st.success(f"✅ Combustível suficiente para o final da prova.")

    # --- GRÁFICOS ---
    st.divider()
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.subheader("Consistência: Tempo vs Média")
        # Gráfico comparando tempo real com a média móvel das últimas 3v
        st.line_chart(df_p, x='Volta', y=['Tempo', 'Media_3_Voltas'])

    with col_chart2:
        st.subheader("Consumo por Volta (L)")
        st.bar_chart(df_p, x='Volta', y='Consumo_Volta')

    # --- TABELA ---
    st.subheader("Log Completo")
    st.dataframe(df_p.sort_values(by='Volta', ascending=False), use_container_width=True)

    # Lógica de atualização
    time.sleep(refresh_rate)
    st.rerun()

else:
    st.info("Aguardando dados... Inicie o script de captura para alimentar o dashboard.")
    time.sleep(5)
    st.rerun()