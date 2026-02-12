import streamlit as st
import pandas as pd
import time
import glob
import os
from config import LOG_DIR, REFRESH_RATE_ST

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Strategy Deck", layout="wide")

def get_latest_file():
    files = glob.glob(str(LOG_DIR / "stint_*.csv"))
    return max(files, key=os.path.getctime) if files else None

st.title("🏎️ Real-Time Strategy Deck")

latest_file = get_latest_file()

if latest_file:
    df = pd.read_csv(latest_file)
    
    if not df.empty:
        st.caption(f"📡 Arquivo Atual: {os.path.basename(latest_file)}")
        
        # Seletor de Piloto
        piloto = st.selectbox("Piloto em Análise", sorted(df['Piloto'].unique()))
        df_p = df[df['Piloto'] == piloto].copy()
        last_row = df_p.iloc[-1]
        best_lap = df_p['Tempo'].min()

        # --- SEÇÃO 1: PERFORMANCE DE VOLTA ---
        st.subheader("⏱️ Performance de Volta")
        c1, c2, c3 = st.columns(3)
        
        c1.metric("Última Volta", f"{last_row['Tempo']:.3f}s")
        c2.metric("Média Móvel (3v)", f"{last_row['Media_3_Voltas']:.3f}s")
        c3.metric("Melhor Volta", f"{best_lap:.3f}s", 
                  delta=f"{last_row['Tempo'] - best_lap:.3f}s", delta_color="inverse")

        # --- DIVISOR VISUAL FORTE ---
        st.divider()

        # --- SEÇÃO 2: ESTRATÉGIA DE COMBUSTÍVEL ---
        st.subheader("⛽ Estratégia de Combustível")
        
        # Cálculos de Projeção
        laps_rem = last_row['Voltas_Restantes_Estimadas']
        avg_cons = df_p['Consumo_Volta'].mean()
        fuel_left = last_row['Combustivel_Restante']
        balance = fuel_left - (laps_rem * avg_cons)

        f1, f2, f3, f4 = st.columns(4)
        f1.metric("Consumo Médio", f"{avg_cons:.3f} L")
        f2.metric("Tanque Atual", f"{fuel_left:.2f} L")
        f3.metric("Voltas Estimadas", f"{laps_rem:.1f}")
        f4.metric("Balanço Final", f"{balance:.2f} L", 
                  delta=f"{balance:.2f} L", delta_color="normal")

        # Alertas de Estratégia
        if balance < 0:
            st.error(f"⚠️ ALERTA: Faltam {abs(balance):.2f}L para terminar a prova!")
        elif balance < 2.0:
            st.warning(f"⚠️ Atenção: Margem de segurança baixa ({balance:.2f}L). Economize!")
        else:
            st.success(f"✅ Estratégia Segura. Margem de {balance:.2f}L.")

        # --- GRÁFICOS E DADOS ---
        st.divider()
        st.subheader("📈 Análise Visual")
        g1, g2 = st.columns(2)
        g1.line_chart(df_p, x='Volta', y=['Tempo', 'Media_3_Voltas'], width="stretch")
        g2.bar_chart(df_p, x='Volta', y='Consumo_Volta', width="stretch")

        # Recarregamento automático
        time.sleep(REFRESH_RATE_ST)
        st.rerun()

    else:
        st.info("Sessão iniciada. Aguardando a primeira volta...")
        time.sleep(5)
        st.rerun()
else:
    st.warning("Nenhum arquivo de log encontrado. Inicie o script de captura.")
    time.sleep(5)
    st.rerun()