"""
ETAPA 3 - Modelagem: prepare_features, ConversionNet, train_model,
Baseline + Thompson Sampling contextual
"""
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.preprocessing import StandardScaler, LabelEncoder, MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, average_precision_score
import mlflow
import mlflow.pytorch
import warnings

from src_config import *
from data.kaggle import run as run_step1
from data.synthetic_enrichment import run as run_step2

warnings.filterwarnings("ignore")
torch.manual_seed(SEED)
np.random.seed(SEED)

# ══════════════════════════════════════════════════════════════════
# PREPARAÇÃO DE FEATURES
# ══════════════════════════════════════════════════════════════════

def prepare_features(df: pd.DataFrame) -> tuple:
    """
    Transforma o DataFrame JYB em arrays prontos para treino.
    Retorna X, y, encoders, scaler, feature_cols.
    """
    df = df.copy()

    # pdays=-1 significa "nunca contactado" — não é um número real
    df["contacted_before"] = (df["pdays"] != -1).astype(int)
    df["pdays_clean"]      = df["pdays"].clip(lower=0)

    encoders = {}
    for col in CAT_COLS:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col].astype(str))
        encoders[col] = le

    available_macro = [c for c in MACRO_COLS if c in df.columns]
    feature_cols    = NUM_COLS + CAT_COLS + available_macro

    X = df[feature_cols].values.astype(np.float32)
    y = (df["y"] == "yes").astype(int).values

    if np.isnan(X).any():
        bad = [feature_cols[i] for i in range(X.shape[1]) if np.isnan(X[:,i]).any()]
        raise ValueError(f"NaN nas colunas: {bad}")

    scaler = StandardScaler()
    X      = scaler.fit_transform(X).astype(np.float32)

    print(f"Dataset: {X.shape[0]} amostras | {X.shape[1]} features | "
          f"conversao={y.mean():.2%}")
    return X, y, encoders, scaler, feature_cols


def build_client_context(row: pd.Series, encoders: dict,
                          feature_cols: list) -> dict:
    """
    Constrói contexto completo a partir de uma linha REAL do DataFrame.
    Garante que TODAS as features existam, sem zeros artificiais.
    """
    row = row.copy()

    for col in CAT_COLS:
        if col in encoders and isinstance(row.get(col), str):
            try:
                row[col] = encoders[col].transform([row[col]])[0]
            except ValueError:
                row[col] = 0  # categoria desconhecida → classe 0

    # BUG 5: mesma lógica de pdays usada no prepare_features
    row["contacted_before"] = int(row.get("pdays", -1) != -1)
    row["pdays_clean"]      = max(0, float(row.get("pdays", 0)))

    context = {col: float(row[col]) for col in feature_cols if col in row.index}
    missing = [c for c in feature_cols if c not in context]
    if missing:
        raise ValueError(
            f"Features ausentes no contexto: {missing}\n"
            f"Use uma linha do DataFrame processado pelo prepare_features()."
        )
    return context

# ══════════════════════════════════════════════════════════════════
# MODELO PYTORCH
# ══════════════════════════════════════════════════════════════════

