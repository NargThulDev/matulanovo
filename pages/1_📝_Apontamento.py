import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import google.generativeai as genai
from PIL import Image
from gtts import gTTS
import io
import re

st.set_page_config(page_title="Monitoramento Biológico", page_icon="🐛", layout="centered")
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

st.markdown('<div class="top-header"><h1>🐛 Controle Biológico</h1><p>MIP de Pragas, Doenças e Daninhas</p></div>', unsafe_allow_html=True)

chave_padrao = st.secrets.get("GEMINI_API_KEY", "")

with st.sidebar:
    st.header("🤖 Motor Felipe")
    api_key = st.text_input("API Key (Gemini):", value=chave_padrao, type="password", key="bio_key")
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

INFO_PRAGAS = {
    # SOJA
    "Percevejo-marrom (Euschistus heros)": {"dano": "Insere o estilete nas vagens e injeta toxinas. Causa abortamento, grãos chochos ou enrugados.", "id": "11-13mm. Marrom-escuro. Meia-lua branca no dorso."},
    "Percevejo-verde-pequeno (Piezodorus guildinii)": {"dano": "Injeta saliva altamente tóxica, causando retenção foliar e reduzindo qualidade da semente.", "id": "8-10mm. Verde-claro. Faixa transversal avermelhada no dorso."},
    "Percevejo-verde (Nezara viridula)": {"dano": "Perfura vagens em formação, favorecendo fungos nas sementes.", "id": "14-17mm. Verde-escuro intenso. Três pequenos pontos brancos no dorso."},
    "Percevejo-asa-preta (Edessa meditabunda)": {"dano": "Ataca hastes e ramos, sugando seiva. Dano menor nas vagens.", "id": "11-14mm. Corpo verde com asas na cor preta/marrom-escura."},
    "Percevejo-barriga-verde (Dichelops spp.) - Soja": {"dano": "Dano focado na sucção de seiva de hastes e vagens em estágios finais.", "id": "9-11mm. Dorso marrom, ventre verde. Cabeça com duas pontas agudas."},
    "Lagarta-da-soja (Anticarsia gemmatalis)": {"dano": "Consome limbo foliar, poupa nervuras. Reduz fotossíntese.", "id": "Até 40mm. Verde ou negra. 4 pares de pernas abdominais. Joga-se no chão quando tocada."},
    "Lagarta-falsa-medideira (Chrysodeixis includens)": {"dano": "Deixa a folha rendilhada. Fica no baixeiro da planta.", "id": "Até 35mm. Verde-clara. 2 pares de pernas falsas (anda medindo palmos)."},
    "Lagarta Helicoverpa (Helicoverpa armigera)": {"dano": "Ataca folhas, hastes, flores e vagens. Muito resistente a defensivos.", "id": "Até 40mm. Pelos finos e tubérculos escuros. Enrola-se em espiral."},
    "Lagarta-das-maçãs (Heliothis virescens)": {"dano": "Ataca ponteiros, flores e vagens.", "id": "Até 35mm. Verde/amarelada com estrias claras. Micro-espinhos escuros no corpo."},
    "Lagarta-preta (Spodoptera cosmioides)": {"dano": "Desfolhadora voraz. Ataca até vagens maduras.", "id": "Até 45mm. Preta/marrom-escura aveludada. Listras amareladas laterais."},
    "Lagarta-elasmo (Elasmopalpus lignosellus)": {"dano": "Penetra no colo da planta causando 'coração morto'.", "id": "15-20mm. Verde-azulada/avermelhada. Fica em casulo de terra na base da planta."},
    "Broca-das-axilas (Epinotia aporema)": {"dano": "Broqueia axilas das folhas e ponteiros, unindo folíolos com teia.", "id": "10-15mm. Branca-amarelada a rosada. Escondida no ponteiro."},
    "Tamanduá-da-soja (Sternechus subsignatus)": {"dano": "Adulto raspa a haste (desfiamento). Larva broqueia haste/raiz.", "id": "Adulto: Besouro bicudo de 8mm, preto com listras amarelas. Larva: Branca, sem pernas."},
    "Mosca-branca (Bemisia tabaci)": {"dano": "Excreta honeydew (fumagina). Vetor de viroses.", "id": "1-2mm. Inseto alado, corpo amarelado coberto com pó ceroso branco."},
    "Ácaro-rajado (Tetranychus urticae)": {"dano": "Bronzeamento foliar e desfolha precoce. Agravado em secas.", "id": "0,5mm. Esverdeado com duas manchas escuras no dorso. Forma teias."},
    "Ácaro-branco (Polyphagotarsonemus latus)": {"dano": "Causa encarquilhamento foliar e engrossamento de nervuras.", "id": "0,2mm. Translúcido a branco brilhante. Não tece teia."},
    "Ácaro-vermelho (Tetranychus ludeni)": {"dano": "Pontuações claras que evoluem para amarelecimento foliar.", "id": "0,5mm. Vermelho intenso e brilhante. Tece pequena quantidade de teia."},
    "Tripes (Frankliniella schultzei)": {"dano": "Raspa folhas (aspecto prateado). Transmite queima-do-broto.", "id": "1-2mm. Corpo alongado, amarelado, marrom ou preto. Muito rápido."},
    "Coró-da-soja (Phyllophaga cuyabana)": {"dano": "Larva de solo que consome raízes em reboleiras.", "id": "Larva branca (bicho-bolo) em 'C', cabeça marrom, 3 pares de pernas."},
    "Piolho-de-cobra / Embuá (Julida)": {"dano": "Ataca sementes e raízes de plântulas.", "id": "20-50mm. Corpo cilíndrico rígido (parece mola) com dezenas de pernas."},
    # MILHO SAFRINHA
    "Cigarrinha-do-milho (Dalbulus maidis)": {"dano": "Vetor de molicutes (enfezamento). Atrofia o milho e impede formação da espiga.", "id": "3-4mm. Cor palha. Duas manchas negras circulares na cabeça."},
    "Lagarta-do-cartucho (Spodoptera frugiperda)": {"dano": "Destrói o cartucho do milho. Pode perfurar a espiga.", "id": "Até 40mm. Y invertido branco na cabeça e 4 pontos escuros em quadrado no abdômen."},
    "Percevejo-barriga-verde (Dichelops spp.) - Milho": {"dano": "Perfura a base da plântula. Causa 'encharutamento' e morte do perfilho.", "id": "9-11mm. Dorso marrom, ventre verde vivo."},
    "Lagarta-da-espiga (Helicoverpa zea)": {"dano": "Penetra na espiga, destruindo grãos do topo.", "id": "Até 40mm. Listras longitudinais claras e escuras, microespinhas ásperas."},
    "Lagarta-rosca (Agrotis ipsilon)": {"dano": "Corta plântulas rente ao chão à noite.", "id": "Até 45mm. Cinza-escura/marrom. Fica enrolada enterrada próxima à planta de dia."},
    "Lagarta-elasmo (Elasmopalpus lignosellus) - Milho": {"dano": "Perfura o colmo ('coração morto'). Comum em solo arenoso.", "id": "Lagarta saltitante verde-azulada. Constrói tubo de terra na entrada do colmo."},
    "Larva-alfinete (Diabrotica speciosa)": {"dano": "Destrói raízes adventícias (acamamento / pescoço de ganso).", "id": "Larva fina, cilíndrica, branca-amarelada. 10-15mm."},
    "Coró-do-milho (Liogenys spp.)": {"dano": "Larva de solo. Mastiga sistema radicular jovem em reboleiras.", "id": "Branca em 'C' com cabeça marrom e traseira dilatada escura (terra translúcida)."},
    "Pulgão-do-milho (Rhopalosiphum maidis)": {"dano": "Suga seiva em cartuchos e pendões. Atrai fumagina.", "id": "2mm. Corpo mole, formato de pêra, verde-azulada escura a preta. Vivem em colônias."},
    "Broca-do-colmo (Diatraea saccharalis) - Milho": {"dano": "Broqueia colmo, causando tombamento.", "id": "Até 25mm. Lagarta branco-amarelada com pintas escuras (verrugas)."},
    "Tripes (Frankliniella spp.)": {"dano": "Raspa epiderme (V2-V5). Folhas esbranquiçadas que podem enrolar.", "id": "1-2mm. Corpo alongado (parece traço). Ficam no cartucho de plantas jovens."},
    "Formiga-saúva (Atta spp.)": {"dano": "Cortam intensamente folhas jovens. Desfolham bordaduras.", "id": "Formigas grandes. Soldado com cabeça muito grande. Cortes em meia-lua."},
    "Formiga-quemquém (Acromyrmex spp.)": {"dano": "Cortam pedaços menores de plantas novas.", "id": "Mais de três pares de espinhos no dorso do tórax."},
    "Cupim-de-montículo (Procornitermes spp.)": {"dano": "Ataca sementes e raízes em solos secos com palhada.", "id": "Insetos sociais esbranquiçados de corpo mole."},
    "Besouro-saltador / Larva-arame (Conoderus spp.)": {"dano": "Larva perfura sementes e raízes.", "id": "Larva fina e muito dura (arame), amarelada. Adulto dá 'saltos' (cliques)."},
    "Bicho-bolo (Cyclocephala spp.)": {"dano": "Consome raízes superficiais.", "id": "Coró em 'C', branco com cabeça marrom clara."},
    "Mosca-da-espiga (Euxesta spp.)": {"dano": "Larvas comem cabelos e grãos leitosos.", "id": "Mosca com asas transparentes possuindo faixas pretas. Larva branca/amarelada."},
    # SORGO
    "Mosca-do-sorgo (Stenodiplosis sorghicola)": {"dano": "A fêmea põe ovos nas flores; larvas destroem o ovário (panícula chocha).", "id": "2mm (parece mosquito). Vermelho-alaranjado vivo com asas transparentes."},
    "Pulgão-verde (Schizaphis graminum)": {"dano": "Injeta saliva tóxica (manchas avermelhadas). Reduz fotossíntese.", "id": "2mm. Verde-amarelada clara com listra verde-escura central no dorso."},
    "Pulgão-da-cana / Pulgão-amarelo (Melanaphis sacchari)": {"dano": "Multiplica rápido, produz muita fumagina, travando a colheita.", "id": "Cor amarelo a palha. Pontas das antenas e pernas na cor negra."},
    "Percevejo-do-sorgo (Thyanta spp.)": {"dano": "Sugador secundário na panícula.", "id": "8-10mm. Predominantemente verde, mas com margens do tórax avermelhadas."},
    "Coró-das-pastagens (Diloboderus abderus)": {"dano": "Consome raízes, definhando plantas em manchas.", "id": "Coró de grande porte (50mm). Cabeça vermelho-escura."},
    "Tripes-do-sorgo (Caliothrips spp.)": {"dano": "Raspa a folha (estrias prateadas). Seca pontas de plantas jovens.", "id": "Corpo afilado milimétrico, escuro (preto a marrom)."},
    "Cupim-de-raiz (Syntermes spp.)": {"dano": "Seca plântulas atacando raízes no cerrado.", "id": "Operários esbranquiçados, soldados com cabeças alaranjadas."},
    "Vaquinha-verde-amarela (Diabrotica speciosa) - Sorgo": {"dano": "Adulto mastiga folhas (pequenos furos).", "id": "Besourinho verde brilhante com 6 grandes manchas amarelas."},
    "Outra Praga (Não listada)": {"dano": "Dano a ser avaliado pelo técnico.", "id": "Preencher nas observações."}
}

