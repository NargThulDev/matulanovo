import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import os

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Matula - Dashboard", page_icon="🌱", layout="wide")
os.makedirs('fotos_app', exist_ok=True)
ARQUIVO_DB = 'banco_lavoura.db'

# --- CSS PREMIUM E RESPONSIVO ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    .stApp { background-color: #F4F7F6; font-family: 'Inter', sans-serif !important; }
    
    .block-container { padding-top: 3.5rem !important; padding-bottom: 2rem !important; }
    header { background-color: #F4F7F6 !important; box-shadow: none !important; }
    footer, [data-testid="stToolbar"], #MainMenu { display: none !important; }
    
    .top-header {
        background: linear-gradient(135deg, #1A3626 0%, #2E7D32 100%);
        padding: 30px; border-radius: 16px; margin-bottom: 30px;
        color: white; box-shadow: 0 8px 20px rgba(46, 125, 50, 0.15);
        display: flex; justify-content: space-between; align-items: center;
    }
    .top-header h1 { margin: 0; font-size: 28px !important; font-weight: 700; color: white !important;}
    .top-header p { margin: 0; color: #A5D6A7 !important; font-size: 16px; }
    
    .kpi-container { display: flex; gap: 20px; margin-bottom: 30px; flex-wrap: wrap; }
    .kpi-card {
        background: #FFFFFF; border-radius: 16px; padding: 20px; flex: 1; min-width: 200px;
        border: 1px solid #EBEFEB; box-shadow: 0px 4px 16px rgba(0, 0, 0, 0.03);
        border-left: 5px solid #2E7D32; transition: transform 0.2s;
    }
    .kpi-card:hover { transform: translateY(-3px); }
    .kpi-title { font-size: 14px; color: #6B7280; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 5px;}
    .kpi-value { font-size: 32px; font-weight: 700; color: #1A3626; margin: 0;}
    
    .card-panel {
        background: #FFFFFF; border-radius: 16px; padding: 25px; height: 100%;
        border: 1px solid #EBEFEB; box-shadow: 0px 4px 16px rgba(0, 0, 0, 0.03);
    }
    .card-title { font-size: 18px; font-weight: 700; color: #1A3626; margin-bottom: 20px; border-bottom: 2px solid #F4F7F6; padding-bottom: 10px;}
    </style>
""", unsafe_allow_html=True)

# --- BANCO DE DADOS ---
def iniciar_banco():
    conn = sqlite3.connect(ARQUIVO_DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS talhoes (id INTEGER PRIMARY KEY, nome TEXT, cultura TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS apontamentos (
                 id INTEGER PRIMARY KEY, talhao_id INTEGER, tipo TEXT, 
                 detalhes TEXT, foto_path TEXT, data_hora DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('SELECT COUNT(*) FROM talhoes')
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO talhoes (nome, cultura) VALUES ('Talhão 01 - Sede', 'Soja')")
        c.execute("INSERT INTO talhoes (nome, cultura) VALUES ('Talhão 02 - Fundo', 'Milho Safrinha')")
    conn.commit()
    conn.close()

iniciar_banco()

# --- EXTRAÇÃO DE DADOS PARA O DASHBOARD ---
conn = sqlite3.connect(ARQUIVO_DB)
total_apontamentos = pd.read_sql_query("SELECT COUNT(*) as count FROM apontamentos", conn).iloc[0]['count']
total_talhoes = pd.read_sql_query("SELECT COUNT(*) as count FROM talhoes", conn).iloc[0]['count']
df_registros = pd.read_sql_query('''
    SELECT t.nome as Talhão, a.tipo as Tipo, a.data_hora as Data, a.detalhes as Detalhes 
    FROM apontamentos a JOIN talhoes t ON a.talhao_id = t.id 
    ORDER BY a.data_hora DESC LIMIT 8
''', conn)
df_grafico = pd.read_sql_query('''
    SELECT substr(tipo, 1, instr(tipo || ' ', ' ') - 1) as Categoria, COUNT(*) as Quantidade 
    FROM apontamentos GROUP BY Categoria
''', conn)
conn.close()

if not df_registros.empty:
    df_registros['Data'] = pd.to_datetime(df_registros['Data']).dt.strftime('%d/%m/%Y %H:%M')

# --- HEADER EXECUTIVO ---
st.markdown("""
    <div class="top-header">
        <div>
            <h1>🌱 Matula Visão Geral</h1>
            <p>Painel de Controle e Monitoramento de Safra</p>
        </div>
        <div style="text-align: right;">
            <span style="background: rgba(255,255,255,0.2); padding: 8px 15px; border-radius: 20px; font-size: 14px; font-weight: 600;">Safra 26/27</span>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- CARTÕES DE MÉTRICAS (KPIs) ---
st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-card">
            <div class="kpi-title">Talhões Ativos</div>
            <div class="kpi-value">{total_talhoes}</div>
        </div>
        <div class="kpi-card" style="border-left-color: #F59E0B;">
            <div class="kpi-title">Registros na Safra</div>
            <div class="kpi-value">{total_apontamentos}</div>
        </div>
        <div class="kpi-card" style="border-left-color: #3B82F6;">
            <div class="kpi-title">Última Atualização</div>
            <div class="kpi-value" style="font-size: 22px; line-height: 1.5;">{df_registros.iloc[0]['Data'][:10] if not df_registros.empty else 'N/A'}</div>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- ÁREA DE GRÁFICOS E TABELAS ---
col1, col2 = st.columns([1, 2])

with col1:
    st.markdown('<div class="card-panel"><div class="card-title">📊 Distribuição de Atividades</div>', unsafe_allow_html=True)
    if not df_grafico.empty:
        fig = px.pie(df_grafico, values='Quantidade', names='Categoria', hole=0.6, 
                     color_discrete_sequence=['#2E7D32', '#F59E0B', '#3B82F6', '#EF4444', '#8B5CF6'])
        fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), showlegend=True, 
                          legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    else:
        st.info("Nenhum dado suficiente para gerar gráficos.")
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="card-panel"><div class="card-title">📝 Últimas Movimentações Operacionais</div>', unsafe_allow_html=True)
    if not df_registros.empty:
        st.dataframe(
            df_registros, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Talhão": st.column_config.TextColumn("Local"),
                "Tipo": st.column_config.TextColumn("Categoria", width="medium"),
                "Data": st.column_config.TextColumn("Data/Hora"),
                "Detalhes": st.column_config.TextColumn("Resumo do Apontamento", width="large")
            }
        )
    else:
        st.write("Nenhum registro encontrado no banco de dados.")
    st.markdown('</div>', unsafe_allow_html=True)