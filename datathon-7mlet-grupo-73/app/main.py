"""
ETAPA 5 - API FastAPI
Expõe /decide, /reward e /health com log auditável.
"""
import json
import uuid
import datetime
import sys
from pathlib import Path
import pickle

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from pydantic import BaseModel
import torch

from sklearn.preprocessing import MinMaxScaler

from src_config import *
from model import ConversionNet, NeuralThompsonSampling, prepare_features

app = FastAPI(
    title='Datathon 7MLET - Bandit API',
    description='Plataforma de experimentação adaptativa com Thompson Sampling',
    version=POLICY_VERSION
)

# Estado global
_bandit =       None
_encoders =     None
_scaler =       None
_arm_scaler =   None
_feature_cols = None

# ══════════════════════════════════════════════════════════════════
# Schemas Pydantic
# ══════════════════════════════════════════════════════════════════

class DecideRequest(BaseModel):
    client_features: dict
    policy_version: str = POLICY_VERSION

    class Config:
        json_schema_extra = {
            'example': {
                'client_features': {
                    'age': 42, 'campaign': 1,
                    'pdays': -1, 'previous': 0, 'job': 2,
                    'marital': 1, 'education': 3, 'default': 0,
                    'housing': 1, 'loan': 0, 'contact': 2,
                    'month': 4, 'poutcome': 0,
                },
                'policy_version': 'v1.0'
            }
        }

class RewardRequest(BaseModel):
    event_id:   str
    arm:        str
    reward:     int

    class Config:
        json_schema_extra = {
            'example': {
                'event_id': 'abc-123',
                'arm':      'dep_6m_8pct',
                'reward':   1,
            }
        }

# ══════════════════════════════════════════════════════════════════
# Log Auditável
# ══════════════════════════════════════════════════════════════════

def write_log(entry: dict):
    LOGS_DIR.mkdir(exist_ok=True)
    log_path = LOGS_DIR / 'decisions.jsonl'
    with open(log_path, 'a') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')

# ══════════════════════════════════════════════════════════════════
# Startup
# ══════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Carrega modelo e artefatos salvos pelo pipeline
    Em produção: carrega do Azure Blob / MLflow Registry
    """
    global _bandit, _encoders, _scaler, _arm_scaler, _feature_cols

    model_path = MODELS_DIR / 'conversion_net.pt'
    if not model_path.exists():
        print('AVISO: modelo não encontrado - API em modo degradado.')
        return
    
    checkpoint      = torch.load(model_path, map_location='cpu')
    model           = ConversionNet(
        input_dim = checkpoint['input_dim'],
        hidden    = checkpoint['hidden'],
        drop      = checkpoint['drop'],
    )
    model._load_from_state_dict(checkpoint['model_state'])
    model.eval()

    # Carrega artefatos de pré-processamento
    artifacts_path = MODELS_DIR / 'preprocessing.pkl'
    if artifacts_path.exists():
        with open(artifacts_path, 'rb') as f:
            arts = pickle.load(f)

        _encoders       = arts['encoders']
        _scaler         = arts['scaler']
        _arm_scaler     = arts['arm_scaler']
        _feature_cols   = arts['feature_cols']

        _bandit = NeuralThompsonSampling(
            model           = model,
            arms            = ARMS,
            scaler          = _scaler,
            arm_scaler      = _arm_scaler,
            feature_cols    = _feature_cols,
            arm_features    = ARM_FEATURES,
            n_mc            = 30,
        )
        print(f'Bandit carregado: {len(ARMS)} braços | input_dim = {checkpoint['input_dim']}')
    else:
        print('AVISO: artefatos de pré-processamento não encontrados.')

# ══════════════════════════════════════════════════════════════════
# Endpoints
# ══════════════════════════════════════════════════════════════════

@app.get('/health')
def health():
    return {
        'status':           'ok',
        'model_loaded':     _bandit is not None,
        'policy_version':   POLICY_VERSION,
        'timestamp':        datetime.datetime.now().isoformat(),
    }

@app.post('/decide')
def decide(req: DecideRequest):
    """
    Recebe contexto do cliente e retorna a oferta escolhida pelo bandit.
    Gera log auditável com reason_codes, braço e versão da política.
    """
    if _bandit is None:
        raise HTTPException(503, 'Modelo não carregado - execute o pipeline primeiro.')
    
    try:
        decisao  = _bandit.choose(req.client_features, req.policy_version)
        event_id = str(uuid.uuid4())

        log_entry = {
            "event_id":       event_id,
            "timestamp":      datetime.datetime.now().isoformat(),
            "arm_chosen":     decisao["arm_chosen"],
            "policy_version": decisao["policy_version"],
            "reason_codes":   decisao["reason_codes"],
            "estimates":      decisao["estimates"],
            "client_context": req.client_features,
        }
        write_log(log_entry)
 
        return {"event_id": event_id, **decisao}
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise HTTPException(500, f'Erro interno: {e}')
    
@app.post('/reward')
def register_reward(req: RewardRequest):
    """
    Registra a recompensa observada (pode ser delayed).
    Acumula no replay_buffer para retreino periódico.
    """
    if _bandit is None:
        raise HTTPException(503, 'Modelo não carregado.')
    
    if req.arm not in ARMS:
        raise HTTPException(422, f'Braço inválido: {req.arm}. Válidos: {ARMS}.')
    
    if req.reward not in (0, 1):
        raise HTTPException(422, 'reward deve ser 0 ou 1.')
    
    log_entry = {
        "event_id":  req.event_id,
        "arm":       req.arm,
        "reward":    req.reward,
        "timestamp": datetime.datetime.now().isoformat(),
        "type":      "reward",
    }
    write_log(log_entry)

    # Retreino automático se buffer atingir 100 amostras
    if len(_bandit.replay_X) >= 100:
        _bandit.retrain(min_samples=50)

    return {
        'status':       'ok',
        'event_id':     req.event_id,
        'buffer_size':  len(_bandit.replay_X),
    }

@app.get("/arms")
def list_arms():
    """Lista os braços disponíveis com suas taxas estimadas atuais."""
    return {
        "arms":           ARMS,
        "arm_features":   ARM_FEATURES,
        "policy_version": POLICY_VERSION,
    }