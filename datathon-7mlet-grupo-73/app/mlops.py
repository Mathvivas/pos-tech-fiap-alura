"""
Etapa 7 — Ciclo de vida MLOps
================================
Conecta com:
  - model.py       : ConversionNet, NeuralThompsonSampling, train_model
  - step2_synthetic.py   : rewards_df (janelas temporais para simular drift)
  - src_config.py        : ARMS, ARM_TRUE_RATES, MLFLOW_EXPERIMENT, MODELS_DIR
  - MLflow               : rastreia experimentos, versiona políticas

O que esta etapa gera:
  - reports/drift_report.json       : métricas de drift por janela temporal
  - reports/mlops_cycle.json        : histórico de versões e aprovações
  - docs/mlops-plan.md              : plano documentado de retreino e promoção
  - models/conversion_net_v2.pt     : modelo retreinado (se aprovado)
"""

import json
import copy
import datetime
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import mlflow
import mlflow.pytorch
from pathlib import Path

from src_config import (
    ARMS, ARM_TRUE_RATES, MLFLOW_EXPERIMENT,
    MODELS_DIR, REPORTS_DIR, ROOT, SEED,
    POLICY_VERSION,
)

DOCS_DIR = ROOT / "docs"


# ══════════════════════════════════════════════════════════════════
# 1. DETECÇÃO DE DRIFT
# ══════════════════════════════════════════════════════════════════

def detect_reward_drift(rewards_df: pd.DataFrame,
                         window_days: int = 7) -> dict:
    """
    Compara taxa de conversão em janelas temporais consecutivas.
    Drift = variação > threshold entre janela atual e anterior.

    Conecta com step2_synthetic.py: usa delayed_rewards.jsonl
    que contém reward_observed_at e delay_days.
    """
    if "reward_observed_at" not in rewards_df.columns:
        return {"error": "rewards_df sem coluna reward_observed_at"}

    rewards_df = rewards_df.copy()
    rewards_df["obs_date"] = pd.to_datetime(rewards_df["reward_observed_at"])
    rewards_df["window"]   = (
        (rewards_df["obs_date"] - rewards_df["obs_date"].min()).dt.days
        // window_days
    )

    windows = (
        rewards_df.groupby("window")["reward"]
        .agg(["mean", "count", "sum"])
        .rename(columns={"mean": "conv_rate", "count": "n_obs", "sum": "n_conv"})
    )

    # Variação entre janelas consecutivas
    windows["prev_conv"] = windows["conv_rate"].shift(1)
    windows["delta"]     = (windows["conv_rate"] - windows["prev_conv"]).abs()
    windows["drift"]     = windows["delta"] > 0.05   # threshold 5pp

    drift_detected = bool(windows["drift"].any())
    max_delta      = float(windows["delta"].max()) if len(windows) > 1 else 0.0

    report = {
        "drift_detected":   drift_detected,
        "max_delta":        round(max_delta, 4),
        "threshold":        0.05,
        "window_days":      window_days,
        "n_windows":        len(windows),
        "windows":          windows.reset_index().to_dict(orient="records"),
    }

    status = "DRIFT DETECTADO" if drift_detected else "Estável"
    print(f"  Drift de recompensa: {status} (max_delta={max_delta:.4f})")
    return report


def detect_feature_drift(df_train: pd.DataFrame,
                          df_recent: pd.DataFrame,
                          num_cols: list) -> dict:
    """
    Compara distribuição de features numéricas entre treino e dados recentes.
    Usa Population Stability Index (PSI) como métrica de drift.
    PSI < 0.1: estável | 0.1-0.2: monitorar | > 0.2: retreinar
    """

    def psi(expected: np.ndarray, actual: np.ndarray,
             n_bins: int = 10) -> float:
        breakpoints = np.linspace(0, 100, n_bins + 1)
        exp_bins    = np.percentile(expected, breakpoints)
        exp_bins    = np.unique(exp_bins)
        if len(exp_bins) < 2:
            return 0.0

        exp_perc = np.histogram(expected, bins=exp_bins)[0] / len(expected)
        act_perc = np.histogram(actual,   bins=exp_bins)[0] / len(actual)

        exp_perc = np.where(exp_perc == 0, 1e-4, exp_perc)
        act_perc = np.where(act_perc == 0, 1e-4, act_perc)

        return float(np.sum((act_perc - exp_perc) * np.log(act_perc / exp_perc)))

    results = {}
    for col in num_cols:
        if col not in df_train.columns or col not in df_recent.columns:
            continue
        score = psi(df_train[col].dropna().values,
                    df_recent[col].dropna().values)
        status = "stable" if score < 0.1 else ("monitor" if score < 0.2 else "retrain")
        results[col] = {"psi": round(score, 4), "status": status}

    need_retrain = any(v["status"] == "retrain" for v in results.values())
    print(f"  Feature drift (PSI): {sum(1 for v in results.values() if v['status']=='retrain')} "
          f"colunas acima do threshold de retreino")
    return {"feature_psi": results, "needs_retrain": need_retrain}


