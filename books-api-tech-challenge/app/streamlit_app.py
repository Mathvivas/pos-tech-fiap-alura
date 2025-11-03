import requests
import streamlit as st
from dotenv import load_dotenv
import os

load_dotenv()

for key in ("form_user", "form_pass", "token"):
    st.session_state.setdefault(key, "")

API_URL = os.getenv("API_URL")

st.set_page_config(
    page_title='API de Livros',
    page_icon=':orange_book:'
)

def sidebar():

    st.html("""
        <style>
            [alt=Logo] {
                padding-top: 1rem;
                height: 10rem;
            }
        </style>
    """)
    
    with st.sidebar:
        st.title('API de Livros')
        st.markdown('-----')
        
        with st.expander('Conta', icon=':material/account_box:'):
            def login():
                user_val = st.session_state.form_user
                pass_val = st.session_state.form_pass

                auth = {
                    'username': user_val,
                    'password': pass_val
                }

                response_login = requests.post(f'{API_URL}/api/v1/auth/login', json=auth)

                if response_login.status_code == 201:
                    dados_json = response_login.json()
                    st.session_state['login_message'] = ('success', dados_json.get('access_token'))
                else:
                    st.session_state['login_message'] = ('error', 'Não foi possível realizar o login')

            def register():
                user_val = st.session_state.form_user
                pass_val = st.session_state.form_pass

                auth = {
                    'username': user_val,
                    'password': pass_val
                }

                response_register = requests.post(f'{API_URL}/api/v1/auth/register', json=auth)

                if response_register.status_code == 201:
                    st.session_state['login_message'] = ('success', response_register.text)
                else:
                    st.session_state['login_message'] = ('error', response_register.text)

            user = st.text_input('Usuário', key='form_user')
            password = st.text_input('Senha', type='password', key='form_pass')
            col1, col2 = st.columns(2)
            
            with col1:
                register = st.button('Registrar', icon=':material/person_add:', on_click=register)
            
            with col2:
                login = st.button('Login', icon=':material/login:', on_click=login)

            if 'login_message' in st.session_state:
                type, message = st.session_state.login_message
                if type == 'success':
                    st.success(message)
                else:
                    st.error(message)
            
            

        with st.expander('Token', icon=':material/token:'):
            token = st.text_input('Cole o token aqui:', type='password', key='token')
            atualizar = st.button('Renovar token prestes a expirar')
            
            if atualizar:
                header = {'Authorization': f'Bearer {token}'}
                response_atualizar = requests.post(f'{API_URL}/api/v1/auth/refresh', headers=header)

                if response_atualizar.status_code == 200:
                    dados_json = response_atualizar.json()
                    st.success(dados_json.get('access_token'))
                else:
                    st.error([response_atualizar.status_code, response_atualizar.content])

        st.markdown('-----')
        st.page_link(f"{API_URL}/apidocs/", label="Documentação", icon=':material/docs:')

pages = {
    'Web Scraping': [
        st.Page('pages/web_scraping.py', title='Web Scraping', icon=':material/tools_power_drill:')
    ],
    'Livros': [
        st.Page('pages/listar_livros.py', title='Listar Livros', icon=':material/book_2:')
    ],
    'Categorias': [
        st.Page('pages/listar_categorias.py', title='Listar Categorias', icon=':material/category:')
    ],
    'Estatísticas': [
        st.Page('pages/estatisticas.py', title='Estatísticas', icon=':material/bar_chart:')
    ],
    'Status': [
        st.Page('pages/status.py', title='Status', icon=':material/android_wifi_3_bar:')
    ],
    'Métricas': [
        st.Page('pages/metrics.py', title='Métricas', icon=':material/signal_cellular_alt:')
    ],
    'Machine Learning': [
        st.Page('pages/machine_learning.py', title='Machine Learning', icon=':material/robot_2:')
    ]
}

st.logo('../images/book-logo-nbg.png')

footer="""<style>
a:link , a:visited{
color: #00ffff;
background-color: transparent;
}

a:hover,  a:active {
color: red;
background-color: transparent;
text-decoration: underline;
}

.footer {
position: fixed;
left: 0;
bottom: 0;
width: 100%;
color: white;
text-align: center;
background-color: #0E1117;
z-index: 1;
}
</style>
<div class="footer">
<p>Developed by <a style='display: block; text-align: center;' href="https://github.com/Mathvivas" target="_blank">Matheus Lopes Vivas</a></p>
</div>
"""

def main():
    sidebar()
    st.html(footer)
    pg = st.navigation(pages, position='top')
    pg.run()

if __name__ == '__main__':
    main()