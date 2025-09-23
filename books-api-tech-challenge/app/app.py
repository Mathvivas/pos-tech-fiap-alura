from flask import Flask
from models import db
import pandas as pd
from models import Book
from flask_jwt_extended import JWTManager
from flasgger import Swagger

app = Flask(__name__)
app.config.from_object('config')

db.init_app(app)

swagger = Swagger(app)
jwt = JWTManager(app)

from routes import *

if __name__ == '__main__':
    app.run(debug=True)