import requests
import streamlit as st
from app import app
import pandas as pd
from streamlit_app import setar_metrica
from pagination import pagination, get_data
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
        st.session_state['fetch_data_features'] = True

    if st.session_state.get('fetch_data_features', default=False):
        if 'livros_ml_features' not in st.session_state:
            dados = get_data(url='/api/v1/ml/features')
            if dados:
                st.session_state['livros_ml_features'] = pd.DataFrame(json.loads(dados))
            else:
                st.session_state['fetch_data_features'] = False
                st.stop()

        df = st.session_state['livros_ml_features']
        setar_metrica()

        pagination(df, key='ml_features')

with tab2:
    st.subheader('Dados de Treinamento')
    bt = st.button('Obter dados')
    
    if bt:
        st.session_state['fetch_data_training'] = True

    if st.session_state.get('fetch_data_training', default=False):
        if 'livros_ml_training' not in st.session_state:
            dados = get_data(url='/api/v1/ml/training-data')
            if dados:
                st.session_state['livros_ml_training'] = pd.DataFrame(json.loads(dados))
            else:
                st.session_state['fetch_data_training'] = False
                st.stop()

        df = st.session_state['livros_ml_training']
        setar_metrica()

        pagination(df, key='ml_training')

with tab3:
    st.subheader('Predições')
    query = st.text_input('Digite uma palavra (em inglês) do que busca para obter títulos similares existentes', key='ml_predicoes')
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
                            df = pd.DataFrame(json.loads(response.json()))
                            st.dataframe(df)
                        else:
                            st.error(f'Erro ao buscar livros: {response.text}')
                    except Exception as e:
                        st.error(f'Ocorreu um erro ao conectar à API: {e}')
        else:
            st.error('Campo deve ser preenchido')
