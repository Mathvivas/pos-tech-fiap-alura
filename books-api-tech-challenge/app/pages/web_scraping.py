import requests
import streamlit as st
from app import app, db, logger
from sqlalchemy import create_engine
from models import Book
import pandas as pd
from bs4 import BeautifulSoup
import time
from streamlit_app import setar_metrica

app.config.from_object('config')
app.json.ensure_ascii = False

### Funções usadas para o web scraping

def get_category_description(url: str):
    logger.debug('Entrando na função de pegar categoria e descrição.')
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    time.sleep(1)

    category = soup.find('ul', class_='breadcrumb').find_all('li')[2].find('a').get_text()
    description = soup.find_all('p')[3].get_text()

    return category, description

def get_details() -> list:
    """
    Pega os detalhes de cada livro dentro de cada página.

    Retorna uma lista de dicionários com os detalhes de cada livro.

    Returns:
        list: Uma lista de dicionários com os detalhes de cada livro.
    """
    logger.debug('Entrando na função de pegar detalhes dos livros.')
    book_data = []
    url_books = 'https://books.toscrape.com/'
    url_raiz = 'https://books.toscrape.com/catalogue/'

    try:
        response = requests.get(url_books)
        # Achando o número de páginas
        if response.status_code == 200:
            content = response.text
            soup = BeautifulSoup(content, 'html.parser')

            pages = int(soup.find('li', class_='current').get_text(strip=True)[-2:])
    except Exception as e:
        st.error('Não foi possível encontrar a página: {e}')

    for page in range(pages):
        url = f'https://books.toscrape.com/catalogue/page-{page+1}.html'

        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        books = soup.find('ol', class_='row').find_all('li')

        for book in books:
            title = book.find('article', class_='product_pod').find('h3').find('a')['title']
            price = book.find('div', class_='product_price').find('p', class_='price_color').text[2:]
            rating = book.find('p', class_='star-rating')['class'][1]
            availability = book.find('p', class_='instock availability').find('i')['class'][0].split('-')[-1]

            link_to_book = book.find('article', class_='product_pod').find('h3').find('a')['href']
            full_link = requests.compat.urljoin(url_raiz, link_to_book)

            category, description = get_category_description(full_link)
            img = book.find('div', class_='image_container').find('a').find('img')['src']
            image = requests.compat.urljoin(url_books, img)

            book_data.append({
                'title': title,
                'description': description,
                'price': price,
                'rating': rating,
                'availability': availability,
                'category': category,
                'image': image
            })

        time.sleep(1)

    return book_data


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
    - *Descrição* (não era necessária, mas foi utilizada para dar mais informações ao modelo de Machine Learning)
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
        
        with st.spinner("Pegando os dados do site, deve demorar...", show_time=True):
            book_data = get_details()
            df = pd.DataFrame(book_data)
            df.to_sql('books', engine, if_exists='replace', index=True, index_label='id')
            df.to_csv('../data/books.csv', index=True, index_label='id')
            return df

buttons = st.columns(2, gap=None, width=500)

with buttons[0]:
    scrap = st.button('Realizar Scraping', width="stretch")
with buttons[1]:
    listar_csv = st.button('Listar Dados pelo CSV Salvo', width="stretch")

if scrap:
    setar_metrica()
    df = import_df_to_db()

    st.dataframe(data=df, width='content', hide_index=True, column_config={
        'price': st.column_config.NumberColumn(format='R$%.2f'),
        'image': st.column_config.ImageColumn(width=110)
    })

if listar_csv:
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