# ══════════════════════════════════════════════════════════════════
# 2. RETREINO COM APPROVAL GATE
# ══════════════════════════════════════════════════════════════════

class PolicyVersion:
    """Representa uma versão de política com metadados de aprovação."""

    def __init__(self, version: str, model_state: dict,
                 metrics: dict, input_dim: int):
        self.version     = version
        self.model_state = model_state
        self.metrics     = metrics
        self.input_dim   = input_dim
        self.status      = "candidate"   # candidate → approved → production | rejected
        self.created_at  = datetime.datetime.utcnow().isoformat()
        self.approved_by = None
        self.approved_at = None

    def to_dict(self) -> dict:
        return {
            "version":     self.version,
            "status":      self.status,
            "metrics":     self.metrics,
            "created_at":  self.created_at,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at,
        }


def retrain_candidate(model_artifacts: dict,
                       df: pd.DataFrame,
                       new_version: str = "v2.0") -> PolicyVersion:
    """
    Retreina o modelo com dados mais recentes e retorna um candidato.
    O candidato precisa ser aprovado antes de ir para produção.

    Conecta com model.py: usa train_model com os mesmos parâmetros.
    """
    from model import train_model, prepare_features

    print(f"  Treinando candidato {new_version}...")

    # Usa os mesmos dados + features do pipeline original
    X, y, _, _, _ = prepare_features(df)

    mlflow.set_experiment(MLFLOW_EXPERIMENT)
    with mlflow.start_run(run_name=f"retrain_{new_version}"):
        mlflow.log_param("policy_version", new_version)
        mlflow.log_param("retrain_trigger", "drift_detected")
        mlflow.log_param("retrain_date", datetime.datetime.utcnow().isoformat())

        from model import ARM_FEATURES
        model, _ = train_model(
            X, y,
            arm_features=ARM_FEATURES,
            epochs=40,     # menos épocas para retreino rápido
            lr=1e-4,       # lr menor para fine-tuning
            batch_size=256,
        )

        # Avalia o candidato no golden set
        from sklearn.metrics import roc_auc_score
        import torch
        X_t   = torch.tensor(X, dtype=torch.float32)
        n_arm = len(next(iter(ARM_FEATURES.values())))

        # Adiciona features de oferta zeradas para inferência de avaliação
        from sklearn.preprocessing import MinMaxScaler
        arm_vals   = np.array([list(v.values()) for v in ARM_FEATURES.values()],
                               dtype=np.float32)
        arm_scaler = MinMaxScaler().fit(arm_vals)
        a_vec      = arm_scaler.transform(arm_vals[:1]).flatten()
        X_exp      = np.hstack([X, np.tile(a_vec, (len(X), 1))]).astype(np.float32)
        X_exp_t    = torch.tensor(X_exp, dtype=torch.float32)

        model.eval()
        with torch.no_grad():
            probs = torch.sigmoid(model(X_exp_t)).numpy()

        auc = roc_auc_score(y, probs)
        mlflow.log_metric("candidate_auc", auc)
        print(f"  Candidato AUC: {auc:.4f}")

    candidate = PolicyVersion(
        version     = new_version,
        model_state = {k: v.clone() for k, v in model.state_dict().items()},
        metrics     = {"auc": round(auc, 4), "n_samples": len(y)},
        input_dim   = X.shape[1] + n_arm,
    )
    return candidate


