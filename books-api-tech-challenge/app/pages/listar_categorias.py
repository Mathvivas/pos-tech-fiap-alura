import requests
import streamlit as st
from app import app
import ast
import pandas as pd
from streamlit_app import setar_metrica

app.config.from_object('config')
app.json.ensure_ascii = False

st.set_page_config(
    page_title='Procurando Livro',
    page_icon=':orange_book:'
)

st.title('Procurando um Livro? :material/shelves:')

st.header('Listar Categorias')

categ = st.button('Listar categorias')

if categ:
    token = st.session_state['token']
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get('http://localhost:5000/api/v1/categories', headers=headers)

    if response.status_code == 200:
        setar_metrica()
        dados = ast.literal_eval(response.text)
        df = pd.DataFrame(dados, columns=['Categorias'])
        st.dataframe(df)
    else:
        st.error(response.text)