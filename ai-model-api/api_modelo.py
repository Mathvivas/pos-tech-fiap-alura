import logging

from flask import Flask
import joblib
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from Predictions import Base

app = Flask(__name__)
app.config.from_object('config')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('api_modelo')

engine = create_engine(app.config['DB_URL'], echo=False)

SessionLocal = sessionmaker(bind=engine)

# Cria as tabelas no banco (em produção -> utilizar Alembic)
Base.metadata.create_all(engine)

model = joblib.load('modelo_iris.pkl')
logger.info('Modelo carregado com sucesso.')

from routes import *

if __name__ == '__main__':
    app.run(debug=True)
