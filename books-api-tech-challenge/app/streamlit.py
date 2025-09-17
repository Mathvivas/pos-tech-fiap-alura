import requests
import streamlit as st
from app import app
import pandas as pd
import time

app.config.from_object('config')
app.json.ensure_ascii = False
df = pd.read_csv(app.config['CSV_FILE_PATH'])

st.set_page_config(
    page_title='Procurando Livro',
    page_icon=':orange_book:'
)

pages = {
    'Web Scraping': [
        st.Page('pages/web_scraping.py', title='Web Scraping')
    ],
    'Livros': [
        st.Page('pages/listar_livros.py', title='Listar Livros')
    ],
    'Categorias': [
        st.Page('pages/listar_categorias.py', title='Listar Categorias')
    ],
    'Estatísticas': [
        st.Page('pages/estatisticas.py', title='Estatísticas')
    ],
    'Status': [
        st.Page('pages/status.py', title='Status')
    ]
}

pg = st.navigation(pages, position='top')
pg.run()

with st.sidebar:
        # https://fonts.google.com/icons?icon.set=Material+Symbols&icon.style=Rounded&icon.size=24&icon.color=%23e3e3e3
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
            token = st.text_input('Cole o token aqui:')
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
