"""
Datathon 7MLET - Pipeline end-to-end
====================================
Orquestra todas as etapas em sequência:

- ETAPA 1 → Kaggle + EDA
- ETAPA 2 → Enriquecimento sintético + golden set
- ETAPA 3 → Treino ConversionNet + simulação bandit
- ETAPA 4 → Avaliação offline
- ETAPA 5 → Salva artefatos para a API

Uso:
    python pipeline.py                  # Executa tudo
    python pipeline.py --step 1         # Só a etapa 1
    python pipeline.py --step 3         # Só treino (requer etapas anteriores)
    python pipeline.py --skip-train     # Pula treino, carrega modelo salvo
"""
import argparse
import pickle
import json
import sys
import torch
import numpy as np
import pandas as pd
from pathlib import Path
 
# Garantir que o diretório raiz do projeto está no PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
 
from src_config import *
import data.kaggle as kaggle
import data.synthetic_enrichment as synthetic_enrichment
import model
import evaluation

# ══════════════════════════════════════════════════════════════════
# Utilitários
# ══════════════════════════════════════════════════════════════════

def banner(msg: str):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")

def save_preprocessing_artifacts(encoders, scaler, arm_scaler, feature_cols):
    """Salva artefatos de pré-processamento para a API carregar."""
    MODELS_DIR.mkdir(exist_ok=True)
    path = MODELS_DIR / "preprocessing.pkl"
    with open(path, "wb") as f:
        pickle.dump({
            "encoders":     encoders,
            "scaler":       scaler,
            "arm_scaler":   arm_scaler,
            "feature_cols": feature_cols,
        }, f)
    print(f"Artefatos de pré-processamento salvos: {path}")

def load_preprocessing_artifacts() -> dict:
    path = MODELS_DIR / "preprocessing.pkl"
    if not path.exists():
        raise FileNotFoundError(f"Execute o pipeline completo primeiro: {path}")
    with open(path, "rb") as f:
        return pickle.load(f)
    
def load_saved_model(arts: dict) -> model.ConversionNet:
    """Carrega modelo salvo sem re-treinar."""
    model_path = MODELS_DIR / "conversion_net.pt"
    if not model_path.exists():
        raise FileNotFoundError(f"Modelo não encontrado: {model_path}")
    checkpoint = torch.load(model_path, map_location="cpu")
    model = model.ConversionNet(
        input_dim=checkpoint["input_dim"],
        hidden=checkpoint["hidden"],
        drop=checkpoint["drop"],
    )
    model.load_state_dict(checkpoint["model_state"])
    model.eval()
    return model

# ══════════════════════════════════════════════════════════════════
# Etapas individuais
# ══════════════════════════════════════════════════════════════════

def run_step1() -> pd.DataFrame:
    banner("ETAPA 1 — Base Kaggle + EDA")
    return kaggle.run()

def run_step2(df: pd.DataFrame) -> dict:
    banner("ETAPA 2 — Enriquecimento Sintético")
    return synthetic_enrichment.run(df)

def run_step3(df: pd.DataFrame, synth: dict,
              skip_train: bool = False) -> dict:
    banner("ETAPA 3 — Modelagem + Simulação Bandit")
 
    # Sempre prepara features (necessário mesmo sem treino)
    X, y, encoders, scaler, feature_cols = model.prepare_features(df)
 
    if skip_train:
        print("--skip-train: carregando modelo salvo...")
        arts = load_preprocessing_artifacts()
        trained_model = load_saved_model(arts)
        encoders, scaler = arts["encoders"], arts["scaler"]
        arm_scaler       = arts["arm_scaler"]
        feature_cols     = arts["feature_cols"]
    else:
        trained_model, arm_scaler = model.train_model(X, y)
        save_preprocessing_artifacts(encoders, scaler, arm_scaler, feature_cols)
 
    bandit = model.NeuralThompsonSampling(
        model=trained_model, arms=ARMS, scaler=scaler,
        arm_scaler=arm_scaler, feature_cols=feature_cols,
        arm_features=ARM_FEATURES
    )
    baseline = model.DeterministicBaseline(ARM_TRUE_RATES)
 
    # Simulação com eventos sintéticos
    events_df  = synth["events_df"]
    rewards_df = synth["rewards_df"]
    merged     = events_df.merge(rewards_df, on="event_id", how="left")
 
    print(f"Simulando {len(merged):,} eventos...")
    bandit_history, baseline_history = [], []
 
    for i, (_, row) in enumerate(merged.iterrows()):
        try:
            ctx = model.build_client_context(
                df.iloc[int(row["client_index"])], encoders, feature_cols
            )
        except Exception:
            continue
 
        reward_raw = row.get("reward", 0)
        reward = 0 if pd.isna(reward_raw) else int(reward_raw)
 
        dec = bandit.choose(ctx)
        bandit.update(ctx, dec["arm_chosen"], reward)
        bandit_history.append({
            "arm_chosen": dec["arm_chosen"],
            "reward":     reward,
            "segment":    row["client_segment"],
        })
 
        base_dec = baseline.choose(row["client_segment"])
        baseline.update(base_dec["arm_chosen"], reward)
        baseline_history.append({
            "arm_chosen": base_dec["arm_chosen"],
            "reward":     reward,
            "segment":    row["client_segment"],
        })
 
        if (i + 1) % 100 == 0 and len(bandit.replay_X) >= 50:
            bandit.retrain()
 
    bandit_metrics   = model.compute_metrics(bandit_history)
    baseline_metrics = model.compute_metrics(baseline_history)
 
    print("\n=== COMPARATIVO: BANDIT vs BASELINE ===")
    print(f"{'Métrica':<28} {'Bandit':>12} {'Baseline':>12}")
    print("-" * 54)
    for k in ["total_reward","conversion_rate","cumulative_regret","exploration_rate"]:
        print(f"  {k:<26} {str(bandit_metrics[k]):>12} {str(baseline_metrics[k]):>12}")
 
    metrics_path = REPORTS_DIR / "simulation_metrics.json"
    REPORTS_DIR.mkdir(exist_ok=True)
    with open(metrics_path, "w") as f:
        json.dump({"bandit": bandit_metrics, "baseline": baseline_metrics},
                  f, indent=2)
 
    return {
        "model":           model,
        "arm_scaler":      arm_scaler,
        "encoders":        encoders,
        "scaler":          scaler,
        "feature_cols":    feature_cols,
        "bandit":          bandit,
        "bandit_metrics":  bandit_metrics,
        "bandit_history":  bandit_history,
    }
 
 
