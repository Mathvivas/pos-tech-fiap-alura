from flask import Flask
from models import db
import pandas as pd
from sqlalchemy import create_engine

app = Flask(__name__)
app.config.from_object('config')

db.init_app(app)

def import_csv_to_db():
    with app.app_context():
        db.create_all()

        df = pd.read_csv(app.config['CSV_FILE_PATH'])
        engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
        df.to_sql('books', engine, if_exists='replace', index=False)

if __name__ == '__main__':
    import_csv_to_db()
    app.run(debug=True)