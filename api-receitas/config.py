import os

SECRET_KEY = 'sua_chave_secreta'
CACHE_TYPE = 'simple'
SWAGGER = {
    'title': 'Catálogo de Receitas Gourmet',
    'uiversion': 3
}
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'recipes.db')}"
SQLALCHEMY_TRACK_MODIFICATIONS = False
JWT_SECRET_KEY = 'sua_chave_jwt_secreta'