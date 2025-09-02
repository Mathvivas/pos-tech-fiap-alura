from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flasgger import Swagger
from flask_jwt_extended import JWTManager

app = Flask(__name__)
app.config.from_object('config')
swagger = Swagger(app)

db = SQLAlchemy(app)
jwt = JWTManager(app)

from routes import *

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        #print('Banco de dados criado!')
        app.run(debug=True)