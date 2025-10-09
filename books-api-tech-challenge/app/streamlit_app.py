import requests
import streamlit as st
from app import app, logger
import pandas as pd
import datetime
import threading
import nltk


app.config.from_object('config')
app.json.ensure_ascii = False

@st.cache_resource
def load_data(file_path):
    return pd.read_csv(file_path)

def setar_metrica():
    st.session_state['metric'] += 1
    new_row = pd.DataFrame([{'Time': datetime.datetime.now(), 'Metric': st.session_state.metric}])
    st.session_state.history = pd.concat([st.session_state.history, new_row], ignore_index=True)

@st.cache_data(show_spinner=False)
def split_frame(input_df, rows):
    df = [input_df.loc[i : i + rows - 1, :] for i in range(0, len(input_df), rows)]
    return df

st.set_page_config(
    page_title='Books API',
    page_icon=':orange_book:'
)

pages = {
    'Web Scraping': [
        st.Page('pages/web_scraping.py', title='Web Scraping', icon=':material/tools_power_drill:')
    ],
    'Livros': [
        st.Page('pages/listar_livros.py', title='Listar Livros', icon=':material/book_2:')
    ],
    'Categorias': [
        st.Page('pages/listar_categorias.py', title='Listar Categorias', icon=':material/category:')
    ],
    'Estatísticas': [
        st.Page('pages/estatisticas.py', title='Estatísticas', icon=':material/bar_chart:')
    ],
    'Status': [
        st.Page('pages/status.py', title='Status', icon=':material/android_wifi_3_bar:')
    ],
    'Métricas': [
        st.Page('pages/metrics.py', title='Métricas', icon=':material/signal_cellular_alt:')
    ],
    'Machine Learning': [
        st.Page('pages/machine_learning.py', title='Machine Learning', icon=':material/robot_2:')
    ]
}

nltk.download('stopwords')
    
if 'df' not in st.session_state:
    df = load_data(app.config['CSV_FILE_PATH'])
    st.session_state['df'] = df

if 'embeddings' not in st.session_state:
    df_embeddings = load_data(app.config['CSV_FILE_PATH_EMBEDDINGS'])
    st.session_state['embeddings'] = df_embeddings

logger.info(f'start of streamlit_test, {threading.get_ident()}')

if 'metric' not in st.session_state:
    st.session_state['metric'] = 0
    metric = st.session_state['metric']

if 'history' not in st.session_state:
    st.session_state['history'] = pd.DataFrame(columns=['Time', 'Metric'])

st.html("""
    <style>
        [alt=Logo] {
            padding-top: 1rem;
            height: 10rem;
        }
    </style>
""")

with st.sidebar:
    st.logo('../images/book-logo-nbg.png')
    st.title('API de Livros')
    st.markdown('-----')
    
    with st.expander('Usuário', icon=':material/account_box:'):
        user = st.text_input('Usuário')
        password = st.text_input('Senha', type='password')
        col1, col2 = st.columns(2)
        
        with col1:
            register = st.button('Registrar', icon=':material/person_add:')
        
        with col2:
            login = st.button('Login', icon=':material/login:')
        
        if register:
            auth = {
                'username': user,
                'password': password
            }
            response_register = requests.post('http://localhost:5000/api/v1/auth/register', json=auth)
        
            if response_register.status_code == 201:
                st.success(response_register.text)
            else:
                st.error(response_register.text)
        if login:
            auth = {
                'username': user,
                'password': password
            }
        
            response_login = requests.post('http://localhost:5000/api/v1/auth/login', json=auth)
        
            if response_login.status_code == 201:
                dados_json = response_login.json()
                st.success('Token: ' + dados_json.get('access_token'))
            else:
                st.error(response_login.text)

    with st.expander('Token', icon=':material/token:'):
        token = st.text_input('Cole o token aqui:', type='password')
        st.session_state['token'] = token
        atualizar = st.button('Renovar token prestes a expirar')
        
        if atualizar:
            header = {'Authorization': f'Bearer {token}'}
            response_atualizar = requests.post('http://localhost:5000/api/v1/auth/refresh', headers=header)

            if response_atualizar.status_code == 200:
                dados_json = response_atualizar.json()
                st.success(dados_json.get('access_token'))
            else:
                st.error([response_atualizar.status_code, response_atualizar.content])

    st.markdown('-----')
    st.page_link("http://localhost:5000/apidocs/", label="Documentação", icon=':material/docs:')

footer="""<style>
a:link , a:visited{
color: #00ffff;
background-color: transparent;
}

a:hover,  a:active {
color: red;
background-color: transparent;
text-decoration: underline;
}

.footer {
position: fixed;
left: 0;
bottom: 0;
width: 100%;
color: white;
text-align: center;
background-color: #0E1117;
z-index: 1;
}
</style>
<div class="footer">
<p>Developed by <a style='display: block; text-align: center;' href="https://github.com/Mathvivas" target="_blank">Matheus Lopes Vivas</a></p>
</div>
"""

st.html(footer)

pg = st.navigation(pages, position='top')
pg.run()