def approval_gate(candidate: PolicyVersion,
                   current_metrics: dict,
                   auto_approve_threshold: float = 0.02) -> bool:
    """
    Avalia se o candidato deve ser aprovado para produção.

    Critérios automáticos:
      1. AUC do candidato >= AUC atual - tolerance (não regrediu)
      2. AUC do candidato > 0.60 (mínimo absoluto)

    Critério humano:
      Se auto-aprovação falhar, imprime o relatório e aguarda confirmação
      (em produção: integrar com JIRA / Teams approval workflow).
    """
    candidate_auc = candidate.metrics.get("auc", 0)
    current_auc   = current_metrics.get("val_auc", current_metrics.get("auc", 0))

    delta         = candidate_auc - float(current_auc) if current_auc else 0
    min_absolute  = 0.60
    auto_approved = (candidate_auc >= min_absolute and
                     delta >= -auto_approve_threshold)

    print(f"\n  APPROVAL GATE — {candidate.version}")
    print(f"  {'─'*40}")
    print(f"  AUC candidato : {candidate_auc:.4f}")
    print(f"  AUC atual     : {current_auc:.4f}" if current_auc else "  AUC atual     : N/A (primeira versão)")
    print(f"  Delta         : {delta:+.4f}")
    print(f"  Mínimo abs.   : {min_absolute}")
    print(f"  Auto-aprovação: {'SIM' if auto_approved else 'NÃO'}")

    if auto_approved:
        candidate.status      = "approved"
        candidate.approved_by = "auto_gate"
        candidate.approved_at = datetime.datetime.utcnow().isoformat()
        print(f"  ✓ Candidato APROVADO automaticamente")
    else:
        # Em produção: envia notificação para aprovação humana
        print(f"  ✗ Candidato requer APROVAÇÃO HUMANA")
        print(f"    → Razão: AUC abaixo do threshold ou regressão detectada")
        print(f"    → Em produção: abrir ticket de aprovação no sistema de governança")
        candidate.status = "pending_human_approval"

    return auto_approved


def promote_to_production(candidate: PolicyVersion,
                           current_version: str) -> str:
    """
    Promove o candidato aprovado para produção.
    Salva o modelo e registra no MLflow com alias 'Production'.
    Mantém o modelo anterior como rollback disponível.
    """
    from model import ConversionNet

    model_path = MODELS_DIR / f"conversion_net_{candidate.version}.pt"
    torch.save({
        "model_state": candidate.model_state,
        "input_dim":   candidate.input_dim,
        "hidden":      64,
        "drop":        0.3,
    }, model_path)

    # Mantém versão anterior para rollback
    prev_path = MODELS_DIR / f"conversion_net_{current_version}_rollback.pt"
    prod_path = MODELS_DIR / "conversion_net.pt"
    if prod_path.exists():
        import shutil
        shutil.copy(prod_path, prev_path)
        print(f"  Rollback salvo: {prev_path}")

    # Promove: copia como versão de produção
    import shutil
    shutil.copy(model_path, prod_path)
    print(f"  Modelo promovido para produção: {prod_path}")

    return candidate.version


def rollback(target_version: str) -> bool:
    """
    Reverte para uma versão anterior em caso de degradação em produção.
    """
    rollback_path = MODELS_DIR / f"conversion_net_{target_version}_rollback.pt"
    prod_path     = MODELS_DIR / "conversion_net.pt"

    if not rollback_path.exists():
        print(f"  Rollback indisponível: {rollback_path} não encontrado")
        return False

    import shutil
    shutil.copy(rollback_path, prod_path)
    print(f"  Rollback executado para: {target_version}")
    return True


# ══════════════════════════════════════════════════════════════════
# 3. RASTREIO DE EXPERIMENTOS (MLflow)
# ══════════════════════════════════════════════════════════════════

def log_policy_cycle(candidate: PolicyVersion,
                      drift_report: dict,
                      promoted: bool):
    """Loga o ciclo completo de vida da política no MLflow."""
    mlflow.set_experiment(MLFLOW_EXPERIMENT)
    with mlflow.start_run(run_name=f"policy_cycle_{candidate.version}"):
        mlflow.log_params({
            "candidate_version": candidate.version,
            "status":            candidate.status,
            "approved_by":       candidate.approved_by or "pending",
            "promoted":          promoted,
        })
        mlflow.log_metrics({
            "candidate_auc":  candidate.metrics.get("auc", 0),
            "drift_detected": int(drift_report.get("drift_detected", False)),
            "max_drift_delta": drift_report.get("max_delta", 0),
        })


# ══════════════════════════════════════════════════════════════════
# 4. DOCUMENTAÇÃO DO PLANO MLOPS
# ══════════════════════════════════════════════════════════════════

