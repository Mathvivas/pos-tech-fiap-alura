import requests
import streamlit as st
from app import app, db, logger
from sqlalchemy import create_engine
import pandas as pd
from bs4 import BeautifulSoup
from streamlit_app import setar_metrica
import concurrent.futures

app.config.from_object('config')
app.json.ensure_ascii = False

session = requests.Session()

BASE_URL = 'https://books.toscrape.com/'
CATALOGUE_URL = BASE_URL + 'catalogue/'

### Funções usadas para o web scraping

def get_category(session, url: str):
    logger.debug('Entrando na função de pegar categoria.')
    try:
        response = session.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        category = soup.find('ul', class_='breadcrumb').find_all('li')[2].find('a').get_text()
        return category
    except Exception as e:
        logger.error(f'Erro ao pegar categoria em {url}: {e}')
        return None
    
def get_total_pages(session):
    response = session.get(BASE_URL)
    soup = BeautifulSoup(response.text, 'html.parser')
    current = soup.find('li', class_='current')
    if current:
        text = current.get_text(strip=True)
        return int(text.split()[-1])
    return 1

def get_books_on_page(session, page_num) -> list:
    """
    Pega os detalhes de cada livro dentro de cada página.

    Retorna uma lista de dicionários com os detalhes de cada livro.

    Returns:
        list: Uma lista de dicionários com os detalhes de cada livro.
    """
    logger.debug('Entrando na função de pegar detalhes dos livros.')
    url = f'{CATALOGUE_URL}page-{page_num}.html'
    response = session.get(url, timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    books = []
    for book in soup.select('ol.row li'):
        title = book.find('h3').find('a')['title']
        price = book.find('p', class_='price_color').text[2:]
        rating = book.select_one('p', class_='star-rating')['class'][1]
        availability = book.find('p', class_='instock availability').find('i')['class'][0].split('-')[-1]
        img_url = requests.compat.urljoin(BASE_URL, book.img['src'])
        book_url = requests.compat.urljoin(CATALOGUE_URL, book.h3.a['href'])

        books.append({
            'title': title,
            'price': price,
            'rating': rating,
            'availability': availability,
            'image': img_url,
            'url': book_url
        })

    return books

def get_all_books():
    """Pega todos os livros e inclui suas categorias"""
    all_books = []
    with requests.Session() as session:
        pages = get_total_pages(session)
        logger.info(f'Total de páginas: {pages}')

        for page in range(1, pages + 1):
            logger.debug(f'Raspando página {page}')
            all_books.extend(get_books_on_page(session, page))

        # Pegando categorias em paralelo
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(get_category, session, book['url']): book for book in all_books}
            for future in concurrent.futures.as_completed(futures):
                book = futures[future]
                category = future.result()
                book['category'] = category or 'Desconhecido'

    return all_books


### Aplicação Streamlit

st.header('Web Scraping')

st.markdown('Essa aba tem como objetivo realizar o Web Scraping do site [Books to Scrape](https://books.toscrape.com/index.html) e obter os seguintes campos:')
st.markdown(
    """
    - Título
    - Preço
    - Nota
    - Disponibilidade
    - Categoria
    - Imagem
    """)


# Pegar os dados e colocar em um dataframe, aí df.to_sql envia para o banco
def import_df_to_db():
    with app.app_context():
        db.create_all()
        engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
        
        with st.spinner("Raspando dados do site (~ 2 minutos)...", show_time=True):
            book_data = get_all_books()
            df = pd.DataFrame(book_data)
            df.to_sql('books', engine, if_exists='replace', index=True, index_label='id')
            # df.to_csv('data/books', index=True, index_label='id')
            return df

buttons = st.columns(2, gap=None, width=500)

with buttons[0]:
    scrap = st.button('Realizar Scraping', width="stretch")
# with buttons[1]:
#     listar_csv = st.button('Listar Dados pelo CSV', width="stretch")

if scrap:
    df = import_df_to_db()

    df.drop(columns=['url'], inplace=True)
    df.rename(columns={
            'title': 'Título',
            'id': 'Id',
            'category': 'Categoria',
            'image': 'Imagem',
            'price': 'Preço',
            'rating': 'Nota',
            'availability': 'Disponibilidade',
        }, inplace=True)

    st.dataframe(data=df, width='content', hide_index=True, column_config={
        'Preço': st.column_config.NumberColumn(format='R$%.2f'),
        'Imagem': st.column_config.ImageColumn(width=110)
    })
    setar_metrica()
    # st.session_state['csv_data'] = 1

# if listar_csv:
#     if st.session_state['csv_data'] == 0:
#         st.error('Dados inexistentes, por favor, rode o web scraping para preencher o CSV.')
#     else:
#         setar_metrica()
#         df = pd.read_csv('../data/books.csv')
#         st.dataframe(data=df, width='content', hide_index=True, column_config={
#             'price': st.column_config.NumberColumn(format='R$%.2f'),
#             'image': st.column_config.ImageColumn(width=110)
#         })


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