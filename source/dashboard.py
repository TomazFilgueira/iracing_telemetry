import streamlit as st
import os
import signal
import pandas as pd
import time
import glob
import os
from config import LOG_DIR, REFRESH_RATE_ST # Importa do config.py

st.set_page_config(page_title="CK Strategy", layout="wide")

def get_latest_file():
    files = glob.glob(str(LOG_DIR / "stint_*.csv"))
    return max(files, key=os.path.getctime) if files else None

st.title("🏎️ Real-Time Strategy")
latest_file = get_latest_file()

if latest_file:
    df = pd.read_csv(latest_file)
    if not df.empty:
        st.caption(f"📡 Arquivo Atual: {os.path.basename(latest_file)}")
        piloto = st.selectbox("Piloto", sorted(df['Piloto'].unique()))
        df_p = df[df['Piloto'] == piloto].copy()
        last = df_p.iloc[-1]
        
        # KPIs
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Última Volta (s)", f"{last['Tempo']:.3f}s")
        k2.metric("Média Últiumas 3 Voltas", f"{last['Media_3_Voltas']:.3f}s")
        k3.metric("Consumo Médio", f"{df_p['Consumo_Volta'].mean():.3f} L")
        k4.metric("Voltas Restantes", f"{last['Voltas_Restantes_Estimadas']:.1f}")

        # Gráficos de Consistência e Estacionariedade
        st.divider()
        st.subheader("Análise de Voltas")
        st.line_chart(df_p, x='Volta', y=['Tempo', 'Media_3_Voltas'], width="stretch")
        
        # Tabela
        st.dataframe(df_p.sort_values(by='Volta', ascending=False), width="stretch")

        time.sleep(REFRESH_RATE_ST)
        st.rerun()
else:
    st.warning("Aguardando gravação do primeiro log...")
    time.sleep(5)
    st.rerun()



# No final do seu código do dashboard:
if st.button("🔴 Encerrar Dashboard"):
    st.warning("Encerrando o servidor do Dashboard...")
    time.sleep(2)
    # Envia um sinal para o próprio processo se encerrar
    os.kill(os.getpid(), signal.SIGTERM)    