def run_step4(model_artifacts: dict, df: pd.DataFrame) -> dict:
    banner("ETAPA 4 — Avaliação Offline + Golden Set")
    return evaluation.run(model_artifacts, df)
 
 
def run_step5_save(model_artifacts: dict):
    """Garante que todos os artefatos estão prontos para a API."""
    banner("ETAPA 5 — Salvando artefatos para API")
    save_preprocessing_artifacts(
        encoders     = model_artifacts["encoders"],
        scaler       = model_artifacts["scaler"],
        arm_scaler   = model_artifacts["arm_scaler"],
        feature_cols = model_artifacts["feature_cols"],
    )
 
    # Exemplo de chamada para a API (pode ser testado com uvicorn)
    sample = {
        "client_features": {col: 0.0 for col in model_artifacts["feature_cols"]},
        "policy_version": POLICY_VERSION,
    }
    print("Exemplo de chamada à API:")
    print(f"  POST /decide")
    print(f"  {json.dumps(sample, indent=4)}")
    print("\nPara iniciar a API localmente:")
    print("  uvicorn app.main:app --reload --port 8000")
    print("  curl http://localhost:8000/health")

# ══════════════════════════════════════════════════════════════════
# Diagnóstico final
# ══════════════════════════════════════════════════════════════════

def run_diagnostics(model_artifacts: dict, df: pd.DataFrame):
    banner("DIAGNÓSTICO FINAL")
 
    encoders     = model_artifacts["encoders"]
    feature_cols = model_artifacts["feature_cols"]
    bandit       = model_artifacts["bandit"]
 
    # Testa uma decisão de exemplo
    sample_row = df.iloc[0]
    ctx        = model.build_client_context(sample_row, encoders, feature_cols)
    decisao    = bandit.choose(ctx, POLICY_VERSION)
 
    print("\n=== DECISÃO DE EXEMPLO ===")
    print(f"  Oferta escolhida        : {decisao['arm_chosen']}")
    print(f"  Estimativa de conversão : {decisao['reason_codes']['estimated_conversion']:.2f}%")
    print(f"  Incerteza (std)         : {decisao['reason_codes']['uncertainty_std']:.4f}")
    print(f"  Explorando?             : {decisao['reason_codes']['exploring']}")
    print(f"  Amostra TS              : {decisao['reason_codes']['ts_sample']:.4f}")
    print(f"  Versão da política      : {decisao['policy_version']}")
 
    print("\n  Estimativas por braço:")
    for arm, est in decisao["estimates"].items():
        marker = " ← escolhido" if arm == decisao["arm_chosen"] else ""
        print(f"    {arm:22s}: {est['mean']*100:5.1f}%  std={est['std']:.4f}{marker}")
 
    # Verifica saúde do MC Dropout
    import torch
    x    = bandit._tensor(ctx, decisao["arm_chosen"])
    m    = bandit.model
    m.train()
    with torch.no_grad():
        samples = [torch.sigmoid(m(x)).item() for _ in range(30)]
    m.eval()
    mc_std = np.std(samples)
    print(f"\n  MC Dropout std (30 passes): {mc_std:.4f}", end="")
    if mc_std < 0.001:
        print("  ← ALERTA: std=0")
    elif mc_std > 0.35:
        print("  ← ALERTA: std muito alto (modelo não treinado?)")
    else:
        print("  ← OK")
 
    # Resumo dos artefatos gerados
    print("\n=== ARTEFATOS GERADOS ===")
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and not any(
            p in str(path) for p in ["__pycache__", ".git", "mlruns"]
        ):
            size = path.stat().st_size
            print(f"  {str(path.relative_to(ROOT)):55s}  {size:>8,} bytes")

# ══════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Pipeline Datathon 7MLET")
    parser.add_argument("--step",       type=int, default=0,
                        help="Executa apenas a etapa especificada (1-5). 0=todas.")
    parser.add_argument("--skip-train", action="store_true",
                        help="Pula treino e carrega modelo salvo.")
    args = parser.parse_args()
 
    np.random.seed(SEED)
    torch.manual_seed(SEED)
 
    LOGS_DIR.mkdir(exist_ok=True)
    REPORTS_DIR.mkdir(exist_ok=True)
    MODELS_DIR.mkdir(exist_ok=True)
 
    if args.step == 1:
        run_step1()
        return
 
    if args.step in (0, 1, 2, 3, 4, 5):
        df = run_step1()
 
    if args.step in (0, 2, 3, 4, 5):
        synth = run_step2(df)
 
    if args.step in (0, 3, 4, 5):
        model_artifacts = run_step3(df, synth, skip_train=args.skip_train)
 
    if args.step in (0, 4, 5):
        run_step4(model_artifacts, df)
 
    if args.step in (0, 5):
        run_step5_save(model_artifacts)
 
    if args.step == 0:
        run_diagnostics(model_artifacts, df)
 
    banner("PIPELINE CONCLUÍDO")
 
 
if __name__ == "__main__":
    main()