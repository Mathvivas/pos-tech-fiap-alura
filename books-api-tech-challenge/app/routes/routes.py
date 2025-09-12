from flask import request, jsonify
from app import app, db
from models import Book, User
from sqlalchemy import func
import json
from flask_jwt_extended import (
    create_access_token,
    jwt_required, get_jwt_identity
)

# Lista todos os livros disponíveis na base (definir paginação)
@app.route('/api/v1/books', methods=['GET'])
@jwt_required()
def get_books():
    """
    Lista todos os livros que estão disponíveis.
    ---
    security:
      - BearerToken: []
        responses:
            200:
                description: Livros retornados com sucesso
            401:
                description: Token não fornecido ou inválido
            500:
                description: Erro no servidor
    """
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
@jwt_required()
def get_book_detail(book_id):
    """
    Lista os detalhes completos de um livro específico pelo ID.
    ---
    security:
      - BearerToken: []
    parameters:
      - in: path
        name: book_id
        required: true
        type: integer
        responses:
            200:
                description: Detalhes obtidos com sucesso
            401:
                description: Token não fornecido ou inválido
    """
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
@jwt_required()
def get_book_by_title_or_category_or_both():
    """
    Lista livros com filtros de título e/ou categoria.
    ---
    security:
      - BearerToken: []
    parameters:
      - in: query
        name: title
        required: false
        type: string
        description: Qualquer palavra que esteja contida no título
      - in: query
        name: category
        required: false
        type: string
        description: Qualquer palavra que esteja contida na categoria
        responses:
            200:
                description: Livros obtidos com sucesso
            401:
                description: Token não fornecido ou inválido
            404:
                description: Não há livros com os filtros definidos
    """
    title = request.args.get('title')
    category = request.args.get('category')

    query = Book.query
    if title:
        query = query.filter(Book.title.ilike(f'%{title}%'))
    if category:
        query = query.filter(Book.category.ilike(f'%{category}%'))

    books = query.all()

    if books == []:
        return jsonify({'msg': 'Não há livros com esse nome ou categoria.'}), 404
    
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
    ]), 200

# Lista todas as categorias de livros disponíveis
@app.route('/api/v1/categories', methods=['GET'])
@jwt_required()
def get_categories():
    """
    Lista todos as categorias.
    ---
    security:
      - BearerToken: []
        responses:
            200:
                description: Livros retornados com sucesso
            401:
                description: Token não fornecido ou inválido
    """
    categories = Book.query.with_entities(Book.category).distinct().all()
    return [category[0] for category in categories]

# Verifica status da API e conectividade com os dados
@app.route('/api/v1/health', methods=['GET'])
def check_system():
    """
    Verifica o status da API e a conectividade com os dados.
    ---
        responses:
            200:
                description: API está operacional e conectada ao banco de dados
            503:
                description: Falha na verificação
    """
    try:
        Book.query.filter_by(availability = 'ok').order_by(Book.title).first()
        return jsonify({'status': 'OK', 'message': 'API está operacional e conectada ao banco de dados.'}), 200
    except Exception as e:
        return jsonify({'status': 'ERROR', 'message': f'Falha na verificação: {str(e)}'}), 503

# Estatísticas gerais da coleção (total de livros, preço médio, distribuição de ratings)    
@app.route('/api/v1/stats/overview', methods=['GET'])
@jwt_required()
def get_overview():
    """
    Lista livros com filtros de título e/ou categoria.
    ---
    security:
      - BearerToken: []
        responses:
            200:
                description: Livros obtidos com sucesso
            401:
                description: Token não fornecido ou inválido
    """
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
@jwt_required()
def get_category_stats():
    """
    Lista estatísticas detalhadas por categoria.
    ---
    security:
      - BearerToken: []
        responses:
            200:
                description: Estatísticas obtidas com sucesso
            401:
                description: Token não fornecido ou inválido
    """
    total_books_per_category = db.session.query(Book.category, func.count(Book.category)).group_by(Book.category).all()
    price_per_category = db.session.query(Book.category, func.round(func.avg(Book.price), 2)).group_by(Book.category).all()
    return jsonify({
        'Total de Livros por Categoria': json.dumps(dict(total_books_per_category)),
        'Preço por Categoria': json.dumps(dict(price_per_category))
    }), 200

# Lista os livros com melhor avaliação (rating mais alto)
@app.route('/api/v1/books/top-rated', methods=['GET'])
@jwt_required()
def get_rop_rated_books():
    """
    Lista os livros com melhor avaliação.
    ---
    security:
      - BearerToken: []
        responses:
            200:
                description: Livros obtidos com sucesso
            401:
                description: Token não fornecido ou inválido
    """
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
@jwt_required()
def get_price_ranged_books():
    """
    Filtra livros dentro de uma faixa de preço específica.
    ---
    security:
      - BearerToken: []
    parameters:
      - in: query
        name: min
        required: false
        type: float
        description: Valor do preço mínimo
      - in: query
        name: max
        required: false
        type: float
        description: Valor do preço máximo
        responses:
            200:
                description: Livros obtidos com sucesso
            401:
                description: Token não fornecido ou inválido
            404:
                description: Não há livros na faixa de preço definida
    """
    min = request.args.get('min', type=float)
    max = request.args.get('max', type=float)

    query = Book.query
    if min is not None:
        query = query.filter(Book.price >= min)
    if max is not None:
        query = query.filter(Book.price <= max)

    books = query.all()

    if books == []:
        return jsonify({'msg': 'Não há livros nessa faixa de preço.'}), 404
    
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
    ]), 200

@app.route('/api/v1/auth/register', methods=['POST'])
def register_user():
    """
    Registra um novo usuário.
    ---
    parameters:
      - in: body
        name: body
        required: true
        schema:
            type: object
            properties:
                username:
                    type: string
                password:
                    type: string
        responses:
            201:
                description: Usuário criado com sucesso
            400:
                description: Usuário já existe
    """
    data = request.get_json()
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Usuário já existe'}), 400

    is_strong, messages = User.check_password_strength(data['password'])

    if not is_strong:
        return jsonify({'sucesso': False, 'errors': messages}), 400

    password = User.set_password(password=data['password'])
    new_user = User(username=data['username'], password=password)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'msg': 'Usuário criado'}), 201

@app.route('/api/v1/auth/login', methods=['POST'])
def get_token():
    """
    Faz login do usuário e recebe um JWT.
    ---
    parameters:
      - in: body
        name: body
        required: true
        schema:
            type: object
            properties:
                username:
                    type: string
                password:
                    type: string
        responses:
            201:
                description: Login bem sucedido, retorna JWT
            400:
                description: Credenciais inválidas
    """
    try:
        data = request.get_json()
        user = User.query.filter_by(username=data['username']).first()
        password = User.check_password(username=data['username'], password=data['password'])
        if user and password:
            token = create_access_token(identity=str(user.id))
            return jsonify({'access_token': token}), 201
    except:
        return jsonify({'error': 'Credenciais inválidas.'}), 401

# @app.route('/api/v1/auth/refresh', methods=['GET'])
# def refresh_token():
#     current_user_id = get_jwt_identity()
#     if current_user_id:
#         token = create_access_token(identity=str(current_user_id))
#         return jsonify({'token': token}), 200
#     return jsonify({'msg': 'Usuário desconectado, faça login.'})