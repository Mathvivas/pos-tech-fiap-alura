import requests
import streamlit as st
from app import app

app.config.from_object('config')
app.json.ensure_ascii = False

st.set_page_config(
    page_title='Procurando Livro',
    page_icon=':orange_book:'
)

st.title('Procurando um Livro? :material/shelves:')

tab1, tab2, tab3, tab4 = st.tabs(['Listar Livros', 'Listar Categorias', 'Estatísticas', 'Status API'])

with tab1:
    st.subheader('Listar Livros')

    indice = st.text_input('Digitar o id de um livro específico para saber os detalhes (não obrigatório):')
    titulo = st.text_input('Digitar uma palavra que esteja contida no título de um livro:')
    categoria = st.text_input('Digitar uma palavra que esteja contida na categoria de um livro:')

    get_livros = st.button('Listar')
    if get_livros and not indice and not titulo and not categoria:
        token = st.session_state['token']
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get('http://localhost:5000/api/v1/books', headers=headers)

        if response.status_code == 200:
            st.text(response.text)
        else:
            st.error(response.text)

    if get_livros and indice:
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(f'http://localhost:5000/api/v1/books/{indice}', headers=headers)

        if response.status_code == 200:
            st.text(response.text)
        else:
            st.error(response.text)

    # 'http://localhost:5000/api/v1/books/search'
    # 'http://localhost:5000/api/v1/books/top-rated'
    # 'http://localhost:5000/api/v1/books/price-range'

