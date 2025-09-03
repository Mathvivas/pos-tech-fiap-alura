from flask import request, jsonify
from api_modelo import app, logger, model, SessionLocal
import config
import numpy as np
from tools import create_token, token_required
from Predictions import Predictions

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json(force=True)
    username = data.get('username')
    password = data.get('password')
    if username == config.TEST_USERNAME and password == config.TEST_PASSWORD:
        token = create_token(username)
        return jsonify({'token': token})
    else:
        return jsonify({'error': 'Credenciais inválidas'}), 401

predictions_cache = {}

@app.route('/predict', methods=['post'])
@token_required
def predict():
    """
    Endpoint protegido por token para obter predição.
    Corpo (JSON):
    {
        "sepal_length": 5.1,
        "sepal_width": 3.5,
        "petal_length": 1.4,
        "petal_width": 0.2
    }
    """
    data = request.get_json(force=True)
    try:
        sepal_length = float(data['sepal_length'])
        sepal_width = float(data['sepal_width'])
        petal_length = float(data['petal_length'])
        petal_width = float(data['petal_width'])
    except (ValueError, KeyError) as e:
        logger.error(f'Dados de entrada inválidos: {e}')
        return jsonify({'error': 'Dados inválidos, verifique parâmetros'}), 400
    
    # Verifica se já está no cache
    features = (sepal_length, sepal_width, petal_length, petal_width)
    if features in predictions_cache:
        logger.info(f'Cache hit para {features}')
        predicted_class = predictions_cache[features]
    else:
        # Rodar o modelo
        input_data = np.array([features])
        prediction = model.predict(input_data)
        predicted_class = int(prediction[0])
        # Armazenar no cache
        predictions_cache[features] = predicted_class
        logger.info(f'Cache updated para {features}')
    
    # Armazenar em DB
    db = SessionLocal()
    new_pred = Predictions(
        sepal_length=sepal_length,
        sepal_width=sepal_width,
        petal_length=petal_length,
        petal_width=petal_width,
        predicted_class=predicted_class
    )
    db.add(new_pred)
    db.commit()
    db.close()

    return jsonify({'prediction': predicted_class})


@app.route('/predictions', methods=['GET'])
@token_required
def list_predictions():
    """
    Lista as predições armazenadas no banco.
    Parâmetros opcionais (via query string):
      - limit (int): quantos registros retornar, padrão 10
      - offset (int): a partir de qual registro começar, padrão 0
    Exemplo:
      /predictions?limit=5&offset=10
    """
    limit = int(request.args.get('limit', default=10))
    offset = int(request.args.get('offset', default=0))
    db = SessionLocal()
    preds = db.query(Predictions).order_by(Predictions.id.desc()).limit(limit).offset(offset).all()
    db.close()
    results = []
    for p in preds:
        results.append({
            'id': p.id,
            'sepal_length': p.sepal_length,
            'sepal_width': p.sepal_width,
            'petal_length': p.petal_length,
            'petal_width': p.petal_width,
            'predicted_class': p.predicted_class,
            'created_at': p.created_at.isoformat()
        })
    return jsonify(results)