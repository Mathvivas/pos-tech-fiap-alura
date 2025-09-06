from flask import request, jsonify
from app import app, db
from models.book import Book

# Lista todos os livros disponíveis na base (definir paginação)
@app.route('/api/v1/books', methods=['GET'])
def get_books():
    
    return 

# get /api/v1/books/{id}
# Retorna detalhes completos de um livro específico pelo ID
@app.route('/api/v1/books/<int:book_id>', methods=['GET'])
def get_book_detail(book_id):

    return

# get /api/v1/books/search?title={title}&catgeory={category}
# Busca livros por título e/ou categoria
@app.route('/api/v1/books/search', methods=['GET'])
def get_book_by_title_or_category_or_both():

    return

# get /api/v1/categories
# Lista todas as categorias de livros disponíveis
@app.route('/api/v1/categories', methods=['GET'])
def get_categories():

    return

# get /api/v1/health
# Verifica status da API e conectividade com os dados
@app.route('/api/v1/health', methods=['GET'])
def check_system():

    return