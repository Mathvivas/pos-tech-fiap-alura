import requests
import streamlit as st
from app import app
import json
import pandas as pd
from streamlit_app import setar_metrica
from dotenv import load_dotenv
import os

load_dotenv()

API_URL = os.getenv('API_URL')

app.config.from_object('config')
app.json.ensure_ascii = False

tab1, tab2 = st.tabs(['Estatísticas Gerais', 'Estatísticas por Categoria'])


with tab1:
    st.subheader('Estatísticas Gerais')

    estatisticas = st.button('Estatísticas', key='stats_1')

    if estatisticas:
        token = st.session_state['token']
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(f'{API_URL}/api/v1/stats/overview', headers=headers)

        if response.status_code == 200:
            setar_metrica()
            col1, col2 = st.columns(2)
            dados_json = response.json()
            df = pd.DataFrame.from_dict(json.loads(dados_json.get('Distribuição de Notas')),
                                        orient='index', columns=['Distribuição'])
            df.index.name = 'Nota'
            df = df.reset_index()
            with col1:
                st.dataframe(df)
            with col2:
                st.text(f'Total de Livros: {dados_json.get("Total de Livros")}')
                st.text(f'Preço Médio: {dados_json.get("Preço Médio")}')
        else:
            st.text(response.text)

with tab2:
    st.subheader('Estatísticas por Categoria')

    estatisticas = st.button('Estatísticas', key='stats_2')

    if estatisticas:
        token = st.session_state['token']
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(f'{API_URL}/api/v1/stats/categories', headers=headers)

        if response.status_code == 200:
            setar_metrica()
            dados_json = response.json()
            df_preco = pd.DataFrame.from_dict(json.loads(dados_json['Preço por Categoria']),
                                              orient='index', columns=['Preço por Categoria'])
            df_total = pd.DataFrame.from_dict(json.loads(dados_json['Total de Livros por Categoria']),
                                              orient='index', columns=['Total de Livros por Categoria'])
            
            combined_df = pd.concat([df_preco, df_total], axis=1, join='outer')
            combined_df = combined_df.reset_index().rename(columns={'index': 'Categoria'})
            st.dataframe(combined_df)
        else:
            st.text(response.text)