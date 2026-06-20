"""
Configurações centrais do projeto.
Todas as constantes ficam aqui — nunca hardcoded nos módulos.
"""
from pathlib import Path

ROOT         = Path(__file__).parent
DATA_KAGGLE  = ROOT / "data" / "kaggle"
DATA_PROC    = ROOT / "data" / "processed"
DATA_SYNTH   = ROOT / "data" / "synthetic_enrichment"
DATA_GOLDEN  = ROOT / "data" / "golden_set"
LOGS_DIR     = ROOT / "logs"
MODELS_DIR   = ROOT / "models"
REPORTS_DIR  = ROOT / "reports"

SEED         = 42
TARGET_COL   = "y"
DURATION_COL = "duration"   # coluna de leakage — sempre descartar

CAT_COLS  = ["job","marital","education","default",
             "housing","loan","contact","month","poutcome"]
NUM_COLS  = ["age","campaign","pdays_clean","previous","contacted_before"]
MACRO_COLS = ["emp.var.rate","cons.price.idx","cons.conf.idx",
              "euribor3m","nr.employed"]

ARMS = ["dep_6m_8pct","dep_12m_10pct","reativacao","cashback","previdencia"]
ARM_FEATURES = {
    "dep_6m_8pct":   {"duration_months": 6,  "rate": 0.08},
    "dep_12m_10pct": {"duration_months": 12, "rate": 0.10},
    "reativacao":    {"duration_months": 3,  "rate": 0.07},
    "cashback":      {"duration_months": 0,  "rate": 0.02},
    "previdencia":   {"duration_months": 24, "rate": 0.06},
}

# True conversion rates (usadas na simulação sintética)
ARM_TRUE_RATES = {
    "dep_6m_8pct":   0.18,
    "dep_12m_10pct": 0.14,
    "reativacao":    0.28,
    "cashback":      0.09,
    "previdencia":   0.12,
}

MLFLOW_EXPERIMENT = "datathon-jyb-bandit"
POLICY_VERSION    = "v1.0"

# Delayed rewards: distribuição exponencial truncada
REWARD_HORIZON_DAYS = 30
REWARD_MEAN_DAYS    = 7