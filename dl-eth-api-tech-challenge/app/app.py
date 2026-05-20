from flask import Flask
from flasgger import Swagger
from flask_cors import CORS
from flask import send_from_directory
import logging
from pathlib import Path
import sys
import os
import torch
import joblib
from model import LSTM

APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

try:
    from .predicao import predict_future_from_history
except ImportError:
    from predicao import predict_future_from_history

app = Flask(__name__)
try:
    from . import config as app_config
except ImportError:
    import config as app_config

app.config.from_object(app_config)
app.json.ensure_ascii = False

MODEL_WEIGHTS_PATH = APP_DIR / 'model' / 'model_weights.pth'
SCALER_PATH = APP_DIR / 'model' / 'scaler.pkl'
INVERSE_SCALER_PATH = APP_DIR / 'model' / 'inverse_scaler.pkl'

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    handlers=[
                        logging.FileHandler('logging.info', mode='w'),
                        logging.StreamHandler(sys.stdout),
                    ])

logger = logging.getLogger()

CORS(app)

model = None
model_load_error = None

logger.info(f'MODEL_WEIGHTS_PATH: {MODEL_WEIGHTS_PATH} (exists: {MODEL_WEIGHTS_PATH.exists()})')
logger.info(f'SCALER_PATH: {SCALER_PATH} (exists: {SCALER_PATH.exists()})')
logger.info(f'INVERSE_SCALER_PATH: {INVERSE_SCALER_PATH} (exists: {INVERSE_SCALER_PATH.exists()})')

try:
    model = LSTM(2, 32, 2, 10)
    state_dict = torch.load(MODEL_WEIGHTS_PATH, map_location='cpu', weights_only=True)
    model.load_state_dict(state_dict)
    model.eval()
    total_params = sum(p.numel() for p in model.parameters())
    param_sum = sum(p.sum().item() for p in model.parameters())
    logger.info(f'Modelo carregado com sucesso: {total_params} params, soma dos pesos: {param_sum:.6f}')
except Exception as exc:
    model = None
    model_load_error = str(exc)
    logger.exception('Falha ao carregar o modelo')

scaler = joblib.load(SCALER_PATH)
inverse_scaler = joblib.load(INVERSE_SCALER_PATH)

logger.info(f'Scaler data_min_: {scaler.data_min_}, data_max_: {scaler.data_max_}')
logger.info(f'Inverse scaler data_min_: {inverse_scaler.data_min_}, data_max_: {inverse_scaler.data_max_}')

app.config['MODEL'] = model
app.config['SCALER'] = scaler
app.config['INVERSE_SCALER'] = inverse_scaler
app.config['PREDICT_FUNC'] = predict_future_from_history
app.config['MODEL_LOAD_ERROR'] = model_load_error

try:
    from .routes.routes import api_bp
except ImportError:
    from routes.routes import api_bp

app.register_blueprint(api_bp)

# Serve Vue SPA from static/dist
static_dir = APP_DIR / 'static' / 'dist'
if static_dir.exists():
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_spa(path):
        """Serve SPA files or fallback to index.html for client-side routing."""
        dist_path = static_dir / path
        if path and dist_path.exists() and dist_path.is_file():
            return send_from_directory(str(static_dir), path)
        return send_from_directory(str(static_dir), 'index.html')

# Inicializa o Swagger somente após registrar as rotas.
swagger = Swagger(app, config=app.config['SWAGGER_CONFIG'])

if __name__ == '__main__':
    logger.info('Aplicação iniciada')
    # app.run(host='0.0.0.0', port=8080)
    app.run(debug=False)