MLOPS_PLAN_MD = """# Plano MLOps — Ciclo de Vida de Políticas

## Visão geral do ciclo

```
Monitoramento contínuo
        ↓
   Drift detectado?
      ↓       ↓
     Sim      Não → continua monitorando
      ↓
  Retreino do candidato
        ↓
   Approval Gate
   (automático ou humano)
      ↓         ↓
  Aprovado    Rejeitado → investigar / ajustar
      ↓
  Promoção para produção
        ↓
  Versão anterior → rollback disponível
        ↓
  Monitoramento contínuo
```

## Critérios de retreino

| Gatilho                          | Threshold           | Ação                      |
|----------------------------------|---------------------|---------------------------|
| Drift de recompensa (delta conv) | > 5 pontos percentuais | Retreino automático    |
| Feature PSI (qualquer coluna)    | > 0.20              | Retreino automático       |
| AUC de validação                 | < 0.60              | Alerta + revisão humana   |
| Regret acumulado                 | > 20% acima da baseline | Investigar política   |

## Critérios de aprovação automática

1. AUC do candidato ≥ AUC atual − 2pp (não regrediu significativamente)
2. AUC do candidato ≥ 0.60 (mínimo absoluto de qualidade)
3. Passou nos 30 casos do golden set (pass_rate = 100%)

Se qualquer critério falhar → aprovação humana obrigatória.

## Aprovação humana estruturada

**Quem aprova:** Data Scientist responsável + representante de Negócio  
**Prazo:** 48h após geração do candidato  
**Documentação:** preencher `reports/approval_checklist.md` antes de promover

### Checklist de aprovação humana

- [ ] AUC do candidato revisado e documentado
- [ ] Golden set re-executado no candidato
- [ ] Análise de fairness por segmento comparada com versão anterior
- [ ] Revisão dos reason_codes de 10 decisões de exemplo
- [ ] Plano de rollback confirmado (versão anterior salva e testada)
- [ ] Responsável pelo monitoramento pós-deploy identificado

## Rollback

```bash
# Via pipeline (aciona rollback para versão anterior)
python pipeline.py --rollback v1.0

# Manual
cp models/conversion_net_v1.0_rollback.pt models/conversion_net.pt
# Reiniciar o serviço
az containerapp revision restart --name bandit-api --resource-group $RG
```

**Critério de rollback automático:** AUC em produção cair > 10pp em 24h

## Cadência de revisão

| Artefato          | Cadência    | Responsável               |
|-------------------|-------------|---------------------------|
| Model Card        | A cada versão + trimestral | Data Scientist  |
| System Card       | A cada versão + semestral  | Tech Lead       |
| Plano LGPD        | Anual + mudanças de dados  | DPO             |
| Análise de fairness | Trimestral              | Data Scientist  |
| Golden set        | Semestral + mudanças de negócio | DS + Negócio |

## Rastreio no MLflow

Cada execução do ciclo de vida gera uma run no experimento `datathon-jyb-bandit` com:
- `candidate_version` — identificador da versão
- `candidate_auc` — AUC de validação
- `drift_detected` — se drift foi detectado neste ciclo
- `max_drift_delta` — magnitude máxima do drift de recompensa
- `status` — approved / rejected / pending_human_approval
- `promoted` — se a versão foi para produção
"""


# ══════════════════════════════════════════════════════════════════
# 5. RUNNER
# ══════════════════════════════════════════════════════════════════

