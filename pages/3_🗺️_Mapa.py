import streamlit as st
import folium
from folium.plugins import Draw, HeatMap
from streamlit_folium import st_folium
import sqlite3
import pandas as pd

st.set_page_config(page_title="Central Satélite", page_icon="🗺️", layout="wide")
ARQUIVO_DB = 'banco_lavoura.db'

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    .stApp { background-color: #F4F7F6; font-family: 'Inter', sans-serif !important; }
    .block-container { padding-top: 3.5rem !important; padding-bottom: 2rem !important;}
    header { background-color: #F4F7F6 !important; box-shadow: none !important; }
    footer, [data-testid="stToolbar"], #MainMenu { display: none !important; }
    
    .top-header {
        background: linear-gradient(135deg, #1A3626 0%, #2E7D32 100%);
        padding: 30px; border-radius: 16px; margin-bottom: 25px;
        color: white; box-shadow: 0 8px 20px rgba(46, 125, 50, 0.15);
    }
    .top-header h1 { margin: 0; font-size: 28px !important; font-weight: 700; color: white !important;}
    .top-header p { margin: 0; color: #A5D6A7 !important; font-size: 16px; }
    
    .card-panel {
        background: #FFFFFF; border-radius: 16px; padding: 25px; height: 100%;
        border: 1px solid #EBEFEB; box-shadow: 0px 4px 16px rgba(0, 0, 0, 0.03);
    }
    .card-title { font-size: 18px; font-weight: 700; color: #1A3626; margin-bottom: 20px; border-bottom: 2px solid #F4F7F6; padding-bottom: 10px;}
    
    .stButton>button {
        background-color: #2E7D32 !important; color: white !important; border-radius: 8px !important; font-weight: 600 !important;
        padding: 10px 24px !important; border: none !important; width: 100%; transition: all 0.2s;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 6px 12px rgba(46, 125, 50, 0.2) !important; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="top-header"><h1>🗺️ Central Espacial</h1><p>Monitoramento NDVI e Desenho de Talhões</p></div>', unsafe_allow_html=True)

chave_agro_padrao = st.secrets.get("AGRO_API_KEY", "")

with st.sidebar:
    st.header("🛰️ Conexão Sentinel-2")
    agro_key = st.text_input("Agromonitoring API Key:", value=chave_agro_padrao, type="password")
    if agro_key: st.success("Ligação satelital ativa!")

def garantir_tabela():
    conn = sqlite3.connect(ARQUIVO_DB)
    conn.cursor().execute('''CREATE TABLE IF NOT EXISTS talhoes_geometria (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, cultura TEXT, coordenadas TEXT)''')
    conn.commit()
    conn.close()

garantir_tabela()

col_mapa, col_painel = st.columns([2.5, 1])

with col_mapa:
    st.markdown('<div class="card-panel">', unsafe_allow_html=True)
    LAT, LON = -19.6389, -54.5981
    m = folium.Map(location=[LAT, LON], zoom_start=14, control_scale=True)
    folium.TileLayer(tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', attr='Google', name='Google Satellite', max_zoom=20).add_to(m)
    
    draw = Draw(export=True, position='topleft', draw_options={'polyline': False, 'polygon': True, 'circle': False, 'marker': False, 'circlemarker': False, 'rectangle': True})
    draw.add_to(m)

    conn = sqlite3.connect(ARQUIVO_DB)
    try:
        df_geo = pd.read_sql_query("SELECT nome, cultura, coordenadas FROM talhoes_geometria", conn)
        for _, row in df_geo.iterrows():
            folium.Polygon(locations=eval(row['coordenadas']), color="#2E7D32", weight=3, fill=True, fill_color="#2E7D32", fill_opacity=0.2, tooltip=f"{row['nome']}").add_to(m)
    except: pass
    conn.close()

    output = st_folium(m, width="100%", height=600, returned_objects=["last_active_drawing"])
    st.markdown('</div>', unsafe_allow_html=True)

with col_painel:
    st.markdown('<div class="card-panel"><div class="card-title">💾 Guardar Desenho</div>', unsafe_allow_html=True)
    with st.form("form_mapa"):
        nome_talhao = st.text_input("Nome do Talhão:", placeholder="Ex: Talhão 01 - Sede")
        cultura_talhao = st.selectbox("Cultura:", ["Soja", "Milho Safrinha", "Sorgo"])
        salvar = st.form_submit_button("Guardar Polígono")
        
        if salvar:
            desenho = output.get("last_active_drawing")
            if desenho and desenho["geometry"]["type"] == "Polygon":
                coords = [[c[1], c[0]] for c in desenho["geometry"]["coordinates"][0]]
                conn = sqlite3.connect(ARQUIVO_DB)
                conn.cursor().execute("INSERT INTO talhoes_geometria (nome, cultura, coordenadas) VALUES (?, ?, ?)", (nome_talhao, cultura_talhao, str(coords)))
                conn.commit()
                conn.close()
                st.success("Guardado na base de dados!")
                st.rerun()
            else:
                st.warning("Desenhe um polígono no mapa primeiro.")
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="card-panel" style="margin-top:20px;"><div class="card-title">🛰️ Imagens Recentes</div>', unsafe_allow_html=True)
    if agro_key: 
        st.info("Sincronizando com Sentinel-2 ESA...")
        st.button("Baixar NDVI Atualizado")
    else: 
        st.write("Insira a chave da API no menu lateral para descarregar o histórico de NDVI.")
    st.markdown('</div>', unsafe_allow_html=True)