INFO_DOENCAS = {
    # SOJA
    "Ferrugem-asiática (Phakopsora pachyrhizi)": {"dano": "Desfolha precoce severa. O fungo drena nutrientes e água, impedindo o enchimento de grãos.", "id": "Pústulas como pequenos 'vulcões' na face inferior da folha, cor castanha/escura."},
    "Mancha-alvo (Corynespora cassiicola)": {"dano": "Causa desfolha prematura. Atinge folhas, hastes e vagens.", "id": "Manchas circulares com anéis concêntricos (formato de alvo) e um ponto negro central."},
    "Antracnose (Colletotrichum truncatum)": {"dano": "Ataca desde a semente até a vagem. Causa vagens retorcidas/chochas.", "id": "Manchas deprimidas escuras (pontuações negras com setas que lembram espinhos)."},
    "Oídio (Microsphaera diffusa)": {"dano": "O fungo cobre a folha, bloqueando a luz do sol e reduzindo a fotossíntese.", "id": "Fina camada de pó branco a acinzentado sobre as folhas e hastes."},
    "Mancha-parda / Septoriose (Septoria glycines)": {"dano": "Uma das primeiras a aparecer. Amarelecimento e queda das folhas do baixeiro.", "id": "Pequenos pontos escuros angulares, delimitados pelas nervuras."},
    "Crestamento-foliar / Cercosporiose (Cercospora kikuchii)": {"dano": "Desfolha severa reprodutiva e mancha-púrpura nas sementes.", "id": "Folhas superiores com manchas vermelho-arroxeadas, aspecto de couro."},
    "Mofo-branco (Sclerotinia sclerotiorum)": {"dano": "Apodrece hastes e vagens. Forma estruturas de resistência (escleródios).", "id": "Crescimento semelhante a algodão branco nas hastes, com pedrinhas pretas."},
    "Podridão-radicular (Phytophthora sojae)": {"dano": "Morte em áreas com encharcamento.", "id": "Apodrecimento marrom-escuro que sobe da raiz até os primeiros nós da haste."},
    "Podridão-cinzenta-do-caule (Macrophomina phaseolina)": {"dano": "Morte prematura ('soja seca em pé'). Associada a seca.", "id": "Tecido cinzento com pontuações pretas minúsculas ao abrir a base da haste."},
    "Morte-súbita (Fusarium virguliforme)": {"dano": "Toxina sobe pela planta, causando necrose foliar fulminante.", "id": "Manchas amarelas entre nervuras que evoluem para necrose marrom."},
    # MILHO SAFRINHA
    "Complexo Enfezamento (Molicutes / Cigarrinha)": {"dano": "Entupimento vascular. A planta não cresce, espigas malformadas.", "id": "Vermelho: folhas avermelhadas nas bordas. Pálido: estrias brancas largas."},
    "Ferrugem-polissora (Puccinia polysora)": {"dano": "Destrói a área foliar verde muito rápido no terço médio e superior.", "id": "Pústulas pequenas, circulares e em grande quantidade, cor amarelo-ouro a dourada."},
    "Mancha-branca (Phaeosphaeria / Pantoea)": {"dano": "Reduz drasticamente a fotossíntese. Senescência antecipada.", "id": "Lesões iniciais aquosas que se tornam esbranquiçadas e arredondadas (1-2 cm)."},
    "Cercosporiose Milho (Cercospora zeae-maydis)": {"dano": "Seca o milho de baixo para cima.", "id": "Lesões cinza a marrons, alongadas e estritamente retangulares nas nervuras."},
    "Helmintosporiose (Exserohilum turcicum)": {"dano": "Necrose intensa de folhas. Comum com acúmulo de palha.", "id": "Lesões grandes elípticas, formato de 'charuto', palha com bordos escuros."},
    "Podridão-do-colmo (Fusarium / Colletotrichum)": {"dano": "Decompõe a medula do colmo. A planta tomba.", "id": "Colmo oco e descolorido. Rosada (Fusarium) ou preta brilhante (Antracnose)."},
    "Podridão-de-espiga (Fusarium verticillioides)": {"dano": "Destrói os grãos e produz micotoxinas.", "id": "Mofo branco a rosado sobre os grãos, partindo da ponta da espiga."},
    "Mancha-de-diplodia (Stenocarpella macrospora)": {"dano": "Progride da folha para apodrecer espigas e colmos.", "id": "Lesões foliares muito grandes, marrons com ponto claro no centro e pontinhos negros."},
    "Ferrugem-comum (Puccinia sorghi)": {"dano": "Reduz área fotossintética em climas amenos.", "id": "Pústulas alongadas, cor marrom-ferrugem a canela."},
    "Virose-da-risca (MRFV - Vetor: Cigarrinha)": {"dano": "Afeta o desenvolvimento geral e tamanho das espigas.", "id": "Pontinhos cloróticos alinhados nas nervuras foliares ('riscos' tracejados)."},
    # SORGO
    "Ferrugem-do-sorgo (Puccinia purpurea)": {"dano": "Acelera a maturação foliar e debilita a panícula.", "id": "Pústulas marrom-arroxeadas, circulares, que rompem a epiderme."},
    "Antracnose-do-sorgo (Colletotrichum sublineolum)": {"dano": "Ataca folhas, panículas e sementes.", "id": "Manchas circulares a elípticas com centro pardo e bordas arroxeadas."},
    "Doença-açucarada / Ergot (Claviceps africana)": {"dano": "Infecta o ovário da flor, impedindo a formação do grão.", "id": "Exsudação de líquido pegajoso (mel) que escorre das espiguetas."},
    "Mancha-zonada (Gloeocercospora sorghi)": {"dano": "Extensa necrose foliar em umidade.", "id": "Grandes lesões semi-circulares formando anéis alternados ('zonas')."},
    "Podridão-seca-do-colmo (Macrophomina phaseolina)": {"dano": "Colapso do colmo na fase de enchimento, levando a acamamento extremo.", "id": "Desintegração da medula folhando fibras intactas com pontuações pretas."},
    "Míldio-do-sorgo (Peronosclerospora sorghi)": {"dano": "Infeção sistêmica que esteriliza a planta.", "id": "Listras cloróticas paralelas. Penugem branca fina na face inferior no orvalho."},
    "Estria-bacteriana (Xanthomonas vasicola)": {"dano": "Redução fotossintética favorecida por ventos fortes.", "id": "Estrias estreitas e inter-nervais, vermelho-escuras."},
    "Outra Doença (Não listada)": {"dano": "Dano a ser avaliado pelo técnico.", "id": "Preencher nas observações."}
}

