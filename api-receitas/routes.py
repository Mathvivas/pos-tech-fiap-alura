from flask import request, jsonify
from app import app, db
from models.recipe import Recipe
from models.user import User
from flask_jwt_extended import (
    create_access_token,
    jwt_required, get_jwt_identity
)

@app.route('/register', methods=['POST'])
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
        return jsonify({'error': 'User already exists'}), 400
    new_user = User(username=data['username'], password=data['password'])
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'msg': 'User created'}), 201


@app.route('/login', methods=['POST'])
def login():
    """
    Faz login do usuário e retorna um JWT.
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
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()
    if user and user.password == data['password']:
        # Converter o ID para string
        token = create_access_token(identity=str(user.id))
        return jsonify({'access_token': token}), 200
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    # Retorna o 'identity' usado na criação do token
    current_user_id = get_jwt_identity()
    return jsonify({'msg': f'Usuário com ID {current_user_id} acessou a rota protegida'}), 200


@app.route('/recipes', methods=['POST'])
@jwt_required()
def create_recipe():
    """
    Cria uma nova receita.
    ---
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        schema:
            type: object
            required: true
            properties:
                title:
                    type: string
                ingredients:
                    type: string
                time_minutes:
                    type: integer
                description:
                    type: string
        responses:
            201:
                description: Receita criada com sucesso
            401:
                description: Token não fornecido ou inválido
    """
    data = request.get_json()
    current_user_id = get_jwt_identity()
    new_recipe = Recipe(
        title=data['title'],
        ingredients=data['ingredients'],
        time_minutes=data['time_minutes'],
        description=data['description'],
        usuario_id=current_user_id
    )
    db.session.add(new_recipe)
    db.session.commit()
    return jsonify({'msg': 'Recipe created'}), 201


@app.route('/recipes', methods=['GET'])
# in: query --> supports simple fields (int, string, etc)
def get_recipe():
    """
    Lista receitas com filtros opcionais.
    ---
    parameters:
      - in: query
        name: ingredients
        type: string
        required: false
        description: Filtra por ingrediente
      - in: query
        name: max_time
        type: integer
        required: false
        description: Tempo máximo de preparo (minutos)
        responses:
            200:
                description: Lista de receitas filtradas
                schema:
                    type: array
                    items:
                        type: object
                        properties:
                            id:
                                type: integer
                            title:
                                type: string
                            time_minutes:
                                type: integer
    """
    # Gets the arguments informed in the path
    ingredients = request.args.get('ingredients')
    max_time = request.args.get('max_time', type=int)

    query = Recipe.query
    if ingredients:
        query = query.filter(Recipe.ingredients.ilike(f'%{ingredients}'))
    if max_time is not None:
        query = query.filter(Recipe.time_minutes <= max_time)

    recipes = query.all()
    return jsonify([
        {
        'id': r.id,
        'title': r.title,
        'ingredients': r.ingredients,
        'time_minutes': r.time_minutes
        }
        for r in recipes
    ])

@app.route('/recipes/<int:recipe_id>', methods=['PUT'])
@jwt_required()
# in: path --> only supports int and string fields
def update_recipe(recipe_id):
    """
    Atualiza uma receita existente.
    ---
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: recipe_id
        required: true
        type: integer
      - in: body
        name: body
        schema:
            type: object
            properties:
                title:
                    type: string
                ingredients:
                    type: string
                time_minutes:
                    type: integer
        responses:
            200:
                description: Receita atualizada
            401:
                description: Token não fornecido ou inválido
            404:
                description: Receita não encontrada
    """
    data = request.get_json()
    # Get the whole recipe based on the id
    recipe = Recipe.query.get_or_404(recipe_id)
    if 'title' in data:
        recipe.title = data['title']
    if 'ingredients' in data:
        recipe.ingredients = data['ingredients']
    if 'time_minutes' in data:
        recipe.time_minutes = data['time_minutes']

    db.session.commit()
    return jsonify({'msg': 'Recipe udated'}), 200


@app.route('/recipes/<int:recipe_id>', methods=['DELETE'])
@jwt_required()
# in: path --> only supports int and string fields
def delete_recipe(recipe_id):
    """
    Deleta uma receita existente.
    ---
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: recipe_id
        required: true
        type: integer
        responses:
            200:
                description: Receita deletada
            401:
                description: Token não fornecido ou inválido
            404:
                description: Receita não encontrada
    """
    recipe = Recipe.query.get_or_404(recipe_id)
    db.session.delete(recipe)
    db.session.commit()
    return jsonify({'msg': 'Recipe deleted'}), 200