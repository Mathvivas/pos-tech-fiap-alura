import os
from pathlib import Path

SWAGGER = {
    'title': 'API de Livros',
    'uiversion': 3
}

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'books.db')}"
SQLALCHEMY_TRACK_MODIFICATIONS = False

APP_FOLDER = Path(__file__).parent

CSV_FILE_PATH = APP_FOLDER.parent / "data" / "books.csv"
CSV_FILE_PATH_EMBEDDINGS = APP_FOLDER.parent / "data" / "books_embeddings.csv"

JWT_SECRET_KEY = 'secret_key'