INFO_DANINHAS = {
    "Capim-amargoso (Digitaria insularis)": {"dano": "Gramínea perene, alta competição. Casos de resistência a Glifosato e ACCase.", "id": "Folhas pilosas, entouceiramento agressivo, inflorescência branca e plumosa."},
    "Buva (Conyza spp.)": {"dano": "Sementeira dispersa pelo vento. Alta resistência a Glifosato e ALS. Competição extrema inicial.", "id": "Caule ereto, folhas estreitas e pilosas. Crescimento em roseta no estágio inicial."},
    "Capim-pé-de-galinha (Eleusine indica)": {"dano": "Touceira espalmada. Casos de resistência múltipla. Rouba nutrientes rápido.", "id": "Hábito prostrado, hastes esbranquiçadas na base. Inflorescência lembra dedos de galinha."},
    "Caruru (Amaranthus spp.)": {"dano": "Crescimento explosivo, folha larga. Alerta máximo para Amaranthus palmeri.", "id": "Caule liso ou com espinhos, avermelhado na base. Inflorescência em espiga densa."},
    "Corda-de-viola (Ipomoea spp.)": {"dano": "Trepadeira. Enrola na cultura, causando quebra e travando a colheitadeira.", "id": "Folhas em formato de coração. Flores grandes em formato de funil (rosa, azul, branca)."},
    "Trapoeraba (Commelina benghalensis)": {"dano": "Tolera glifosato. Reproduz por rizomas e sementes (inclusive subterrâneas).", "id": "Folhas carnudas, caule suculento. Flor azul pequena. Raízes nos nós que tocam o solo."},
    "Leiteiro / Amendoim-bravo (Euphorbia heterophylla)": {"dano": "Sombreamento rápido da cultura. Alta taxa de infestação.", "id": "Folhas de formatos variados. Exsuda látex branco espesso quando o caule ou folha é quebrado."},
    "Picão-preto (Bidens pilosa)": {"dano": "Rápida propagação. Competição forte por luz e água.", "id": "Sementes em formato de agulhas com ganchos que grudam (carrapicho). Caule quadrangular."},
    "Milho-tiguera (Zea mays voluntário)": {"dano": "Competidor feroz na soja. Serve de ponte verde para cigarrinha e enfezamento.", "id": "Plantas de milho crescendo fora de época e alinhamento no meio da cultura atual."},
    "Soja-tiguera (Glycine max voluntária)": {"dano": "Ponte verde para ferrugem e outras doenças no milho ou pousio.", "id": "Plântulas de soja emergindo de grãos caídos na colheita anterior."},
    "Tiririca (Cyperus rotundus)": {"dano": "Extremamente agressiva, reprodução vegetativa subterrânea rápida.", "id": "Folhas estreitas e brilhantes. Caule triangular. Raiz forma cadeia de pequenos tubérculos escuros."},
    "Vassourinha-de-botão (Spermacoce verticillata)": {"dano": "Caule lenhoso, dificulta ação de herbicidas de contato.", "id": "Hábito subarbustivo, folhas dispostas em círculo no nó (verticiladas). Flores brancas em 'botão'."},
    "Capim-massambará (Sorghum halepense)": {"dano": "Perene, rizomatosa. Forte efeito alelopático (inibe crescimento de outras plantas).", "id": "Parece sorgo ou milho novo. Rizomas grossos e esbranquiçados no solo. Folhas largas."},
    "Guanxuma (Sida spp.)": {"dano": "Raiz pivotante profunda, rouba água das camadas inferiores.", "id": "Caule duro, quase lenhoso ('vassoura'). Folhas serrilhadas. Difícil arranque manual."},
    "Capim-colonião (Panicum maximum)": {"dano": "Crescimento agressivo, porte muito alto. Sombreia a cultura.", "id": "Gramínea robusta, touceiras grandes, folhas largas. Inflorescência grande e ramificada."},
    "Capim-carrapicho (Cenchrus echinatus)": {"dano": "Atrasa colheita, incomoda operadores e contamina grãos.", "id": "Folhas verdes claras, bainha avermelhada. Produz os famosos 'carrapichos' espinhosos."},
    "Maria-pretinha (Solanum americanum)": {"dano": "Frutos mancham os grãos da soja na colheita, gerando desconto na umidade e impureza.", "id": "Folhas verde-escuras. Produz pequenos frutos esféricos que ficam pretos brilhantes quando maduros."},
    "Apaga-fogo / Periquito (Alternanthera tenella)": {"dano": "Cobre o solo rapidamente em tapete, abafando plântulas.", "id": "Planta rasteira. Caule avermelhado e muito ramificado. Inflorescência como pequenas 'bolinhas' brancas."},
    "Nabiça / Fumo-bravo (Raphanus raphanistrum)": {"dano": "Crucífera agressiva no sul e safrinhas de inverno.", "id": "Folhas lobadas ásperas, caule com pelos rígidos. Flores amarelas em cruz."},
    "Aveia / Azevém voluntário": {"dano": "Matocompetição severa em áreas de transição inverno-verão no Sul.", "id": "Gramíneas de clima ameno que rebrotam ou nascem de sementes perdidas antes do plantio da soja."},
    "Outra Daninha (Não listada)": {"dano": "Dano a ser avaliado pelo técnico.", "id": "Preencher nas observações."}
}

