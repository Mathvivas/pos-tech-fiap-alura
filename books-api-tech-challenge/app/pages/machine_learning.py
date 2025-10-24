import requests
import streamlit as st
from app import app
import pandas as pd
from streamlit_app import setar_metrica, load_data
from data_cleaning import data_cleaning, split_data, vectorize, find_similar
import json
from dotenv import load_dotenv
import os

load_dotenv()

API_URL = os.getenv("API_URL")

app.config.from_object('config')
app.json.ensure_ascii = False

st.title('Machine Learning :material/robot:')

tab1, tab2, tab3 = st.tabs(['Características', 'Dados de Treinamento', 'Predições'])

with tab1:
    st.subheader('Características')
    bt = st.button('Obter features')

    if bt:
        try:
            with st.spinner("Pegando as features...", show_time=True):
                response = requests.get(f'{API_URL}/api/v1/ml/features')
                if response.status_code == 200:
                    setar_metrica()
                    dados = json.loads(response.json())
                    df = pd.DataFrame(dados)
                    st.dataframe(df, column_config={
                                'Imagem': st.column_config.ImageColumn(label='Imagem', width=110)
                    })
                else:
                    st.error(f'Erro ao buscar livros: {response.text}')
        except Exception as e:
            st.error(f'Ocorreu um erro ao conectar à API: {e}')

with tab2:
    st.subheader('Dados de Treinamento')
    bt = st.button('Obter dados')
    
    if bt:
        try:
            with st.spinner("Pegando os dados de treinamento...", show_time=True):
                response = requests.get(f'{API_URL}/api/v1/ml/training-data')
                if response.status_code == 200:
                    setar_metrica()
                    dados = json.loads(response.json())
                    X_train = pd.DataFrame(dados)
                    st.dataframe(X_train)
                    st.markdown(f'**Shape dos Dados de Treinamento: {X_train.shape}**')
                else:
                    st.error(f'Erro ao buscar livros: {response.text}')
        except Exception as e:
            st.error(f'Ocorreu um erro ao conectar à API: {e}')

with tab3:
    st.subheader('Predições')
    query = st.text_input('Digite uma palavra (em inglês) do que busca para obter títulos similares existentes')
    bt = st.button('Obter predição')

    if bt:
        if query:
            with st.spinner("Achando similares...", show_time=True):
                if 'token' not in st.session_state or st.session_state.token == '':
                    st.error('Token de autenticação não encontrado. Por favor, faça login.')
                else:
                    token = st.session_state['token']
                
                    json_query = {
                        'query': query,
                    }
                    headers = {'Authorization': f'Bearer {token}'}
                    try:
                        response = requests.post(f'{API_URL}/api/v1/ml/predictions', json=json_query, headers=headers)
                        if response.status_code == 200:
                            setar_metrica()
                            dados = json.loads(response.json())
                            df = pd.DataFrame(dados)
                            st.dataframe(df)
                        else:
                            st.error(f'Erro ao buscar livros: {response.text}')
                    except Exception as e:
                        st.error(f'Ocorreu um erro ao conectar à API: {e}')
        else:
            st.error('Campo deve ser preenchido')
