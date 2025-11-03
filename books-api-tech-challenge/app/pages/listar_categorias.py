import requests
import streamlit as st
from app import app
import ast
import pandas as pd
from utils import setar_metrica
from dotenv import load_dotenv
import os

load_dotenv()

API_URL = os.getenv('API_URL')

app.config.from_object('config')
app.json.ensure_ascii = False

st.header('Listar Categorias')

categ = st.button('Listar categorias')

if categ:
    token = st.session_state['token']
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(f'{API_URL}/api/v1/categories', headers=headers)

    if response.status_code == 200:
        setar_metrica()
        dados = ast.literal_eval(response.text)
        df = pd.DataFrame(dados, columns=['Categorias'])
        st.dataframe(df)
    else:
        st.error(f'Não foi possível acessar categorias: {response.text}')