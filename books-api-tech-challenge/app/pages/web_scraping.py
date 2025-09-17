import requests
import streamlit as st
from app import app
import pandas as pd
import time

app.config.from_object('config')
app.json.ensure_ascii = False
df = pd.read_csv(app.config['CSV_FILE_PATH'])

st.set_page_config(
    page_title='Procurando Livro',
    page_icon=':orange_book:'
)


st.header('Web Scraping')

st.dataframe(data=df, width='content', hide_index=True, column_config={
    'Price': st.column_config.NumberColumn(label='Preço', format='R$%.2f'),
    'Image': st.column_config.ImageColumn(label='Imagem', width=110)
})

st.markdown(
    """
    <style>
    section[data-testid="stSidebar"] {
        width: 350px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)