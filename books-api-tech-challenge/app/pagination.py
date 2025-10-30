import streamlit as st
import requests
from dotenv import load_dotenv
import os

load_dotenv()

API_URL = os.getenv("API_URL")

@st.cache_data(show_spinner="Carregando dados do servidor...")
def get_data(url, token=None):
    try:
        if token:
            headers = {'Authorization': f'Bearer {token}'}
            response = requests.get(f'{API_URL}' + url, headers=headers)
            response.raise_for_status()
        else:
            response = requests.get(f'{API_URL}' + url)
        return response.json()
    except requests.exceptions.HTTPError as err:
        st.error(f'Erro do servidor (código {err.response.status_code}): {err.response.text}')
        return None
    except Exception as e:
        st.error(f'Ocorreu um erro ao conectar à API: {e}')
        return None

@st.cache_data(show_spinner=False)
def split_frame(input_df, rows):
    df = [input_df.loc[i : i + rows - 1, :] for i in range(0, len(input_df), rows)]
    return df

def pagination(df, key):
    bottom_menu = st.columns((4, 1, 1))    
    page_container = st.container()

    with bottom_menu[2]:
        batch_size = st.selectbox('Tamanho', options=[25, 50, 100], key='batch_' + key)
    with bottom_menu[1]:
        total_pages = (
            int(len(df) / batch_size) if int(len(df) / batch_size) > 0 else 1
        )
        current_page = st.number_input(
            'Página', min_value=1, max_value=total_pages, step=1, key='page_' + key
        )
    with bottom_menu[0]:
        st.markdown(f'Página **{current_page}** of **{total_pages}**')

    pages = split_frame(df, batch_size)
    page_container.dataframe(data=pages[current_page - 1], width='stretch', hide_index=True, 
                             column_config={
        'Preço': st.column_config.NumberColumn(format='R$%.2f'),
        'Imagem': st.column_config.ImageColumn(width=110)
    })