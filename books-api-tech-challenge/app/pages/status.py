import requests
import streamlit as st
from app import app
import time
from streamlit_app import setar_metrica
import os

API_URL = os.getenv('API_URL')

app.config.from_object('config')
app.json.ensure_ascii = False

st.header('Status API')

status = st.button('Checar Status')
if status:
    setar_metrica()
    with st.spinner('Checando o sistema...', show_time=True):
        response = requests.get(f'{API_URL}/api/v1/health')
        time.sleep(1)
            
    if response.status_code == 200:
        st.success(':material/check: ' + response.text)
    else:
        st.warning(':material/error: ' + response.text)