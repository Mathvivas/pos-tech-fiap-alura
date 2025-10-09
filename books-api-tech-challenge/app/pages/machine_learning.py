import requests
import streamlit as st
from app import app
import pandas as pd
from streamlit_app import setar_metrica, load_data
from data_cleaning import data_cleaning, split_data

app.config.from_object('config')
app.json.ensure_ascii = False

st.title('Machine Learning :material/robot:')

tab1, tab2, tab3 = st.tabs(['Características', 'Dados de Treinamento', 'Predições'])

with tab1:
    st.subheader('Características')
    bt = st.button('Obter features')

    if bt:
        try:
            response = requests.get('http://localhost:5000/api/v1/ml/features')
            if response.status_code == 200:
                setar_metrica()
                dados = response.json()
                df = pd.DataFrame(dados)
                df = data_cleaning(df)
                df = df.rename(columns={
                        'Id': 'Id',
                        'Price': 'Preço',
                        'Rating': 'Nota',
                        'Availability': 'Disponibilidade',
                    })
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
            response = requests.get('http://localhost:5000/api/v1/ml/training-data')
            if response.status_code == 200:
                setar_metrica()
                dados = response.json()
                df = pd.DataFrame(dados)
                df = data_cleaning(df)
                X_train, _, _, _ = split_data(df)
                st.dataframe(X_train)
                st.markdown(f'**Shape dos Dados de Treinamento: {X_train.shape}**')
            else:
                st.error(f'Erro ao buscar livros: {response.text}')
        except Exception as e:
            st.error(f'Ocorreu um erro ao conectar à API: {e}')

with tab3:
    st.subheader('Predições')
    query = st.text_input('Digite uma palavra do que busca para obter títulos similares existentes')
    bt = st.button('Obter predição')

    if bt:
        if query:
            if 'token' not in st.session_state or st.session_state.token == '':
                st.error('Token de autenticação não encontrado. Por favor, faça login.')
            else:
                token = st.session_state['token']
            try:
                json_query = {
                    'query': query,
                }
                headers = {'Authorization': f'Bearer {token}'}
                response = requests.post('http://localhost:5000/api/v1/ml/predictions', json=json_query, headers=headers)
                if response.status_code == 200:
                    setar_metrica()
                    dados = response
                    st.dataframe(dados)
                else:
                    st.error(f'Erro ao buscar livros: {response.text}')
            except Exception as e:
                st.error(f'Ocorreu um erro ao conectar à API: {e}')
        else:
            st.error('Campo deve ser preenchido')
