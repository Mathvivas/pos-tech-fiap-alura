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

tab1, tab2 = st.tabs(['Estatísticas', 'Estatísticas de Categoria'])


with tab1:
    st.header('Estatísticas')

    estatisticas = st.button('Estatísticas')

    if estatisticas:
        token = st.session_state['token']
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get('http://localhost:5000/api/v1/stats/overview', headers=headers)

        if response.status_code == 200:
            dados_json = response.json()
            st.dataframe(dados_json, column_config={
                'value': st.column_config.TextColumn(label='Valor'),
            })
        else:
            st.text(response.text)

    # 'http://localhost:5000/api/v1/stats/categories'