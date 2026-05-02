import os

SWAGGER_CONFIG = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec_1",
            "route": "/apispec_1.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs/",
    "title": "API de Previsão de Preço da Ethereum",
    "description": "API para prever o preço da Ethereum em dólares utilizando dados históricos de preço",
    "version": "1.0.0",
    "contact": {
        "name": "Matheus Lopes Vivas",
        "url": "https://github.com/Mathvivas",
        "email": "mathvivas@hotmail.com"
    }
}

JWT_SECRET_KEY = 'secret-key'