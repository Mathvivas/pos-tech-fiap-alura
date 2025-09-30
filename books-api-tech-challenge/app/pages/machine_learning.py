import requests
import streamlit as st
from app import app
import pandas as pd
from streamlit_app import setar_metrica

app.config.from_object('config')
app.json.ensure_ascii = False

st.set_page_config(
    page_title='Procurando Livro',
    page_icon=':orange_book:'
)

st.title('Machine Learning :material/robot:')

tab1, tab2, tab3 = st.tabs(['Características', 'Dados de Treinamento', 'Predições'])

with tab1:
    st.subheader('Características')

with tab2:
    st.subheader('Dados de Treinamento')

with tab3:
    st.subheader('Predições')