def conselheiro_geral(cultura, estagio, tipo, alvo, quant, desfolha, pressao, severidade, incidencia, densidade, estresse, resistencia):
    alertas = []; status = "success"
    a_low = alvo.lower()
    is_repro = any(x in estagio for x in ["R1","R2","R3","R4","R5","R6","R7","R8","Florescimento","Enchimento"])
    
    if tipo == "Praga":
        if "percevejo" in a_low and is_repro and quant >= 1.5:
            alertas.append("🔴 AÇÃO IMEDIATA: Toxinas na estrutura reprodutiva. NDE atingido."); status = "error"
        elif "lagarta" in a_low and desfolha > 15:
            alertas.append(f"🔴 DANO ECONÔMICO: Desfolha de {desfolha}% ultrapassou o limite reajustado."); status = "error"
        elif any(v in a_low for v in ["cigarrinha", "pulgão"]) and pressao in ["Média", "Alta"]:
            alertas.append("🔴 ALERTA DE VETOR: Alta pressão de pragas sugadoras/vetoras de virose."); status = "error"
            
    elif tipo == "Doença":
        if severidade >= 5 and any(d in a_low for d in ["ferrugem", "mofo", "enfezamento"]):
            alertas.append("🔴 INTERVENÇÃO IMEDIATA: Doença crítica em avanço agressivo."); status = "error"
        elif severidade > 10:
            alertas.append(f"🔴 CONTROLE NECESSÁRIO: Severidade de {severidade}% afeta fotossíntese líquida."); status = "error"
            
    elif tipo == "Plantas Daninhas":
        if "tiguera" in a_low or "voluntária" in a_low:
            alertas.append("🔴 PONTE VERDE: Plantas voluntárias hospedam pragas severas. Eliminação prioritária."); status = "error"
        elif resistencia == "Sim":
            alertas.append("🔴 RESISTÊNCIA: Falha de controle químico reportada. Faça rotação de mecanismo de ação (MOA)."); status = "error"
        elif densidade == "Alta (Tapete)":
            alertas.append("🔴 MATOCOMPETIÇÃO: Nível crítico. Perda direta de produtividade por roubo de água/luz."); status = "error"
            
    if not alertas: return "🟢 Monitoramento Estável", "Nível de dano abaixo da tolerância econômica da cultura.", "success"
    return "ALERTA AGRONÔMICO", "\n\n".join(alertas), status

