import streamlit as st
import pandas as pd
import time
from pathlib import Path

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Racing4all Telemetry", layout="wide")

# Caminho do arquivo (mesmo que você definiu no script de captura)
CSV_PATH = Path("C:/Users/PC/Documents/GitHub/Racing4all/Iracing/Data_Logs/stint_telemetry.csv")

def load_data():
    if CSV_PATH.exists():
        df = pd.read_csv(CSV_PATH)
        # Garantir que o timestamp seja lido corretamente
        return df
    return pd.DataFrame()

# --- INTERFACE ---
st.title("🏎️ Racing4all: Real-Time Telemetry")
st.markdown("Monitoramento de performance e consumo para campeonatos iRacing.")

# Placeholder para o conteúdo que será atualizado
placeholder = st.empty()

while True:
    df = load_data()

    with placeholder.container():
        if not df.empty:
            # Filtro por Piloto (Preparado para múltiplos motoristas)
            pilotos_disponiveis = df['Piloto'].unique()
            col_filter, _ = st.columns([1, 3])
            with col_filter:
                piloto_selecionado = st.selectbox("Filtrar por Piloto", pilotos_disponiveis)
            
            # Dados do piloto selecionado
            df_p = df[df['Piloto'] == piloto_selecionado].copy()

            # --- KPIs (Métricas Principais) ---
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            
            last_lap = df_p['Tempo'].iloc[-1]
            avg_cons = df_p['Consumo'].mean()
            best_lap = df_p['Tempo'].min()
            total_laps = len(df_p)

            kpi1.metric(label="Última Volta", value=f"{last_lap:.3f}s")
            kpi2.metric(label="Melhor Volta", value=f"{best_lap:.3f}s", delta=f"{last_lap - best_lap:.3f}s", delta_color="inverse")
            kpi3.metric(label="Consumo Médio", value=f"{avg_cons:.3f} L")
            kpi4.metric(label="Total de Voltas", value=total_laps)

            # --- GRÁFICOS ---
            st.divider()
            col_chart1, col_chart2 = st.columns(2)

            with col_chart1:
                st.subheader("Evolução do Tempo de Volta")
                st.line_chart(df_p, x='Volta', y='Tempo')

            with col_chart2:
                st.subheader("Consumo de Combustível")
                st.bar_chart(df_p, x='Volta', y='Consumo')

            # --- TABELA DE DADOS ---
            st.subheader("Histórico do Stint")
            st.dataframe(df_p.sort_values(by='Volta', ascending=False), use_container_width=True)
            
        else:
            st.warning("Aguardando dados... Certifique-se de que o script de telemetria está rodando e gravando voltas.")

    # Atualiza a interface a cada 2 segundos
    time.sleep(2)