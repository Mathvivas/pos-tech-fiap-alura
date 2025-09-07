from flask import request, jsonify
from app import app
from models import Book

# Lista todos os livros disponíveis na base (definir paginação)
@app.route('/api/v1/books', methods=['GET'])
def get_books():
    try:
        books = Book.query.filter_by(availability = 'ok').order_by(Book.title).all()
        return jsonify([
            {
                'Id': book.id,
                'Title': book.title,
                'Price': book.price,
                'Rating': book.rating,
                'Availability': book.availability,
                'Category': book.category,
            }
            for book in books
        ]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Retorna detalhes completos de um livro específico pelo ID
@app.route('/api/v1/books/<int:book_id>', methods=['GET'])
def get_book_detail(book_id):
    book = Book.query.get_or_404(book_id, description=f'Não existe livro com o id {book_id}')
    return jsonify([
            {
                'Id': book.id,
                'Title': book.title,
                'Price': book.price,
                'Rating': book.rating,
                'Availability': book.availability,
                'Category': book.category,
                'Image': book.image
            }
        ]), 200

# Busca livros por título e/ou categoria
@app.route('/api/v1/books/search', methods=['GET'])
def get_book_by_title_or_category_or_both():
    title = request.args.get('title')
    category = request.args.get('category')

    query = Book.query
    if title:
        query = query.filter(Book.title.ilike(f'%{title}%'))
    if category:
        query = query.filter(Book.category.ilike(f'%{category}%'))

    books = query.all()
    return jsonify([
        {
            'Id': book.id,
            'Title': book.title,
            'Price': book.price,
            'Rating': book.rating,
            'Availability': book.availability,
            'Category': book.category,
            'Image': book.image
        }
        for book in books
    ])

# Lista todas as categorias de livros disponíveis
@app.route('/api/v1/categories', methods=['GET'])
def get_categories():
    categories = Book.query.with_entities(Book.category).distinct().all()
    return [category[0] for category in categories]

# Verifica status da API e conectividade com os dados
@app.route('/api/v1/health', methods=['GET'])
def check_system():
    try:
        Book.query.filter_by(availability = 'ok').order_by(Book.title).first()
        return jsonify({'status': 'OK', 'message': 'API está operacional e conectada ao banco de dados.'}), 200
    except Exception as e:
        return jsonify({'status': 'ERROR', 'message': f'Falha na verificação: {str(e)}'}), 503