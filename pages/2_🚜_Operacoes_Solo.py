import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import google.generativeai as genai
from PIL import Image
from gtts import gTTS
import io
import re

st.set_page_config(page_title="Operações e Solo", page_icon="🚜", layout="centered")
ARQUIVO_DB = 'banco_lavoura.db'

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    .stApp { background-color: #F4F7F6; font-family: 'Inter', sans-serif !important; }
    .block-container { max-width: 950px !important; padding-top: 3.5rem !important; }
    header { background-color: #F4F7F6 !important; box-shadow: none !important; }
    footer, [data-testid="stToolbar"], #MainMenu { display: none !important; }
    
    .top-header {
        background: linear-gradient(135deg, #1A3626 0%, #2E7D32 100%);
        padding: 30px; border-radius: 16px; margin-bottom: 25px;
        color: white; box-shadow: 0 8px 20px rgba(46, 125, 50, 0.15);
        text-align: center;
    }
    .top-header h1 { margin: 0; font-size: 28px !important; font-weight: 700; color: white !important;}
    .top-header p { margin: 0; color: #A5D6A7 !important; font-size: 16px; }
    
    [data-testid="stForm"] { background-color: #FFFFFF; border-radius: 16px; padding: 25px; border: 1px solid #EBEFEB; box-shadow: 0px 4px 16px rgba(0, 0, 0, 0.03); }
    
    .stTabs [data-baseweb="tab-list"] { gap: 15px; border-bottom: 1px solid #EBEFEB; padding-bottom: 0; }
    .stTabs [data-baseweb="tab"] { 
        background-color: transparent !important; 
        border: none !important; 
        padding: 10px 5px !important; 
        color: #6B7280 !important; 
        font-weight: 500 !important;
    }
    .stTabs [aria-selected="true"] { 
        background-color: transparent !important; 
        border-bottom: 3px solid #2E7D32 !important; 
        color: #1A3626 !important; 
        font-weight: 700 !important; 
    }
    .stTabs button:focus, .stTabs button:focus-visible, .stTabs button:active {
        outline: none !important; box-shadow: none !important; background-color: transparent !important;
    }
    
    .stTextInput>div>div>input, .stSelectbox>div>div>div, .stTextArea>div>div>textarea, .stNumberInput>div>div>div>input {
        background-color: #FFFFFF !important; border-radius: 8px !important; border: 1.5px solid #EBEFEB !important; color: #1E1E1E !important;
    }
    .stButton>button {
        background-color: #2E7D32 !important; color: white !important; border-radius: 8px !important; font-weight: 600 !important;
        padding: 12px 24px !important; border: none !important; width: 100%; transition: all 0.2s; margin-top: 15px;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 6px 12px rgba(46, 125, 50, 0.2) !important; }
    .stChatMessage { background-color: #FFFFFF; border-radius: 12px; padding: 20px; border: 1px solid #E0E5E2; box-shadow: 0 2px 8px rgba(0,0,0,0.02); }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="top-header"><h1>🚜 Máquinas & Solo</h1><p>Manejo de Pulverização, Fertilidade e Solo</p></div>', unsafe_allow_html=True)

chave_padrao = st.secrets.get("GEMINI_API_KEY", "")

with st.sidebar:
    st.header("🤖 Motor Felipe")
    api_key = st.text_input("API Key (Gemini):", value=chave_padrao, type="password", key="op_key")
    if api_key: st.success("🟢 Online e Analisando")
    else: st.warning("⚪ Operação Offline")
    voz_ativa = st.toggle("🔊 Ouvir parecer em voz", value=True)

def falar_felipe(texto):
    try:
        texto_limpo = re.sub(r'[*_#`~>-]', '', texto)
        tts = gTTS(text=texto_limpo, lang='pt', tld='com.br')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        st.audio(fp, format='audio/mp3', autoplay=True)
    except Exception as e:
        st.warning(f"Não foi possível gerar o áudio da resposta: {e}")

CATALOGO_PRODUTOS = {
    "Herbicida": ["Glyphosate (Glifosato)", "Clethodim", "2,4-D", "Atrazina", "Outro (Digitar)"],
    "Inseticida": ["Bifentrina", "Lambda-cialotrina", "Imidacloprid", "Outro (Digitar)"],
    "Fungicida": ["Azoxistrobina + Ciproconazol (Priori Xtra)", "Piraclostrobina + Epoxiconazol (Opera)", "Outro (Digitar)"],
    "Adubo Foliar": ["Boro (B)", "Manganês (Mn)", "Zinco (Zn)", "Outro (Digitar)"],
    "Óleo/Adjuvante": ["Óleo Mineral", "Óleo Vegetal", "Espalhante Siliconado", "Outro (Digitar)"],
    "Outro": ["Outro (Digitar)"]
}

def conselheiro_aplicacao(temp, umidade, vento, equipamento):
    alertas = []; status = "success"
    if temp > 30: alertas.append("⚠️ Temperatura Elevada: Evaporação rápida da gota."); status = "warning"
    elif temp < 12: alertas.append("ℹ️ Temperatura Baixa: Absorção muito lenta pelo metabolismo da planta.")
    if umidade < 50: alertas.append("🔴 Umidade Crítica: UR < 50% resseca gotas finas antes de atingirem o alvo."); status = "error"
    if vento > 10: alertas.append("🔴 Risco de Deriva Severa: Vento forte pode deslocar o produto."); status = "error"
    if vento < 3 and equipamento != "Drone Agrícola": alertas.append("🟡 Risco de Inversão Térmica: Gotas pequenas suspensas."); status = "warning" if status != "error" else "error"
    
    if not alertas: return "🟢 CONDIÇÕES CLIMÁTICAS IDEAIS", "Janela de aplicação com Delta T ótimo.", "success"
    if status == "error": return "🔴 ALERTA DE PERDA DE EFICIÊNCIA", "\n\n".join(alertas), "error"
    return "🟡 ATENÇÃO NA APLICAÇÃO", "\n\n".join(alertas), "warning"

def conselheiro_adubacao(tipo_insumo, metodo, umidade_solo, textura, chuva, taxa):
    alertas = []; status = "success"
    if "Nitrogênio" in tipo_insumo or "Ureia" in tipo_insumo:
        if "Seco" in umidade_solo and "Sem previsão" in chuva:
            alertas.append("🔴 Risco Máximo de Volatilização: Ureia em solo seco sem chuva a caminho. Use inibidor de urease."); status = "error"
            
    if textura == "Arenoso (Leve)":
        if "Chuva Forte" in chuva and ("Nitrogênio" in tipo_insumo or "Potássico" in tipo_insumo):
            alertas.append("🔴 Risco de Lixiviação: Solo arenoso não segura N e K sob chuva forte."); status = "error"
        else:
            alertas.append("🟡 Atenção à CTC: Solos arenosos exigem maior parcelamento."); status = "warning" if status != "error" else "error"
            
    if "Calcário" in tipo_insumo and "lanço (Sem incorporação)" in metodo:
        alertas.append("🟡 Reação Lenta: Calcário em superfície desce muito pouco no perfil."); status = "warning" if status != "error" else "error"

    if not alertas: return "🟢 CONDIÇÕES ADEQUADAS", "Janela nutricional e climática excelentes.", "success"
    if status == "error": return "🔴 ALERTA DE PERDA DE INSUMO", "\n\n".join(alertas), "error"
    return "🟡 ATENÇÃO NO MANEJO", "\n\n".join(alertas), "warning"

def conselheiro_solo(estagio, umidade, compactacao, palhada, erosao):
    alertas = []; status = "success"
    if umidade == "Pó / Muito Seco": alertas.append("🔴 Solo extremamente seco, sem umidade."); status = "error"
    if "Severa" in compactacao: alertas.append("🔴 Compactação severa limitando crescimento radicular e infiltração de água."); status = "error"
    if "Sulcos" in erosao or "Ravinas" in erosao: alertas.append("🔴 Perda de solo: Processo erosivo acelerado."); status = "error"
    
    if not alertas: return "🟢 SOLO CONSERVADO E APTO", "Estrutura, palhada e umidade ideais para a cultura.", "success"
    if status == "error": return "🔴 ALERTA DE DEGRADAÇÃO", "\n\n".join(alertas), "error"
    return "🟡 ATENÇÃO AO MANEJO DO SOLO", "\n\n".join(alertas), "warning"

with st.form("form_op", clear_on_submit=False):
    tab1, tab2, tab3 = st.tabs(["1️⃣ Definição", "2️⃣ Parâmetros Técnicos", "3️⃣ Finalização"])
    
    tipo_produto = ""; produto_comercial = ""; dose = 0.0; unidade_dose = "L/ha"; temp_aplicacao = 25; umidade_aplicacao = 60; vento_aplicacao = 5; equipamento = ""; tipo_bico = ""; volume_calda = 100
    tipo_insumo = ""; insumo_comercial = ""; dose_adubo = 0.0; unid_adubo = "kg/ha"; metodo_aplicacao = ""; umidade_solo = "Friável"; textura_solo = "Textura Média"; previsao_chuva = "Sem previsão"; taxa_aplicacao = "Taxa Fixa"
    compactacao = "Ausente / Baixo"; palhada = "Boa Cobertura (>60%)"; erosao = "Nenhum"
    
    with tab1:
        colA, colB = st.columns(2)
        with colA: cultura = st.selectbox("Cultura:", ["Soja", "Milho Safrinha", "Sorgo"])
        with colB: tipo_selecionado = st.selectbox("Operação:", ["Aplicação / Pulverização", "Adubação / Correção", "Avaliação de Solo"])
        estagio_cultura = st.selectbox("Fase Fenológica:", ["Pré-plantio / Dessecação", "Inicial/Emergência", "Crescimento Vegetativo", "Florescimento", "Enchimento de Grãos", "Maturação"])
        
    with tab2:
        if tipo_selecionado == "Aplicação / Pulverização":
            c1, c2 = st.columns(2)
            with c1:
                tipo_produto = st.selectbox("Classe:", ["Herbicida", "Inseticida", "Fungicida", "Adubo Foliar", "Adjuvante"])
                opcoes_produto = CATALOGO_PRODUTOS.get(tipo_produto, ["Outro (Digitar)"])
                produto_sel = st.selectbox("Produto:", opcoes_produto)
                produto_comercial = st.text_input("Especificar Produto:") if produto_sel == "Outro (Digitar)" else produto_sel
                dose = st.number_input("Dose:", 0.0, step=0.1)
                unidade_dose = st.selectbox("Unid:", ["L/ha", "kg/ha", "g/ha"])
            with c2:
                equipamento = st.selectbox("Máquina:", ["Autopropelido", "Tratorizado", "Drone", "Costal"])
                tipo_bico = st.selectbox("Bico:", ["Cone Vazio", "Leque Padrão", "Indução de Ar", "Rotativo"])
                temp_aplicacao = st.number_input("Temp(°C):", value=25)
                umidade_aplicacao = st.number_input("UR(%):", value=60)
                vento_aplicacao = st.number_input("Vento(km/h):", value=5)
                
        elif tipo_selecionado == "Adubação / Correção":
            c1, c2 = st.columns(2)
            with c1:
                taxa_aplicacao = st.radio("Tecnologia:", ["Taxa Fixa", "Taxa Variável (Mapa)"], horizontal=True)
                tipo_insumo = st.selectbox("Insumo:", ["Calcário", "NPK", "Ureia/Nitrogênio", "Fosfatado", "KCl"])
                insumo_comercial = st.text_input("Especificação (Ex: NPK 00-20-20):")
                dose_adubo = st.number_input("Dose/ha:", 0.0, step=10.0)
                unid_adubo = st.selectbox("Unid:", ["kg/ha", "ton/ha"])
            with c2:
                metodo_aplicacao = st.selectbox("Método:", ["A lanço (Sem incorp.)", "Linha de plantio", "Cobertura"])
                textura_solo = st.selectbox("Textura:", ["Argiloso", "Textura Média", "Arenoso (Leve)"])
                umidade_solo = st.selectbox("Umidade Atual:", ["Seco", "Friável", "Encharcado"])
                previsao_chuva = st.selectbox("Chuva Próx. 48h:", ["Sem previsão", "Garoa (<15mm)", "Forte (>15mm)"])
                
        elif tipo_selecionado == "Avaliação de Solo":
            c1, c2 = st.columns(2)
            with c1:
                umidade_solo = st.selectbox("Umidade:", ["Seco/Pó", "Friável", "Barro/Encharcado"])
                compactacao = st.selectbox("Compactação:", ["Ausente / Baixo", "Leve", "Severa (Raiz torta)"])
            with c2:
                palhada = st.selectbox("Palhada:", ["Boa Cobertura (>60%)", "Parcial", "Solo Descoberto"])
                erosao = st.selectbox("Erosão:", ["Nenhum", "Erosão Laminar", "Sulcos/Ravinas"])

    with tab3:
        conn = sqlite3.connect(ARQUIVO_DB)
        try:
            talhoes = pd.read_sql_query("SELECT id, nome FROM talhoes", conn)
            mapa_t = dict(zip(talhoes['nome'], talhoes['id'])) if not talhoes.empty else {"Geral": 1}
        except:
            mapa_t = {"Geral": 1}
        conn.close()
        
        talhao_escolhido = st.selectbox("Local:", list(mapa_t.keys()))
        anotacoes = st.text_area("Observações Escritas:")
        audio_obs = st.audio_input("🎙️ Gravar Observação por Voz (Opcional - O Felipe escuta!):")
        foto = st.camera_input("Foto Comprovativa (Opcional - O Felipe analisa se enviada!)")
        salvou = st.form_submit_button("Gerar Análise e Salvar")

if salvou:
    obs_resumo = anotacoes if anotacoes else ("Relato gravado por voz" if audio_obs else "Sem observações")
    if tipo_selecionado == "Aplicação / Pulverização": 
        tipo_final = f"Aplicação ({cultura}): {tipo_produto}"
        detalhes = f"Eqp: {equipamento} | Bico: {tipo_bico} | Clima: {temp_aplicacao}°C, {umidade_aplicacao}%, {vento_aplicacao}km/h | {produto_comercial} ({dose}{unidade_dose}) | Obs: {obs_resumo}"
        t_alerta, d_alerta, c_alerta = conselheiro_aplicacao(temp_aplicacao, umidade_aplicacao, vento_aplicacao, equipamento)
    elif tipo_selecionado == "Adubação / Correção":
        tipo_final = f"Adubação ({cultura}): {tipo_insumo}"
        detalhes = f"[{taxa_aplicacao}] {tipo_insumo}: {insumo_comercial} | Solo: {textura_solo} ({umidade_solo}) | Chuva: {previsao_chuva} | Obs: {obs_resumo}"
        t_alerta, d_alerta, c_alerta = conselheiro_adubacao(tipo_insumo, metodo_aplicacao, umidade_solo, textura_solo, previsao_chuva, taxa_aplicacao)
    else:
        tipo_final = f"Solo ({cultura})"
        detalhes = f"Solo: {umidade_solo} | Comp: {compactacao} | Erosão: {erosao} | Obs: {obs_resumo}"
        t_alerta, d_alerta, c_alerta = conselheiro_solo(estagio_cultura, umidade_solo, compactacao, palhada, erosao)
        
    st.markdown("---")
    if c_alerta == "error": st.error(f"**{t_alerta}**\n\n{d_alerta}")
    elif c_alerta == "warning": st.warning(f"**{t_alerta}**\n\n{d_alerta}")
    else: st.success(f"**{t_alerta}**\n\n{d_alerta}")

    if api_key:
        st.markdown("### 🤖 Parecer do Felipe")
        with st.chat_message("ai", avatar="felipe_avatar.png"):
            with st.spinner("Analisando dados operativos, fotos e áudio..."):
                try:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('models/gemini-3.5-flash')
                    
                    if tipo_selecionado == "Aplicação / Pulverização":
                        instrucao = "Avalie a termodinâmica (Delta T) do clima, o risco de deriva e a sinergia entre o bico escolhido e o produto. Sugira adição de adjuvantes apenas se o cenário climático ou o ativo realmente exigir."
                    else:
                        instrucao = "Foque na eficiência agronômica, redução de perdas financeiras no solo (volatilização/lixiviação) e qualidade do plantio direto."

                    prompt_felipe = f"""
                    Aja como Felipe, um agrônomo sênior de campo, experiente e colaborativo.
                    {instrucao}
                    
                    Cultura: {cultura} ({estagio_cultura}). Operação: {tipo_selecionado}. 
                    Dados: {detalhes}. Condição do laudo: {d_alerta}. Obs escrita: {anotacoes}. 
                    
                    REGRAS:
                    1. Saudação objetiva e parceira.
                    2. Divida em **DIAGNÓSTICO TÉCNICO** e **PLANO DE AÇÃO OPERACIONAL**.
                    3. Use marcadores.
                    4. Destaque em **NEGRITO E MAIÚSCULAS** adjuvantes, riscos severos ou pressões/regulagens.
                    5. Mantenha um tom profissional, direto e respeitoso. Sem arrogância.
                    """
                    
                    conteudo_enviado = [prompt_felipe]
                    if foto:
                        imagem_pil = Image.open(foto)
                        conteudo_enviado.append(imagem_pil)
                        conteudo_enviado[0] += "\n[ATENÇÃO: O utilizador anexou uma fotografia. Analise a imagem detalhadamente para complementar o seu diagnóstico operacional ou de solo.]"
                    
                    if audio_obs:
                        bytes_audio = audio_obs.getvalue()
                        pacote_audio = {"mime_type": audio_obs.type or "audio/wav", "data": bytes_audio}
                        conteudo_enviado.append(pacote_audio)
                        conteudo_enviado[0] += "\n[ATENÇÃO: O utilizador gravou um relato em áudio no campo. Escute o áudio e incorpore os detalhes operacionais relatados na sua análise.]"
                    
                    resposta_texto = model.generate_content(conteudo_enviado).text
                    st.write(resposta_texto)
                    if voz_ativa:
                        falar_felipe(resposta_texto)
                except Exception as e:
                    st.error(f"Felipe indisponível. Erro: {e}")

    caminho = None
    if foto:
        caminho = f"fotos_app/op_{datetime.now().strftime('%Y%m%d%H%M')}.jpg"
        with open(caminho, "wb") as f: f.write(foto.getbuffer())
    conn = sqlite3.connect(ARQUIVO_DB)
    conn.cursor().execute("INSERT INTO apontamentos (talhao_id, tipo, detalhes, foto_path) VALUES (?, ?, ?, ?)", (mapa_t.get(talhao_escolhido, 1), tipo_final, detalhes, caminho))
    conn.commit()
    conn.close()
    st.toast("Operação guardada no banco local!", icon='💾')