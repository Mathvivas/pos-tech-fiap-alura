import requests
import streamlit as st
from app import app
import json
import pandas as pd

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

    @st.cache_data(show_spinner=False)
    def split_frame(input_df, rows):
        df = [input_df.loc[i : i + rows - 1, :] for i in range(0, len(input_df), rows)]
        return df
    
    @st.cache_data(show_spinner=False)
    def get_data(token):
        try:
            headers = {'Authorization': f'Bearer {token}'}
            response = requests.get(f'http://localhost:5000/api/v1/books', headers=headers)
            response.raise_for_status()
            dados = response.json()
            return dados
        except requests.exceptions.HTTPError as err:
            st.error(f'Erro do servidor (código {err.response.status_code}): {err.response.text}')
            return None
        except Exception as e:
            st.error(f'Ocorreu um erro ao conectar à API: {e}')
            return None
        

    if get_livros and not indice:
        st.session_state['fetch_data'] = True

    if st.session_state.get('fetch_data', default=False):
        if 'token' not in st.session_state:
            st.error('Token de autenticação não encontrado. Por favor, faça login.')
            st.session_state['fetch_data'] = False
        else:
            token = st.session_state['token']

        if indice:
            try:
                headers = {'Authorization': f'Bearer {token}'}
                response = requests.get(f'http://localhost:5000/api/v1/books/{indice}', headers=headers)
                if response.status_code == 200:
                    dados = response.json()
                    df = pd.DataFrame(dados)
                    df = df.rename(columns={
                            'Title': 'Título',
                            'Id': 'Id',
                            'Category': 'Categoria',
                            'Image': 'Imagem',
                            'Price': 'Preço',
                            'Rating': 'Nota',
                            'Availability': 'Disponibilidade',
                        })
                    st.dataframe(df, column_config={
                        'Imagem': st.column_config.ImageColumn(label='Imagem', width=110)
                    })
                else:
                    st.error(f'Erro ao buscar livro: {response.text}')
            except Exception as e:
                st.error(f'Ocorreu um erro ao conectar à API: {e}')
        else:
            if 'livros_df' not in st.session_state:
                dados = get_data(token)
                if dados:
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
            bottom_menu = st.columns((4, 1, 1))

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
                    
            pagination = st.container()

            with bottom_menu[2]:
                batch_size = st.selectbox('Tamanho', options=[25, 50, 100])
            with bottom_menu[1]:
                total_pages = (
                    int(len(df) / batch_size) if int(len(df) / batch_size) > 0 else 1
                )
                current_page = st.number_input(
                    'Página', min_value=1, max_value=total_pages, step=1
                )
            with bottom_menu[0]:
                st.markdown(f'Página **{current_page}** of **{total_pages}**')

            pages = split_frame(df, batch_size)
            pagination.dataframe(data=pages[current_page - 1], use_container_width=True)

with tab2:
    st.subheader('Listar Livros por Título ou Categoria')
    titulo = st.text_input('Digitar uma palavra que esteja contida no título de um livro:')
    categoria = st.text_input('Digitar uma palavra que esteja contida na categoria de um livro:')

    get_livros = st.button('Listar', key='listar_2')
    if get_livros:
        try:
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
                    dados = response.json()
                    df = pd.DataFrame(dados)
                    df = df.rename(columns={
                        'Title': 'Título',
                        'Id': 'Id',
                        'Category': 'Categoria',
                        'Price': 'Preço',
                        'Rating': 'Nota',
                        'Availability': 'Disponibilidade',
                    })
                    st.dataframe(df)
                else:
                    st.error(f'Erro ao buscar livro: {response.text}')
        except Exception as e:
                st.error(f'Ocorreu um erro ao conectar à API: {e}')


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