import os

SWAGGER = {
    'title': 'API de Livros',
    'uiversion': 3
}

BASE_DIR = os.path.abspath(os.path.dirnmae(__file__))
SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'books.db')}"
SQLALCHEMY_TRACK_MODIFICATIONS = False