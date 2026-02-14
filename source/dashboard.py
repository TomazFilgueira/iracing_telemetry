import streamlit as st
import pandas as pd
import glob
import os
from config import LOG_DIR

st.set_page_config(page_title="Strategy Deck", layout="wide")
st.title("🏎️ Real-Time Strategy Deck")

# Função para pegar o arquivo mais recente
files = glob.glob(str(LOG_DIR / "stint_*.csv"))
latest_file = max(files, key=os.path.getctime) if files else None

if latest_file:
    df = pd.read_csv(latest_file)
    if not df.empty:
        last = df.iloc[-1]
        
        # --- CHECKBOX PARA DADOS DA EQUIPE ---
        show_team = st.checkbox("Mostrar Detalhes da Equipe e Posição", value=True)
        
        if show_team:
            st.info(f"🚩 **Equipe:** {last['Equipe']} | **Posição Geral:** P{int(last['Pos_Geral'])} | **Posição na Classe:** P{int(last['Pos_Classe'])}")
            st.divider()

        # KPIs de Performance
        st.subheader("⏱️ Performance")
        k1, k2 = st.columns(2)
        k1.metric("Piloto Atual", last['Piloto'])
        k2.metric("Última Volta", f"{last['Tempo']:.3f}s")
        
        # KPIs de Combustível
        st.subheader("⛽ Estratégia")
        f1, f2 = st.columns(2)
        f1.metric("Tanque", f"{last['Combustivel_Restante']:.2f} L")
        f2.metric("Voltas Est.", f"{last['Voltas_Restantes_Estimadas']}")

        st.rerun()
else:
    st.warning("Aguardando dados...")