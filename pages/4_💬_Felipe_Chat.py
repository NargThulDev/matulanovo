import streamlit as st
import google.generativeai as genai
import sqlite3
import pandas as pd
from gtts import gTTS
import io
import re

st.set_page_config(page_title="Chat com Felipe", page_icon="💬", layout="centered")
ARQUIVO_DB = 'banco_lavoura.db'

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    .stApp { background-color: #F4F7F6; font-family: 'Inter', sans-serif !important; }
    .block-container { max-width: 950px !important; padding-top: 3.5rem !important; padding-bottom: 5rem !important; }
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
    
    .stChatMessage { background-color: #FFFFFF; border-radius: 12px; padding: 20px; border: 1px solid #EBEFEB; box-shadow: 0 2px 8px rgba(0,0,0,0.02); margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="top-header"><h1>💬 Consultoria Integrada</h1><p>Análise inteligente por texto e voz com base no histórico da lavoura</p></div>', unsafe_allow_html=True)

chave_padrao = st.secrets.get("GEMINI_API_KEY", "")

with st.sidebar:
    st.header("🤖 Motor Felipe")
    api_key = st.text_input("API Key (Gemini):", value=chave_padrao, type="password", key="chat_key")
    if api_key: 
        st.success("🟢 Online e com acesso ao Banco de Dados")
    else: 
        st.warning("⚪ Operação Offline. Insira a chave para conversar.")
    
    voz_ativa = st.toggle("🔊 Ouvir resposta em voz", value=True)
    
    st.markdown("---")
    if st.button("Limpar Histórico da Conversa"):
        st.session_state.messages = []
        st.session_state.ultimo_audio = None
        st.rerun()

# --- FUNÇÃO DE SÍNTESE DE VOZ DO FELIPE ---
def falar_felipe(texto):
    try:
        # Remove caracteres de formatação Markdown para a leitura soar natural
        texto_limpo = re.sub(r'[*_#`~>-]', '', texto)
        tts = gTTS(text=texto_limpo, lang='pt', tld='com.br')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        st.audio(fp, format='audio/mp3', autoplay=True)
    except Exception as e:
        st.warning(f"Não foi possível gerar o áudio da resposta: {e}")

def carregar_contexto_fazenda():
    try:
        conn = sqlite3.connect(ARQUIVO_DB)
        
        try:
            df_talhoes = pd.read_sql_query("SELECT id, nome, cultura FROM talhoes", conn)
            str_talhoes = df_talhoes.to_string(index=False) if not df_talhoes.empty else "Nenhum talhão cadastrado."
        except:
            str_talhoes = "Tabela de talhões vazia ou inexistente."
            
        try:
            df_apontamentos = pd.read_sql_query('''
                SELECT t.nome as Talhao, a.tipo as Operacao, a.data_hora as Data, a.detalhes as Parametros 
                FROM apontamentos a 
                LEFT JOIN talhoes t ON a.talhao_id = t.id 
                ORDER BY a.data_hora DESC LIMIT 50
            ''', conn)
            str_apontamentos = df_apontamentos.to_string(index=False) if not df_apontamentos.empty else "Nenhum apontamento/operação registrada ainda."
        except:
            str_apontamentos = "Histórico de apontamentos vazio."
            
        conn.close()
        
        contexto = f"""
        --- TALHÕES E CULTURAS ATUAIS ---
        {str_talhoes}
        
        --- HISTÓRICO RECENTE DE OPERAÇÕES E MIP (Últimos 50 registros) ---
        {str_apontamentos}
        """
        return contexto
    except Exception as e:
        return f"Não foi possível aceder ao banco de dados no momento. Detalhe: {e}"

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Fala, pessoal! Felipe na área. Banco de dados sincronizado. Podem mandar mensagem de texto ou gravar um áudio que eu escuto e respondo daqui!"}
    ]

if "ultimo_audio" not in st.session_state:
    st.session_state.ultimo_audio = None

for message in st.session_state.messages:
    avatar = "felipe_avatar.png" if message["role"] == "assistant" else "🧑‍💻"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

# --- ÁREA DE GRAVAÇÃO DE VOZ ---
audio_gravado = st.audio_input("🎙️ Falar com o Felipe (Grave seu áudio):")

prompt_texto = st.chat_input("Ou digite sua dúvida sobre o histórico, dosagens e manejo...")

enviou_audio = audio_gravado is not None and audio_gravado != st.session_state.ultimo_audio

if prompt_texto or enviou_audio:
    if not api_key:
        st.error("Insira a chave da API no menu lateral para conversar.")
        st.stop()
        
    if enviou_audio:
        st.session_state.ultimo_audio = audio_gravado
        msg_usuario = "🎙️ *[Mensagem de voz enviada]*"
    else:
        msg_usuario = prompt_texto

    st.session_state.messages.append({"role": "user", "content": msg_usuario})
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(msg_usuario)
        if enviou_audio:
            st.audio(audio_gravado)

    with st.chat_message("assistant", avatar="felipe_avatar.png"):
        with st.spinner("Escutando e consultando o banco de dados..." if enviou_audio else "Consultando o banco de dados e analisando..."):
            try:
                genai.configure(api_key=api_key)
                dados_fazenda = carregar_contexto_fazenda()
                
                instrucao_gestor = f"""
                Você é o Felipe, agrônomo sênior e parceiro técnico desta fazenda.
                Você tem acesso imediato e irrestrito ao banco de dados SQLite do aplicativo Matula. 
                Sempre que o usuário fizer uma pergunta (por texto ou áudio), analise os dados reais da fazenda fornecidos abaixo para embasar sua resposta.
                
                DADOS DO BANCO DE DADOS LOCAL:
                {dados_fazenda}
                
                REGRAS DE ATUAÇÃO:
                1. Atue de forma natural e colaborativa. Não anuncie que você é um gestor ou sistema. Aja como um agrônomo trocando ideia.
                2. Se receber um áudio, escute com atenção, compreenda a dúvida ou relato de campo e responda diretamente.
                3. Analise as operações, critique erros de dosagem/clima se houver, e elogie acertos com base nos dados.
                4. Responda com exatidão consultando o histórico quando questionado sobre aplicações ou talhões.
                5. Mantenha o tom profissional, altamente técnico, focado em rentabilidade.
                6. Use marcadores e DESTAQUE EM NEGRITO nomes de produtos, talhões e alertas críticos.
                """
                
                model = genai.GenerativeModel(
                    'models/gemini-1.5-flash',
                    system_instruction=instrucao_gestor
                )
                
                history_gemini = []
                for msg in st.session_state.messages[:-1]:
                    role = "model" if msg["role"] == "assistant" else "user"
                    history_gemini.append({"role": role, "parts": [msg["content"]]})
                
                chat = model.start_chat(history=history_gemini)
                
                if enviou_audio:
                    bytes_audio = audio_gravado.getvalue()
                    pacote_audio = {"mime_type": audio_gravado.type or "audio/wav", "data": bytes_audio}
                    response = chat.send_message([
                        "Escute este áudio enviado pelo produtor/técnico no campo e responda de acordo com o contexto da fazenda:", 
                        pacote_audio
                    ])
                else:
                    response = chat.send_message(prompt_texto)
                
                st.markdown(response.text)
                if voz_ativa:
                    falar_felipe(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"Erro de comunicação: {e}")
