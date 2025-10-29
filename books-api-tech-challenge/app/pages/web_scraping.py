import requests
import streamlit as st
from app import app, db, logger
from sqlalchemy import create_engine
from models import Book
import pandas as pd
from bs4 import BeautifulSoup
import time
from streamlit_app import setar_metrica
import concurrent.futures

app.config.from_object('config')
app.json.ensure_ascii = False

BASE_URL = 'https://books.toscrape.com/'
CATALOGUE_URL = 'https://books.toscrape.com/catalogue/'

### Funções usadas para o web scraping

def get_category(url: str) -> str:
    logger.debug('Entrando na função de pegar categoria.')
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        category = soup.find('ul', class_='breadcrumb').find_all('li')[2].find('a').get_text()
        return category
    except requests.RequestException as e:
        return "Error"

def get_details_from_page(page_url: str) -> list:
    """
    Pega os detalhes de cada livro dentro de cada página.

    Retorna uma lista de dicionários com os detalhes de cada livro.

    Returns:
        list: Uma lista de dicionários com os detalhes de cada livro.
    """
    logger.debug('Entrando na função de pegar detalhes dos livros.')
    page_data = []

    try:
        response = requests.get(page_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        books = soup.find('ol', class_='row').find_all('li')
    except requests.RequestException as e:
        return page_data

    category_tasks = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        for book in books:
            # Extrair detalhes do livro
            article = book.find('article', class_='product_pod')

            title = article.find('h3').find('a')['title']
            price = book.find('p', class_='price_color').text[2:]
            rating = book.find('p', class_='star-rating')['class'][1]
            availability = book.find('p', class_='instock availability').find('i')['class'][0].split('-')[-1]

            link_to_book = article.find('h3').find('a')['href']
            full_link = requests.compat.urljoin(CATALOGUE_URL, link_to_book)

            img = book.find('img')['src']
            image = requests.compat.urljoin(BASE_URL, img)

            future = executor.submit(get_category, full_link)
            category_tasks.append({
                'title': title,
                'price': price,
                'rating': rating,
                'availability': availability,
                'image': image,
                'category': None,
            })

    # Aguardar todas as tarefas da categoria terminarem e coletar os resultados
    for future, book_dict in category_tasks:
        book_dict['category'] = future.result()
        page_data.append(book_dict)

    return page_data

def get_all_details() -> list:
    all_book_data = []
    pages = 1

    try:
        response = requests.get(BASE_URL)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        current_text = soup.find('li', class_='current').get_text(strip=True)

        parts = current_text.split()
        if len(parts) > 2 and parts[-1].isdigit():
            pages = int(parts[-1])
    except Exception:
        pages = 50
    
    page_urls = [f'{CATALOGUE_URL}page-{i+1}.html' for i in range(pages)]

    start_time = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        future_to_url = {executor.submit(get_details_from_page, url): url for url in page_urls}

        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                page_data = future.result()
                all_book_data.extend(page_data)
            except Exception as exc:
                print(f'Error processing {url}: {exc}')

    end_time = time.time()
    total_time = end_time - start_time
    return all_book_data


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

        # if Book.query.first():
        #     print('Database already contains books. Skipping web scraping.')
        #     df = pd.read_sql_query('SELECT * FROM books', engine)
        #     return df
        
        with st.spinner("Pegando os dados do site, deve demorar (~ 30 minutos)...", show_time=True):
            book_data = get_all_details()
            df = pd.DataFrame(book_data)
            df.to_sql('books', engine, if_exists='replace', index=True, index_label='id')
            df.to_csv('data/books.csv', index=True, index_label='id')
            return df

buttons = st.columns(2, gap=None, width=500)

with buttons[0]:
    scrap = st.button('Realizar Scraping', width="stretch")
with buttons[1]:
    listar_csv = st.button('Listar Dados pelo CSV', width="stretch")

if scrap:
    df_url = import_df_to_db()

    df = pd.read_csv(df_url, index_col='id')

    st.dataframe(data=df, width='content', hide_index=True, column_config={
        'price': st.column_config.NumberColumn(format='R$%.2f'),
        'image': st.column_config.ImageColumn(width=110)
    })
    setar_metrica()
    st.session_state['csv_data'] = 1

if listar_csv:
    if st.session_state['csv_data'] == 0:
        st.error('Dados inexistentes, por favor, rode o web scraping para preencher o CSV.')
    else:
        setar_metrica()
        df = pd.read_csv('../data/books.csv')
        st.dataframe(data=df, width='content', hide_index=True, column_config={
            'price': st.column_config.NumberColumn(format='R$%.2f'),
            'image': st.column_config.ImageColumn(width=110)
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