with st.form("form_bio", clear_on_submit=False):
    tab1, tab2, tab3 = st.tabs(["1️⃣ Identificação", "2️⃣ Avaliação Técnica", "3️⃣ Finalização"])
    
    with tab1:
        col1, col2 = st.columns(2)
        with col1: cultura = st.selectbox("Cultura:", ["Soja", "Milho Safrinha", "Sorgo"])
        with col2: tipo_selecionado = st.selectbox("Categoria:", ["Praga", "Doença", "Plantas Daninhas"])
            
        if tipo_selecionado == "Praga": opcoes = list(INFO_PRAGAS.keys()); dic_ativo = INFO_PRAGAS
        elif tipo_selecionado == "Doença": opcoes = list(INFO_DOENCAS.keys()); dic_ativo = INFO_DOENCAS
        else: opcoes = list(INFO_DANINHAS.keys()); dic_ativo = INFO_DANINHAS
        
        alvo_escolhido = st.selectbox(f"Identificação do Alvo:", opcoes)
        
        if alvo_escolhido in dic_ativo and "Não listada" not in alvo_escolhido:
            with st.expander("📖 Guia de Campo Rápido"):
                st.write(f"**Danos:** {dic_ativo[alvo_escolhido]['dano']}")
                st.write(f"**Identificação:** {dic_ativo[alvo_escolhido]['id']}")
        
    with tab2:
        estagio_cultura = st.selectbox("Fase da Cultura:", ["VE a V4 (Vegetativo Inicial)", "V5 a V-T (Vegetativo Pleno)", "Florescimento (R1-R2)", "Enchimento de Grãos (R3-R6)", "Maturação"])
        quant = 0.0; desfolha = 0; pressao = "Baixa"; severidade = 0; incidencia = 0; densidade = "Baixa"; resistencia = "Não"; estresse = "Não"
        
        colA, colB = st.columns(2)
        with colA:
            if tipo_selecionado == "Praga":
                quant = st.number_input("Insetos por amostra/pano:", 0.0, step=0.5)
                desfolha = st.slider("Desfolha ou Dano (%):", 0, 100, 0)
            elif tipo_selecionado == "Doença":
                severidade = st.slider("Severidade foliar (%):", 0, 100, 5)
                incidencia = st.slider("Incidência na área (%):", 0, 100, 10)
            else:
                densidade = st.selectbox("Densidade da Daninha:", ["Baixa (1-5/m²)", "Média", "Alta (Tapete)"])
                resistencia = st.selectbox("Suspeita de Resistência a Herbicidas?", ["Não", "Sim"])
        with colB:
            distribuicao = st.selectbox("Distribuição na área:", ["Generalizada", "Reboleiras/Focos", "Bordaduras"])
            if tipo_selecionado == "Praga": pressao = st.selectbox("Pressão Geral Aparente:", ["Baixa", "Média", "Alta"])
            elif tipo_selecionado == "Doença": estresse = st.selectbox("Clima atual:", ["Quente e Seco", "Quente e Úmido", "Frio e Úmido"])
            else: estresse = st.selectbox("Estado da Daninha:", ["Vigorosa", "Estressada por Seca/Roçada"])

    with tab3:
        conn = sqlite3.connect(ARQUIVO_DB)
        try:
            talhoes = pd.read_sql_query("SELECT id, nome FROM talhoes", conn)
            mapa_t = dict(zip(talhoes['nome'], talhoes['id'])) if not talhoes.empty else {"Sede": 1}
        except:
            mapa_t = {"Sede": 1}
        conn.close()
        
        talhao_escolhido = st.selectbox("Localização (Talhão):", list(mapa_t.keys()))
        anotacoes = st.text_area("Observações Escritas de Campo:")
        audio_obs = st.audio_input("🎙️ Gravar Observação por Voz (Opcional - O Felipe escuta!):")
        foto = st.camera_input("Fotografia (Opcional - O Felipe analisa se enviada!)")
        salvou = st.form_submit_button("Gerar Análise e Salvar")