class ConversionNet(nn.Module):
    """
    Rede neural para predição de conversão bancária.

    SEM Sigmoid no forward() — retorna logits crus.
    LayerNorm em vez de BatchNorm1d — funciona com batch=1.
    input_dim deve incluir features de oferta (n_client + n_arm).
    """

    def __init__(self, input_dim: int, hidden: int = 64, drop: float = 0.3):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden),
            nn.LayerNorm(hidden),    # LayerNorm funciona com batch=1
            nn.ReLU(),
            nn.Dropout(drop),
            nn.Linear(hidden, hidden // 2),
            nn.LayerNorm(hidden // 2),
            nn.ReLU(),
            nn.Dropout(drop),
            nn.Linear(hidden // 2, 1),
            # SEM Sigmoid aqui
        )
        # Inicialização para evitar saturação antes do treino
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, nonlinearity="relu")
                nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Retorna logits crus — NÃO são probabilidades."""
        return self.net(x).squeeze(-1)

    def predict_with_uncertainty(self, x: torch.Tensor,
                                  n_samples: int = 30) -> tuple:
        """
        MC Dropout: n_samples passagens com dropout ATIVO.

        self.train() mantém dropout ativo durante inferência.
        torch.sigmoid() aplicado UMA VEZ para converter logits em probs.

        Retorna (mean, std) garantidos em [0, 1].
        """
        prev = self.training
        self.train()   # Dropout ATIVO

        with torch.no_grad():
            logits = torch.stack([self(x) for _ in range(n_samples)])
            probs  = torch.sigmoid(logits)  # Sigmoid UMA VEZ

        self.train(prev)  # restaura estado original

        return probs.mean(dim=0), probs.std(dim=0)

# ══════════════════════════════════════════════════════════════════
# BASELINE DETERMINÍSTICO
# ══════════════════════════════════════════════════════════════════

class DeterministicBaseline:
    """
    Política simples: sempre escolhe o braço com maior taxa histórica
    no segmento do cliente. Serve de benchmark para o Thompson Sampling.
    """
    def __init__(self, arm_true_rates: dict):
        self.rates = arm_true_rates
        self.history: list = []
 
    def choose(self, segment: str = None) -> dict:
        chosen = max(self.rates, key=self.rates.get)
        return {"arm_chosen": chosen, "policy": "deterministic_best_arm"}
 
    def update(self, arm: str, reward: int):
        self.history.append({"arm": arm, "reward": reward})
 
    def cumulative_reward(self) -> float:
        return sum(h["reward"] for h in self.history)

# ══════════════════════════════════════════════════════════════════
# TREINAMENTO COM MLFLOW
# ══════════════════════════════════════════════════════════════════

def train_model(X_client: np.ndarray, y: np.ndarray,
                arm_features: dict = ARM_FEATURES,
                epochs: int = 80, lr: float = 5e-4,
                batch_size: int = 256) -> tuple:
    """
    Treina ConversionNet expandindo o dataset por braço.
    input_dim = n_client + n_arm calculado antes de instanciar o modelo.
    split correto antes de criar tensors.
    """
    n_client  = X_client.shape[1]
    n_arm     = len(next(iter(arm_features.values())))
    input_dim = n_client + n_arm
    print(f"input_dim: {n_client} (cliente) + {n_arm} (oferta) = {input_dim}")
 
    # Scaler separado para features de oferta
    arm_vals   = np.array([list(v.values()) for v in arm_features.values()],
                           dtype=np.float32)
    arm_scaler = MinMaxScaler().fit(arm_vals)
 
    # Expande: cada cliente × cada braço
    arm_names = list(arm_features.keys())
    X_exp, y_exp = [], []
    for i, arm in enumerate(arm_names):
        a_vec = arm_scaler.transform(arm_vals[i:i+1]).flatten()
        for j in range(len(X_client)):
            X_exp.append(np.concatenate([X_client[j], a_vec]))
            y_exp.append(float(y[j]))
 
    X_exp = np.array(X_exp, dtype=np.float32)
    y_exp = np.array(y_exp, dtype=np.float32)
 
    # Split antes dos tensors
    X_tr, X_vl, y_tr, y_vl = train_test_split(
        X_exp, y_exp, test_size=0.2, random_state=SEED,
        stratify=(y_exp > 0.5).astype(int)
    )
    print(f"Treino: {len(y_tr):,} | Val: {len(y_vl):,} | "
          f"pos_tr={y_tr.mean():.2%} | pos_vl={y_vl.mean():.2%}")
 
    X_tr_t = torch.tensor(X_tr, dtype=torch.float32)
    y_tr_t = torch.tensor(y_tr, dtype=torch.float32)
    X_vl_t = torch.tensor(X_vl, dtype=torch.float32)
    y_vl_t = torch.tensor(y_vl, dtype=torch.float32)
 
    model  = ConversionNet(input_dim=input_dim)
 
    n_neg  = (y_tr < 0.5).sum()
    n_pos  = max((y_tr > 0.5).sum(), 1)
    weight = torch.tensor([n_neg / n_pos], dtype=torch.float32)
 
    # BCEWithLogitsLoss espera logits crus
    criterion = nn.BCEWithLogitsLoss(pos_weight=weight)
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, patience=10, factor=0.5
    )
    loader = torch.utils.data.DataLoader(
        torch.utils.data.TensorDataset(X_tr_t, y_tr_t),
        batch_size=batch_size, shuffle=True
    )
 
    best_auc, best_state = 0.0, None
 
    mlflow.set_experiment(MLFLOW_EXPERIMENT)
    with mlflow.start_run(run_name="conversion_net_jyb"):
        mlflow.log_params({
            "input_dim": input_dim, "hidden": 64, "drop": 0.3,
            "epochs": epochs, "lr": lr,
            "pos_weight": round(weight.item(), 2),
            "n_arms": len(arm_names),
        })
 
        for epoch in range(epochs):
            model.train()
            train_loss = 0.0
            for xb, yb in loader:
                optimizer.zero_grad()
                loss = criterion(model(xb), yb)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                train_loss += loss.item() * len(yb)
            train_loss /= len(y_tr_t)
 
            # Validação com X_vl_t correto
            model.eval()
            with torch.no_grad():
                val_logits = model(X_vl_t)
                val_loss   = criterion(val_logits, y_vl_t).item()
                val_probs  = torch.sigmoid(val_logits).numpy()
 
            val_auc = roc_auc_score((y_vl > 0.5).astype(int), val_probs)
            val_apr = average_precision_score((y_vl > 0.5).astype(int), val_probs)
            scheduler.step(val_loss)
 
            if val_auc > best_auc:
                best_auc   = val_auc
                best_state = {k: v.clone() for k, v in model.state_dict().items()}
 
            if (epoch + 1) % 10 == 0:
                print(f"  Epoch {epoch+1:3d} | train={train_loss:.4f} | "
                      f"val={val_loss:.4f} | auc={val_auc:.4f} | apr={val_apr:.4f}")
                mlflow.log_metrics({
                    "train_loss": train_loss, "val_loss": val_loss,
                    "val_auc": val_auc, "val_apr": val_apr,
                }, step=epoch+1)
 
        model.load_state_dict(best_state)
        model.eval()
 
        with torch.no_grad():
            final_probs = torch.sigmoid(model(X_vl_t)).numpy()
        final_auc = roc_auc_score((y_vl > 0.5).astype(int), final_probs)
        print(f"\nMelhor AUC: {final_auc:.4f} | "
              f"media_pred={final_probs.mean():.4f} (taxa_real={y_vl.mean():.4f})")
 
        mlflow.log_metrics({"best_auc": final_auc, "pred_mean": final_probs.mean()})
        input_example = X_vl_t[:1]
        mlflow.pytorch.log_model(
            model,
            "model",
            input_example=input_example,
            serialization_format="pickle",
        )
 
        # Salva localmente também
        model_path = MODELS_DIR / "conversion_net.pt"
        torch.save({
            "model_state": model.state_dict(),
            "input_dim":   input_dim,
            "hidden":      64,
            "drop":        0.3,
        }, model_path)
        print(f"Modelo salvo: {model_path}")
 
    return model, arm_scaler

# ══════════════════════════════════════════════════════════════════
# THOMPSON SAMPLING CONTEXTUAL
# ══════════════════════════════════════════════════════════════════

class NeuralThompsonSampling:

    def __init__(self, model: ConversionNet, arms: list,
                 scaler: StandardScaler, arm_scaler: MinMaxScaler,
                 feature_cols: list, arm_features: dict, n_mc: int = 30):
        self.model        = model
        self.arms         = arms
        self.scaler       = scaler
        self.arm_scaler   = arm_scaler   # Scaler próprio para oferta
        self.feature_cols = feature_cols
        self.arm_features = arm_features
        self.n_mc         = n_mc
        self.replay_X: list = []
        self.replay_y: list = []

    def _tensor(self, ctx: dict, arm: str) -> torch.Tensor:
        # Features do cliente normalizadas pelo scaler de treino
        c_vec = np.array([ctx[f] for f in self.feature_cols], dtype=np.float32)
        c_vec = self.scaler.transform(c_vec.reshape(1,-1)).flatten()

        # Features de oferta com scaler próprio
        a_raw = np.array(list(self.arm_features[arm].values()), dtype=np.float32)
        a_vec = self.arm_scaler.transform(a_raw.reshape(1,-1)).flatten()

        full = np.concatenate([c_vec, a_vec]).astype(np.float32)
        return torch.tensor(full).unsqueeze(0)

    def choose(self, ctx: dict, policy_version: str = "v1.0") -> dict:
        results = {}
        for arm in self.arms:
            x          = self._tensor(ctx, arm)
            mean, std  = self.model.predict_with_uncertainty(x, self.n_mc)
            mean_v     = mean.item()
            std_v      = std.item()
            # Thompson Sampling: amostra da distribuição de incerteza
            sample     = float(np.clip(
                np.random.normal(loc=mean_v, scale=max(std_v, 1e-4)), 0, 1
            ))
            results[arm] = {"mean": mean_v, "std": std_v, "sample": sample}

        chosen = max(results, key=lambda a: results[a]["sample"])
        rc     = results[chosen]

        return {
            "arm_chosen":     chosen,
            "policy_version": policy_version,
            "estimates":      {a: {"mean": round(v["mean"], 4),
                                   "std":  round(v["std"],  4)}
                               for a, v in results.items()},
            "reason_codes": {
                "estimated_conversion": round(rc["mean"] * 100, 2),
                "uncertainty_std":      round(rc["std"], 4),
                "exploring":            rc["std"] > 0.05,
                "ts_sample":            round(rc["sample"], 4),
            }
        }

    def update(self, ctx: dict, arm: str, reward: int):
        c_vec = np.array([ctx[f] for f in self.feature_cols], dtype=np.float32)
        c_vec = self.scaler.transform(c_vec.reshape(1,-1)).flatten()
        a_raw = np.array(list(self.arm_features[arm].values()), dtype=np.float32)
        a_vec = self.arm_scaler.transform(a_raw.reshape(1,-1)).flatten()
        self.replay_X.append(np.concatenate([c_vec, a_vec]))
        self.replay_y.append(float(reward))

    def retrain(self, min_samples: int = 50, lr: float = 1e-4):
        if len(self.replay_X) < min_samples:
            print(f"Buffer: {len(self.replay_X)}/{min_samples} — aguardando")
            return
        X_b  = torch.tensor(np.array(self.replay_X), dtype=torch.float32)
        y_b  = torch.tensor(self.replay_y,            dtype=torch.float32)
        n_p  = max(y_b.sum().item(), 1)
        n_n  = max((y_b < 0.5).sum().item(), 1)
        crit = nn.BCEWithLogitsLoss(
                   pos_weight=torch.tensor([n_n/n_p], dtype=torch.float32))
        opt  = optim.Adam(self.model.parameters(), lr=lr)
        self.model.train()
        for _ in range(5):
            opt.zero_grad()
            loss = crit(self.model(X_b), y_b)
            loss.backward()
            opt.step()
        self.model.eval()
        print(f"Retreino: {len(self.replay_X)} amostras | loss={loss.item():.4f}")
        self.replay_X.clear()
        self.replay_y.clear()

# ══════════════════════════════════════════════════════════════════
# MÉTRICAS — REGRET, EXPLORAÇÃO, CONVERSÃO
# ══════════════════════════════════════════════════════════════════

def compute_metrics(history: list) -> dict:
    """
    Calcula métricas da simulação do bandit.
    history: lista de dicts com arm_chosen, reward, segment.
    """
    df_h = pd.DataFrame(history)
 
    total_rounds   = len(df_h)
    total_reward   = df_h["reward"].sum()
    conversion_rate = df_h["reward"].mean()
 
    best_arm       = max(ARM_TRUE_RATES, key=ARM_TRUE_RATES.get)
    best_rate      = ARM_TRUE_RATES[best_arm]
    df_h["regret"] = best_rate - df_h["reward"]
    cum_regret     = df_h["regret"].cumsum().iloc[-1]
 
    exploration_rate = (df_h["arm_chosen"] != best_arm).mean()
 
    arm_counts = df_h["arm_chosen"].value_counts()
    arm_rewards = df_h.groupby("arm_chosen")["reward"].mean()
 
    metrics = {
        "total_rounds":    total_rounds,
        "total_reward":    int(total_reward),
        "conversion_rate": round(conversion_rate, 4),
        "cumulative_regret": round(float(cum_regret), 2),
        "exploration_rate":  round(float(exploration_rate), 4),
        "arm_selection_counts": arm_counts.to_dict(),
        "arm_conversion_rates": arm_rewards.round(4).to_dict(),
    }
    return metrics

# ══════════════════════════════════════════════════════════════════
# RUNNER
# ══════════════════════════════════════════════════════════════════
 
def run(df: pd.DataFrame, synth: dict) -> dict:
    print("\n=== ETAPA 3: MODELAGEM ===")
 
    # Features
    X, y, encoders, scaler, feature_cols = prepare_features(df)
 
    # Treina modelo
    print("\nTreinando ConversionNet...")
    model, arm_scaler = train_model(X, y)
 
    # Inicializa bandit e baseline
    bandit   = NeuralThompsonSampling(model, ARMS, scaler, arm_scaler, feature_cols)
    baseline = DeterministicBaseline(ARM_TRUE_RATES)
 
    # Simula com eventos sintéticos
    events_df  = synth["events_df"]
    rewards_df = synth["rewards_df"]
    merged     = events_df.merge(rewards_df, on="event_id", how="left")
 
    print(f"\nSimulando {len(merged):,} eventos sintéticos...")
    bandit_history   = []
    baseline_history = []
 
    for i, (_, row) in enumerate(merged.iterrows()):
        try:
            ctx = build_client_context(
                df.iloc[int(row["client_index"])], encoders, feature_cols
            )
        except Exception:
            continue
 
        reward = int(row.get("reward", 0))
 
        # Bandit
        dec = bandit.choose(ctx)
        bandit.update(ctx, dec["arm_chosen"], reward)
        bandit_history.append({
            "arm_chosen": dec["arm_chosen"],
            "reward":     reward,
            "segment":    row["client_segment"],
        })
 
        # Baseline
        base_dec = baseline.choose(row["client_segment"])
        baseline.update(base_dec["arm_chosen"], reward)
        baseline_history.append({
            "arm_chosen": base_dec["arm_chosen"],
            "reward":     reward,
            "segment":    row["client_segment"],
        })
 
        # Retreino a cada 100 observações
        if (i + 1) % 100 == 0 and len(bandit.replay_X) >= 50:
            bandit.retrain()
 
    # Métricas comparativas
    bandit_metrics   = compute_metrics(bandit_history)
    baseline_metrics = compute_metrics(baseline_history)
 
    print("\n=== COMPARATIVO: BANDIT vs BASELINE ===")
    print(f"{'Métrica':<28} {'Bandit':>12} {'Baseline':>12}")
    print("-" * 54)
    for k in ["total_reward","conversion_rate","cumulative_regret","exploration_rate"]:
        print(f"  {k:<26} {str(bandit_metrics[k]):>12} {str(baseline_metrics[k]):>12}")
 
    # Salva métricas
    import json
    metrics_path = REPORTS_DIR / "simulation_metrics.json"
    with open(metrics_path, "w") as f:
        json.dump({
            "bandit":   bandit_metrics,
            "baseline": baseline_metrics,
        }, f, indent=2)
    print(f"\nMétricas salvas: {metrics_path}")
 
    return {
        "model":          model,
        "arm_scaler":     arm_scaler,
        "encoders":       encoders,
        "scaler":         scaler,
        "feature_cols":   feature_cols,
        "bandit":         bandit,
        "bandit_metrics": bandit_metrics,
    }
 
 
if __name__ == "__main__":
    df   = run_step1()
    synth = run_step2(df)
    run(df, synth)