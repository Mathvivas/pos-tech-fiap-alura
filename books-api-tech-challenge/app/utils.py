import streamlit as st
import pandas as pd
import datetime
import config

@st.cache_resource
def load_data(file_path):
    return pd.read_csv(file_path)

def setar_metrica():
    st.session_state['metric'] += 1
    new_row = pd.DataFrame([{'Time': datetime.datetime.now(), 'Metric': st.session_state.metric}])
    st.session_state.history = pd.concat([st.session_state.history, new_row], ignore_index=True)


if 'df' not in st.session_state:
    df = load_data(config.CSV_FILE_PATH)
    st.session_state['df'] = df

if 'metric' not in st.session_state:
    st.session_state['metric'] = 0
    metric = st.session_state['metric']

if 'history' not in st.session_state:
    st.session_state['history'] = pd.DataFrame(columns=['Time', 'Metric'])

if 'csv_data' not in st.session_state:
    st.session_state['csv_data'] = 0

# if 'form_user' not in st.session_state:
#     st.session_state['form_user'] = ""

# if 'form_pass' not in st.session_state:
#     st.session_state['form_pass'] = ""