if salvou:
    obs_resumo = anotacoes if anotacoes else ("Relato gravado por voz" if audio_obs else "Sem observações")
    detalhes = f"Alvo: {alvo_escolhido} | Dist: {distribuicao} | Obs: {obs_resumo}"
    t_alert, d_alert, status = conselheiro_geral(cultura, estagio_cultura, tipo_selecionado, alvo_escolhido, quant, desfolha, pressao, severidade, incidencia, densidade, estresse, resistencia)
    
    st.markdown("---")
    if status == "error": st.error(f"**{t_alert}**\n\n{d_alert}")
    elif status == "warning": st.warning(f"**{t_alert}**\n\n{d_alert}")
    else: st.success(f"**{t_alert}**\n\n{d_alert}")
    
    if api_key:
        st.markdown("### 🤖 Parecer do Felipe")
        with st.chat_message("ai", avatar="felipe_avatar.png"):
            with st.spinner("Analisando o quadro biológico, fotos e áudio..."):
                try:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('models/gemini-3.5-flash')
                    
                    prompt = f"""
                    Aja como Felipe, agrônomo de campo experiente, direto e técnico.
                    Cultura: {cultura} ({estagio_cultura}). MIP de: {tipo_selecionado} ({alvo_escolhido}). 
                    Situação: {d_alert}. Obs escrita do técnico: {anotacoes}.
                    
                    REGRAS:
                    1. Inicie com saudação objetiva.
                    2. Faça um **DIAGNÓSTICO TÉCNICO** do impacto fisiológico da praga/doença na fase atual.
                    3. Forneça um **PLANO DE AÇÃO**.
                    4. Destaque em **NEGRITO/MAIÚSCULAS** recomendações de grupos químicos ideais para esse alvo e fase.
                    """
                    
                    conteudo_enviado = [prompt]
                    if foto:
                        imagem_pil = Image.open(foto)
                        conteudo_enviado.append(imagem_pil)
                        conteudo_enviado[0] += "\n[ATENÇÃO: O utilizador anexou uma fotografia. Analise a imagem detalhadamente para complementar o seu diagnóstico.]"
                    
                    if audio_obs:
                        bytes_audio = audio_obs.getvalue()
                        pacote_audio = {"mime_type": audio_obs.type or "audio/wav", "data": bytes_audio}
                        conteudo_enviado.append(pacote_audio)
                        conteudo_enviado[0] += "\n[ATENÇÃO: O utilizador gravou um relato em áudio no campo. Escute o áudio e incorpore os detalhes relatados no diagnóstico e plano de ação.]"
                    
                    resposta_texto = model.generate_content(conteudo_enviado).text
                    st.write(resposta_texto)
                    if voz_ativa:
                        falar_felipe(resposta_texto)
                except Exception as e:
                    st.error(f"Felipe indisponível. Erro de API: {e}")
    
    caminho = None
    if foto:
        caminho = f"fotos_app/bio_{datetime.now().strftime('%Y%m%d%H%M')}.jpg"
        with open(caminho, "wb") as f: f.write(foto.getbuffer())
    conn = sqlite3.connect(ARQUIVO_DB)
    conn.cursor().execute("INSERT INTO apontamentos (talhao_id, tipo, detalhes, foto_path) VALUES (?, ?, ?, ?)", (mapa_t.get(talhao_escolhido, 1), f"Biológico: {tipo_selecionado}", detalhes, caminho))
    conn.commit()
    conn.close()
    st.toast("Apontamento biológico salvo!", icon='💾')