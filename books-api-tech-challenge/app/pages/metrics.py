import streamlit as st
from app import app, logger
import pandas as pd

app.config.from_object('config')
app.json.ensure_ascii = False

st.metric(label='Rotas chamadas com sucesso', value=st.session_state['metric'], border=True)
st.line_chart(st.session_state['history'], x='Time', y='Metric', x_label='Hora', y_label='Chamadas')