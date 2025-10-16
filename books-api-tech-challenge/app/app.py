from flask import Flask
from models import db
from flask_jwt_extended import JWTManager
from flasgger import Swagger
import logging

app = Flask(__name__)
app.config.from_object('config')

logging.basicConfig(filename='logging.info',
                    level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%d-%m-%Y %H:%M:%S', 
                    filemode='w')

logger = logging.getLogger()

db.init_app(app)

swagger = Swagger(app)
jwt = JWTManager(app)

from routes import *

def run_flask():
    logger.info('Aplicação iniciada.')
    app.run(debug=True)

if __name__ == '__main__':
    run_flask()