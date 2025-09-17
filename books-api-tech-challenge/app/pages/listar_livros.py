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

tab1, tab2, tab3, tab4 = st.tabs(['Livros', 'Livros por Título ou Categoria', 'Livros por Intervalo de Preço', 'Top Livros (5 estrelas)'])

with tab1:
    st.subheader('Listar Livros ou Listar Detalhes de um Livro pelo ID')

    indice = st.text_input('Digitar o id de um livro específico para saber os detalhes (não obrigatório):')

    get_livros = st.button('Listar', key='listar_1')
    token = st.session_state['token']
    if get_livros and not indice:
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

with tab2:
    st.subheader('Listar Livros por Título ou Categoria')
    titulo = st.text_input('Digitar uma palavra que esteja contida no título de um livro:')
    categoria = st.text_input('Digitar uma palavra que esteja contida na categoria de um livro:')

    get_livros = st.button('Listar', key='listar_2')
    if get_livros:
        token = st.session_state['token']
        headers = {'Authorization': f'Bearer {token}'}
        if not titulo and not categoria:
            st.error('Título ou Categoria deve ser preenchido')
        else:
            if titulo and not categoria:
                response = requests.get(f'http://localhost:5000/api/v1/books/search?title={titulo}', headers=headers)
            elif categoria and not titulo:
                response = requests.get(f'http://localhost:5000/api/v1/books/search?category={categoria}', headers=headers)
            else:
                response = requests.get(f'http://localhost:5000/api/v1/books/search?title={titulo}&category={categoria}', headers=headers)

            if response.status_code == 200:
                st.text(response.text)
            else:
                st.error(response.text)


with tab3:
    st.subheader('Listar Livros por Intervalo de Preço')
    min = st.text_input('Digitar um preço mínimo:')
    max = st.text_input('Digitar um preço máximo:')

    get_livros = st.button('Listar', key='listar_3')
    if get_livros:
        token = st.session_state['token']
        headers = {'Authorization': f'Bearer {token}'}
        if not min and not max:
            st.error('Preço mínimo ou preço máximo deve ser preenchido')
        else:
            if min and not max:
                response = requests.get(f'http://localhost:5000/api/v1/books/price-range?min={min}', headers=headers)
            elif max and not min:
                response = requests.get(f'http://localhost:5000/api/v1/books/price-range?max={max}', headers=headers)
            else:
                response = requests.get(f'http://localhost:5000/api/v1/books/price-range?min={min}&max={max}', headers=headers)

            if response.status_code == 200:
                st.text(response.text)
            else:
                st.error(response.text)

with tab4:
    st.subheader('Listar Top Livros')

    get_livros = st.button('Listar', key='listar_4')
    if get_livros:
        token = st.session_state['token']
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get('http://localhost:5000/api/v1/books/top-rated', headers=headers)

        if response.status_code == 200:
            st.text(response.text)
        else:
            st.error(response.text)