"""
ETAPA 4 - Avaliação offline e golden set
Roda avaliação reproduzível com métricas, fairness e golden set
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path
from src_config import *
from model import build_client_context


def evaluate_golden_set(bandit, encoders: dict,
                         feature_cols: list, df: pd.DataFrame) -> dict:
    """Roda o bandit em cada caso do golden set e verifica pass/fail."""
    golden_path = DATA_GOLDEN / "evaluation_cases.jsonl"
    cases = [json.loads(l) for l in open(golden_path)]

    results = []
    for case in cases:
        try:
            # Reconstrói contexto a partir do segmento e contexto salvo
            subset = df[df.apply(
                lambda r: str(r.get("poutcome","")) ==
                          case["context"].get("poutcome",""), axis=1
            )].head(1)

            if len(subset) == 0:
                subset = df.sample(1, random_state=42)

            ctx = build_client_context(subset.iloc[0], encoders, feature_cols)
            dec = bandit.choose(ctx)

            arm_ok      = dec["arm_chosen"] == case["arm_expected"]
            conv_ok     = dec["reason_codes"]["estimated_conversion"] > 5.0
            passed      = arm_ok or conv_ok

            results.append({
                "case_id":      case["case_id"],
                "type":         case["type"],
                "segment":      case["segment"],
                "arm_expected": case["arm_expected"],
                "arm_chosen":   dec["arm_chosen"],
                "conv_est":     dec["reason_codes"]["estimated_conversion"],
                "passed":       passed,
            })
        except Exception as e:
            results.append({
                "case_id": case["case_id"],
                "type":    case.get("type",""),
                "passed":  False,
                "error":   str(e),
            })

    df_r     = pd.DataFrame(results)
    pass_rate = df_r["passed"].mean()

    print(f"\n=== AVALIAÇÃO GOLDEN SET ({len(results)} casos) ===")
    print(f"Pass rate: {pass_rate:.1%}")
    print(df_r.groupby("type")["passed"].mean().round(3).to_string())

    return {"pass_rate": pass_rate, "results": results}


def fairness_analysis(bandit_history: list) -> dict:
    """Analisa exposição e conversão por segmento (fairness)."""
    df_h = pd.DataFrame(bandit_history)
    if "segment" not in df_h.columns:
        return {}

    fairness = df_h.groupby("segment").agg(
        exposure=("arm_chosen", "count"),
        conversion=("reward", "mean"),
    ).round(4)
    fairness["exposure_share"] = (fairness["exposure"] /
                                   fairness["exposure"].sum()).round(4)
    max_gap = fairness["conversion"].max() - fairness["conversion"].min()

    print("\n=== ANÁLISE DE FAIRNESS ===")
    print(fairness.to_string())
    print(f"Gap máximo de conversão entre segmentos: {max_gap:.4f}")

    return fairness.to_dict()


def run(model_artifacts: dict, df: pd.DataFrame) -> dict:
    print("\n=== ETAPA 4: AVALIAÇÃO OFFLINE ===")

    golden_results = evaluate_golden_set(
        bandit      = model_artifacts["bandit"],
        encoders    = model_artifacts["encoders"],
        feature_cols= model_artifacts["feature_cols"],
        df          = df,
    )

    fairness = fairness_analysis(
        model_artifacts.get("bandit_history", [])
    )

    report = {
        "golden_pass_rate": golden_results["pass_rate"],
        "fairness":         fairness,
    }

    report_path = REPORTS_DIR / "evaluation_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"Relatório salvo: {report_path}")

    return report


if __name__ == "__main__":
    print("Execute via pipeline.py")