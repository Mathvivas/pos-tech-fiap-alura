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

st.title('Procurando um Livro?')

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
            atualizar = st.button('Renovar token prestes a expirar')
            if atualizar:
                header = {'Authorization': f'Bearer {token}'}
                response_atualizar = requests.post('http://localhost:5000/api/v1/auth/refresh', headers=header)

                if response_atualizar.status_code == 200:
                    dados_json = response_atualizar.json()
                    st.success(dados_json.get('access_token'))
                else:
                    st.error([response_atualizar.status_code, response_atualizar.content])

            
tab1, tab2, tab3, tab4, tab5 = st.tabs(['Dados', 'Listar Livros', 'Listar Categorias', 'Estatísticas', 'Status API'])

with tab1:
    st.header('Dados')

    st.dataframe(data=df, width='content', hide_index=True, column_config={
        'Price': st.column_config.NumberColumn(label='Preço', format='R$%.2f'),
        'Image': st.column_config.ImageColumn(label='Imagem', width=110)
    })

    st.markdown(
        """
        <style>
        section[data-testid="stSidebar"] {
            width: 350px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

with tab2:
    st.header('Listar Livros')

    get_livros = st.button('Listar livros')
    if get_livros:
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get('http://localhost:5000/api/v1/books', headers=headers)

        if response.status_code == 200:
            st.text(response.text)
        else:
            st.error(response.text)

with tab3:
    st.header('Listar Categorias')

    categ = st.button('Listar categorias')

    if categ:
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get('http://localhost:5000/api/v1/categories', headers=headers)

        if response.status_code == 200:
            st.text(response.text)
        else:
            st.error(response.text)

with tab4:
    st.header('Estatísticas')

    estatisticas = st.button('Estatísticas')

    if estatisticas:
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get('http://localhost:5000/api/v1/stats/overview', headers=headers)

        if response.status_code == 200:
            dados_json = response.json()
            st.dataframe(dados_json, column_config={
                'value': st.column_config.TextColumn(label='Valor'),
            })
        else:
            st.text(response.text)

with tab5:
    st.header('Status API')

    status = st.button('Checar Status')
    if status:
        with st.spinner('Checando o sistema...', show_time=True):
            response = requests.get('http://localhost:5000/api/v1/health')
            time.sleep(1)
            
        if response.status_code == 200:
            st.success(':material/check: ' + response.text)
        else:
            st.warning(':material/error: ' + response.text)
