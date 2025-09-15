import requests
import streamlit as st
from app import app
import pandas as pd

app.config.from_object('config')
app.json.ensure_ascii = False
df = pd.read_csv(app.config['CSV_FILE_PATH'])

st.set_page_config(
    page_title='Procurando Livro',
    page_icon=':orange_book:'
)

st.title('Procurando um Livro?')

tab1, tab2, tab3, tab4, tab5 = st.tabs(['Dados', 'Listar Livros', 'Listar Categorias', 'Estatísticas', 'Status API'])

with tab1:
    st.header('Dados')

    st.divider()

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

    with st.sidebar:
        with st.expander('Usuário', icon=':material/account_box:'):

            user = st.text_input('Usuário')
            password = st.text_input('Senha')

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
                    st.success(response_login.text)
                else:
                    st.error(response_login.text)

        with st.expander('Atualizar Token', icon=':material/token:'):
            st.button('Atualizar')
            # response = requests.get()


with tab2:
    st.header('Listar Livros')

    token = st.text_input('Cole o token aqui:')
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

with tab4:
    st.header('Estatísticas')

with tab5:
    st.header('Status API')