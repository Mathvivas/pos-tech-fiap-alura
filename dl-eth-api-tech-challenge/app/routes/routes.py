from flask import Blueprint, request, jsonify, current_app
import pandas as pd

api_bp = Blueprint("api", __name__)


@api_bp.route('/predict', methods=['POST'])
def predict():
    """
    Preve o preco futuro com base em dados historicos fornecidos pelo usuario.
    ---
    tags:
      - Predict
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - data_referencia
            - dias_previsao
            - dias_anteriores
          properties:
            data_referencia:
              type: string
              format: date
              example: 2026-01-01
            dias_previsao:
              type: integer
              example: 10
            dias_anteriores:
              type: integer
              example: 30
    responses:
      200:
        description: Predicao realizada com sucesso.
      400:
        description: Campos obrigatorios ausentes.
      500:
        description: Erro interno ao processar a predicao.
      503:
        description: Modelo indisponivel. Verifique os artefatos em app/model e dependencias.
    """
    payload = request.get_json(silent=True) or {}
    required_fields = ['data_referencia', 'dias_previsao', 'dias_anteriores']

    missing_fields = [field for field in required_fields if field not in payload]
    if missing_fields:
        return jsonify({'message': f'Campos obrigatorios ausentes: {", ".join(missing_fields)}'}), 400

    model = current_app.config.get('MODEL')
    scaler = current_app.config.get('SCALER')
    scaler_inverse = current_app.config.get('INVERSE_SCALER')
    predict_future_from_history = current_app.config.get('PREDICT_FUNC')
    model_load_error = current_app.config.get('MODEL_LOAD_ERROR')

    if model is None or scaler is None or predict_future_from_history is None:
        message = 'Modelo indisponivel. Verifique app/model/model_weights.pth e app/model/scaler.pkl.'
        if model_load_error:
            message = f'{message} Detalhe: {model_load_error}'
        return jsonify({'message': message}), 503

    try:
        result = predict_future_from_history(
            data_referencia=payload['data_referencia'],
            dias_previsao=payload['dias_previsao'],
            dias_anteriores=payload['dias_anteriores'],
            scaler=scaler,
            scaler_inverse=scaler_inverse,
            model=model
        )
        
        result_list = [
            {
                'date': idx.strftime('%Y-%m-%d'),
                'historical_close': float(row['Historical_Close']) if not pd.isna(row['Historical_Close']) else None,
                'predicted_close': float(row['Predicted_Close']) if not pd.isna(row['Predicted_Close']) else None
            }
            for idx, row in result.iterrows()
        ]
        
        return jsonify({
            'message': 'Predicao realizada com sucesso.', 
            'data': result_list
        }), 200
    except ValueError as exc:
        return jsonify({'message': str(exc)}), 400
    except Exception:
        current_app.logger.exception('Erro ao processar /predict')
        return jsonify({'message': 'Erro interno ao processar a predicao.'}), 500


@api_bp.route('/health', methods=['GET'])
def healthcheck():
    """
    Verifica se a API esta funcionando corretamente.
    ---
    tags:
      - Healthcheck
    responses:
      200:
        description: API esta funcionando corretamente.
    """
    return jsonify({'status': 'ok'}), 200