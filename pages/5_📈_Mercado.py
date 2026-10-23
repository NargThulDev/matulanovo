import streamlit as st

st.set_page_config(page_title="Mercado e Cotações", page_icon="📈")

st.title("📈 Mercado e Cotações")
st.write("Módulo de internet desativado para garantir a execução local inicial.")

col1, col2 = st.columns(2)
col1.metric("Soja", "R$ --", "Offline")
col2.metric("Milho", "R$ --", "Offline")