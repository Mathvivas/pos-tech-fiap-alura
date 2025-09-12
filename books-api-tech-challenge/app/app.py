from flask import Flask
from models import db
import pandas as pd
from sqlalchemy import create_engine
from models import Book
from flask_jwt_extended import JWTManager
from flasgger import Swagger

app = Flask(__name__)
app.config.from_object('config')

db.init_app(app)

swagger = Swagger(app)
jwt = JWTManager(app)

def import_csv_to_db():
    with app.app_context():
        db.create_all()

        if Book.query.first():
            print('Database already contains books. Skipping CSV import.')
            return

        df = pd.read_csv(app.config['CSV_FILE_PATH'])
        engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
        df.to_sql('books', engine, if_exists='append', index=False)

from routes import *

if __name__ == '__main__':
    import_csv_to_db()
    app.run(debug=True)