from flask import request, jsonify
from app import app, db
from models import Book
from sqlalchemy import func
import json

# Lista todos os livros disponíveis na base (definir paginação)
@app.route('/api/v1/books', methods=['GET'])
def get_books():
    try:
        page = request.args.get('page', type=int)
        books = Book.query.filter_by(availability = 'ok').order_by(Book.title)

        pagination = db.paginate(
            books,
            page=page,
            per_page=20,
            error_out=False
        )

        books_on_page = pagination.items
        book_list = [
            {
                'Id': book.id,
                'Title': book.title,
                'Price': book.price,
                'Rating': book.rating,
                'Availability': book.availability,
                'Category': book.category,
            }
            for book in books_on_page
        ]

        return jsonify(
            {
                'items': book_list,
                'meta': {
                    'page': pagination.page,
                    'per_page': pagination.per_page,
                    'total_pages': pagination.pages,
                    'has_next': pagination.has_next,
                    'has_prev': pagination.has_prev
                }
            }
        ), 200
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

# Estatísticas gerais da coleção (total de livros, preço médio, distribuição de ratings)    
@app.route('/api/v1/stats/overview', methods=['GET'])
def get_overview():
    total_books = Book.query.count()
    avg_price = db.session.query(func.round(func.avg(Book.price), 2)).scalar()
    rating_distribution = db.session.query(Book.rating, func.count(Book.rating)).group_by(Book.rating).all()
    return jsonify({
        'Total de Livros': total_books,
        'Preço Médio': f'R$ {avg_price}',
        'Distribuição de Notas': json.dumps(dict(rating_distribution)) # variável sozinha retorna um Objeto Row
    }), 200

# Estatísticas detalhadas por categoria (quantidade de livros por categoria, preços por categoria)
@app.route('/api/v1/stats/categories', methods=['GET'])
def get_category_stats():
    total_books_per_category = db.session.query(Book.category, func.count(Book.category)).group_by(Book.category).all()
    price_per_category = db.session.query(Book.category, func.round(func.avg(Book.price), 2)).group_by(Book.category).all()
    return jsonify({
        'Total de Livros por Categoria': json.dumps(dict(total_books_per_category)),
        'Preço por Categoria': json.dumps(dict(price_per_category))
    }), 200

# Lista os livros com melhor avaliação (rating mais alto)
@app.route('/api/v1/books/top-rated', methods=['GET'])
def get_rop_rated_books():
    top_rated = Book.query.filter_by(rating = 'Five').all()
    return jsonify([
        {
        'Título': top.title,
        'Nota': top.rating,
        'Disponibilidade': top.availability
        }
        for top in top_rated
    ]), 200

# Filtra livros dentro de uma faixa de preço específica
@app.route('/api/v1/books/price-range', methods=['GET'])
def get_price_ranged_books():
    min = request.args.get('min', type=float)
    max = request.args.get('max', type=float)

    query = Book.query
    if min is not None:
        query = query.filter(Book.price >= min)
    if max is not None:
        query = query.filter(Book.price <= max)

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