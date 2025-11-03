import requests
import streamlit as st
from app import app
import pandas as pd
from utils import setar_metrica
from pagination import pagination, get_data
from dotenv import load_dotenv
import os

load_dotenv()

API_URL = os.getenv('API_URL')

app.config.from_object('config')
app.json.ensure_ascii = False

tab1, tab2, tab3, tab4 = st.tabs(['Livros', 'Livros por Título ou Categoria', 'Livros por Intervalo de Preço', 'Top Livros (5 estrelas)'])

with tab1:
    st.subheader('Listar Livros ou Listar Detalhes de um Livro pelo ID')

    indice = st.text_input('Digitar o id de um livro específico para saber os detalhes (não obrigatório):', key='wbscr_indice')

    get_livros = st.button('Listar', key='listar_1')

    if get_livros:
        st.session_state['fetch_data'] = True

    # If exists, returns the value, if not, returns the default value
    if st.session_state.get('fetch_data', default=False):
        if 'token' not in st.session_state or st.session_state.token == '':
            st.error('Token de autenticação não encontrado. Por favor, faça login.')
            st.session_state['fetch_data'] = False
        else:
            token = st.session_state['token']

            if indice:
                try:
                    headers = {'Authorization': f'Bearer {token}'}
                    response = requests.get(f'{API_URL}/api/v1/books/{indice}', headers=headers)
                    if response.status_code == 200:
                        setar_metrica()
                        df = pd.DataFrame(response.json())
                        df.rename(columns={
                                'Title': 'Título',
                                'Id': 'Id',
                                'Category': 'Categoria',
                                'Image': 'Imagem',
                                'Price': 'Preço',
                                'Rating': 'Nota',
                                'Availability': 'Disponibilidade',
                            }, inplace=True)
                        st.dataframe(df, column_config={
                            'Imagem': st.column_config.ImageColumn(label='Imagem', width=110)
                        }, hide_index=True)
                    else:
                        st.error(f'Erro ao buscar livro: {response.text}')
                except Exception as e:
                    st.error(f'Ocorreu um erro ao conectar à API: {e}')
            else:
                if 'livros_df' not in st.session_state:
                    dados = get_data('/api/v1/books', token)
                    if dados:
                        setar_metrica()
                        df = pd.DataFrame(dados)
                        st.session_state['livros_df'] = df.rename(columns={
                                                        'Title': 'Título',
                                                        'Id': 'Id',
                                                        'Category': 'Categoria',
                                                        'Price': 'Preço',
                                                        'Rating': 'Nota',
                                                        'Availability': 'Disponibilidade',
                                                        })
                    else:
                        st.session_state['fetch_data'] = False
                        st.stop()

                df = st.session_state['livros_df']

                top_menu = st.columns(3)

                with top_menu[0]:
                    sort = st.radio('Ordenar Dados?', options=['Sim', 'Não'], horizontal=1, index=1)
                if sort == 'Sim':
                    with top_menu[1]:
                        sort_field = st.selectbox('Ordenar Por', options=df.columns)
                    with top_menu[2]:
                        sort_direction = st.radio('Direção', 
                                                options=[':material/arrow_upward:', ':material/arrow_downward:'],
                                                horizontal=True
                                                )
                    df = df.sort_values(
                        by=sort_field, ascending=sort_direction == ':material/arrow_upward:', ignore_index=True
                    )

                pagination(df, key='listar_livros')

with tab2:
    st.subheader('Listar Livros por Título ou Categoria')
    titulo = st.text_input('Digitar uma palavra que esteja contida no título de um livro:', key='wbscr_listar_livros_titulo')
    categoria = st.text_input('Digitar uma palavra que esteja contida na categoria de um livro:', key='wbscr_listar_livros_categoria')

    get_livros = st.button('Listar', key='listar_2')
    if get_livros:
        try:
            token = st.session_state['token']
            headers = {'Authorization': f'Bearer {token}'}
            if not titulo and not categoria:
                st.error('Título ou Categoria deve ser preenchido')
            else:
                if titulo and not categoria:
                    response = requests.get(f'{API_URL}/api/v1/books/search?title={titulo}', headers=headers)
                elif categoria and not titulo:
                    response = requests.get(f'{API_URL}/api/v1/books/search?category={categoria}', headers=headers)
                else:
                    response = requests.get(f'{API_URL}/api/v1/books/search?title={titulo}&category={categoria}', headers=headers)

                if response.status_code == 200:
                    setar_metrica()
                    df = pd.DataFrame(response.json())
                    df.rename(columns={
                        'Title': 'Título',
                        'Id': 'Id',
                        'Category': 'Categoria',
                        'Price': 'Preço',
                        'Rating': 'Nota',
                        'Availability': 'Disponibilidade',
                    }, inplace=True)
                    st.dataframe(df, column_config={
                        'Preço': st.column_config.NumberColumn(format='R$%.2f')
                    })
                else:
                    st.error(f'Erro ao buscar livro: {response.text}')
        except Exception as e:
                st.error(f'Ocorreu um erro ao conectar à API: {e}')


with tab3:
    st.subheader('Listar Livros por Intervalo de Preço')
    min = st.text_input('Digitar um preço mínimo:', key='wbscr_listar_livros_preco_min')
    max = st.text_input('Digitar um preço máximo:', key='wbscr_listar_livros_preco_max')

    get_livros = st.button('Listar', key='listar_3')
    if get_livros:
        try:
            token = st.session_state['token']
            headers = {'Authorization': f'Bearer {token}'}
            if not min and not max:
                st.error('Preço mínimo ou preço máximo deve ser preenchido')
            else:
                if min and not max:
                    response = requests.get(f'{API_URL}/api/v1/books/price-range?min={min}', headers=headers)
                elif max and not min:
                    response = requests.get(f'{API_URL}/api/v1/books/price-range?max={max}', headers=headers)
                else:
                    response = requests.get(f'{API_URL}/api/v1/books/price-range?min={min}&max={max}', headers=headers)

                if response.status_code == 200:
                    setar_metrica()
                    df = pd.DataFrame(response.json())
                    df.rename(columns={
                        'Title': 'Título',
                        'Id': 'Id',
                        'Category': 'Categoria',
                        'Price': 'Preço',
                        'Rating': 'Nota'
                    }, inplace=True)
                    st.dataframe(df, column_config={
                        'Preço': st.column_config.NumberColumn(format='R$%.2f')
                    })
                else:
                    st.error(f'Erro ao buscar livro: {response.text}')
        except Exception as e:
                st.error(f'Ocorreu um erro ao conectar à API: {e}')
            

with tab4:
    st.subheader('Listar Top Livros')

    get_livros = st.button('Listar', key='listar_4')
    if get_livros:
        try:
            token = st.session_state['token']
            headers = {'Authorization': f'Bearer {token}'}
            response = requests.get(f'{API_URL}/api/v1/books/top-rated', headers=headers)

            if response.status_code == 200:
                setar_metrica()
                df = pd.DataFrame(response.json())
                df.rename(columns={
                    'Title': 'Título',
                    'Rating': 'Nota'
                }, inplace=True)
                st.dataframe(df)
            else:
                st.error(f'Erro ao buscar livro: {response.text}')
        except Exception as e:
                st.error(f'Ocorreu um erro ao conectar à API: {e}')