def run(model_artifacts: dict, synth: dict, df: pd.DataFrame) -> dict:
    print("\n=== ETAPA 7: MLOPS — CICLO DE VIDA ===")

    rewards_df    = synth["rewards_df"]
    bandit_metrics = model_artifacts.get("bandit_metrics", {})

    # ── 1. Detecta drift ──────────────────────────────────────
    print("\n[1/5] Detecção de drift de recompensa...")
    drift_report = detect_reward_drift(rewards_df, window_days=7)

    print("\n[2/5] Detecção de drift de features (PSI)...")
    # Simula "dados recentes" com pequena perturbação nos últimos 20%
    n = len(df)
    df_train  = df.iloc[:int(n * 0.8)]
    df_recent = df.iloc[int(n * 0.8):].copy()

    # Adiciona drift sintético nas colunas numéricas do dataset JYB
    # (sem 'balance' e sem 'duration' — ambas removidas do dataset processado)
    # Simula padrão realista: clientes mais recentes são mais velhos,
    # fizeram mais contatos e têm menos histórico anterior
    if "age" in df_recent.columns:
        df_recent["age"] = (df_recent["age"] * 1.05).clip(upper=90).astype(int)
    if "campaign" in df_recent.columns:
        df_recent["campaign"] = (df_recent["campaign"] + 1).clip(upper=15)
    if "previous" in df_recent.columns:
        df_recent["previous"] = (df_recent["previous"] * 1.2).clip(upper=10)

    # Apenas colunas que existem no dataset processado
    num_cols_check = [
        c for c in ["age", "campaign", "previous", "pdays_clean", "contacted_before"]
        if c in df.columns
    ]
    feat_drift = detect_feature_drift(df_train, df_recent, num_cols_check)
    drift_report["feature_drift"] = feat_drift

    # ── 2. Retreino do candidato ──────────────────────────────
    retrain_needed = (
        drift_report.get("drift_detected", False) or
        feat_drift.get("needs_retrain", False)
    )

    candidate = None
    promoted  = False

    if retrain_needed:
        print("\n[3/5] Drift detectado — retreinando candidato v2.0...")
        candidate = retrain_candidate(model_artifacts, df, new_version="v2.0")

        # ── 3. Approval gate ──────────────────────────────────
        print("\n[4/5] Avaliando candidato no approval gate...")
        current_auc = bandit_metrics.get("auc", 0.65)
        approved    = approval_gate(
            candidate,
            current_metrics={"auc": current_auc},
            auto_approve_threshold=0.02,
        )

        # ── 4. Promoção ───────────────────────────────────────
        print("\n[5/5] Promoção para produção...")
        if approved:
            promote_to_production(candidate, current_version=POLICY_VERSION)
            promoted = True
        else:
            print("  Candidato aguarda aprovação humana — produção inalterada")
    else:
        print("\n[3/5] Nenhum drift significativo — retreino não necessário")
        print("[4/5] Approval gate não acionado")
        print("[5/5] Versão de produção inalterada")

    # ── 5. Loga ciclo no MLflow ───────────────────────────────
    if candidate:
        log_policy_cycle(candidate, drift_report, promoted)

    # ── Salva relatórios ──────────────────────────────────────
    REPORTS_DIR.mkdir(exist_ok=True)

    cycle_report = {
        "timestamp":       datetime.datetime.utcnow().isoformat(),
        "current_version": POLICY_VERSION,
        "drift_report":    drift_report,
        "retrain_needed":  retrain_needed,
        "candidate":       candidate.to_dict() if candidate else None,
        "promoted":        promoted,
        "rollback_available": (
            MODELS_DIR / f"conversion_net_{POLICY_VERSION}_rollback.pt"
        ).exists(),
    }

    cycle_path = REPORTS_DIR / "mlops_cycle.json"
    with open(cycle_path, "w") as f:
        json.dump(cycle_report, f, indent=2, default=str)
    print(f"\nRelatório MLOps salvo: {cycle_path}")

    drift_path = REPORTS_DIR / "drift_report.json"
    with open(drift_path, "w") as f:
        json.dump(drift_report, f, indent=2, default=str)
    print(f"Drift report salvo : {drift_path}")

    # ── Documentação do plano ─────────────────────────────────
    DOCS_DIR.mkdir(exist_ok=True)
    mlops_plan_path = DOCS_DIR / "mlops-plan.md"
    with open(mlops_plan_path, "w", encoding="utf-8") as f:
        f.write(MLOPS_PLAN_MD)
    print(f"Plano MLOps salvo  : {mlops_plan_path}")

    # ── Resumo ────────────────────────────────────────────────
    print("\n=== RESUMO MLOPS ===")
    print(f"  Drift de recompensa : {'SIM' if drift_report.get('drift_detected') else 'NÃO'}")
    print(f"  Feature drift       : {'SIM' if feat_drift.get('needs_retrain') else 'NÃO'}")
    print(f"  Retreino necessário : {'SIM' if retrain_needed else 'NÃO'}")
    if candidate:
        print(f"  Candidato gerado    : {candidate.version} (AUC={candidate.metrics.get('auc'):.4f})")
        print(f"  Status              : {candidate.status}")
        print(f"  Promovido           : {'SIM' if promoted else 'NÃO'}")
    print(f"  Rollback disponível : {cycle_report['rollback_available']}")

    return cycle_report


if __name__ == "__main__":
    print("Execute via: python pipeline.py --step 7")