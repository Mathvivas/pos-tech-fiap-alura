"""
ETAPA 5 - Serviço demonstrável

1. Testa o contrato da API
2. Verifica o log auditável gerado
3. Salva um relatório de cobertura dos testes de contrato
4. Gera um exemplo de chamada curl para o README
"""
import json
import uuid
import datetime
import traceback
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Any

from src_config import (
    ARMS, ARM_FEATURES, POLICY_VERSION,
    LOGS_DIR, REPORTS_DIR, MODELS_DIR,
)

# ══════════════════════════════════════════════════════════════════
# 1. CLIENTE DA API (testa contratos sem subir o servidor HTTP)
# ══════════════════════════════════════════════════════════════════

class BanditAPIClient:
    """
    Simula as chamadas à API diretamente via o bandit em memória.
    Em produção, substitua por chamadas HTTP reais ao FastAPI.
    
    Isso permite rodar os testes de contrato no pipeline sem depender
    do servidor uvicorn estar rodando.
    """

    def __init__(self, bandit, feature_cols: list):
        self.bandit       = bandit
        self.feature_cols = feature_cols
        self._decisions   = {}

    def health(self) -> dict:
        return {
            'status':           'ok',
            'model_loaded':     True,
            'policy_version':   POLICY_VERSION,
            'timestamp':        datetime.datetime.now().isoformat(),
        }
    
    def arms(self) -> dict:
        return {
            'arms':             ARMS,
            'arms_features':    ARM_FEATURES,
            'policy_version':   POLICY_VERSION,
        }
    
    def decide(self, client_features: dict,
               policy_version: str = POLICY_VERSION) -> str:
        """
        POST /decide - valida contrato de entrada e retorna decisão.
        """

        # Validação de contrato de entrada
        missing = [f for f in self.feature_cols if f not in client_features]
        if missing:
            raise ValueError(f"Features ausentes no request: {missing}")
        
        decisao = self.bandit.choose(client_features, policy_version)
        event_id = str(uuid.uuid4())

        # Log auditável - mesma estrutura do app/main.py
        log_entry = {
            "event_id":       event_id,
            "timestamp":      datetime.datetime.utcnow().isoformat(),
            "arm_chosen":     decisao["arm_chosen"],
            "policy_version": decisao["policy_version"],
            "reason_codes":   decisao["reason_codes"],
            "estimates":      decisao["estimates"],
            "client_context": client_features,
        }
        LOGS_DIR.mkdir(exist_ok=True)
        with open(LOGS_DIR / 'decisions.jsonl', 'a') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

        self._decisions[event_id] = log_entry
        return {'event_id': event_id, **decisao}
    
    def reward(self, event_id: str, arm: str, reward: int) -> dict:
        """
        POST /reward - valida contrato de reward e atualiza buffer.
        """

        # Validação de contrato de entrada
        if arm not in ARMS:
            raise ValueError(f'Braço inválido: {arm}. Válidos: {ARMS}')
        if reward not in (0, 1):
            raise ValueError(f'Reward deve ser 0 ou 1, recebido: {reward}')
        
        # Recupera contexto original para update correto
        original = self._decisions.get(event_id)
        if original:
            self.bandit.update(
                original['client_context'], arm, reward
            )

        log_entry = {
            'event_id':     event_id,
            'arm':          arm,
            'reward':       reward,
            'timestamp':    datetime.datetime.now().isoformat(),
            'type':         'reward',
        }
        with open(LOGS_DIR / 'decisions.jsonl', 'a') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

        return {
            'status':       'ok',
            'event_id':     event_id,
            'buffer_size':  len(self.bandit.replay_X)
        }

# ══════════════════════════════════════════════════════════════════
# 2. TESTES DE CONTRATO
# ══════════════════════════════════════════════════════════════════

class ContractTestResults:
    def __init__(self, name: str):
        self.name       = name
        self.passed     = False
        self.message    = ""

    def ok(self, msg: str = ""):
        self.passed     = True
        self.message    = msg
        return self
    
    def fail(self, msg: str):
        self.passed     = False
        self.message    = msg
        return msg
    
def _build_valid_context(feature_cols: list) -> dict:
    """Contexto mínimo válido para todos os testes."""
    defaults = {
        'age': 42.0, 'campaign': 1.0, 'pdays_clean': 0.0,
        'previous': 0.0, 'contacted_before': 0.0, 'job': 2.0,
        'marital': 1.0, 'education': 3.0, 'default': 0.0,
        'housing': 1.0, 'loan': 0.0, 'contact': 0.0,
        'month': 4.0, 'poutcome': 0.0
    }
    return {f: defaults.get(f, 0.0) for f in feature_cols}

def run_contract_tests(client: BanditAPIClient, feature_cols: list) -> list:
    """
    Suíte de testes de contrato cobrindo:
      - health endpoint
      - arms endpoint
      - decide: caso válido
      - decide: features ausentes (deve dar erro)
      - decide: reward inválido (deve dar erro)
      - reward: fluxo completo decide → reward
      - log auditável: verifica campos obrigatórios
      - reason_codes: verifica campos obrigatórios
      - policy_version: propagação correta
      - arm_chosen: deve ser um dos ARMS válidos
    """
    results = []
    ctx     = _build_valid_context(feature_cols)

    # === T01: health retorn status ok =============================
    r = ContractTestResults('T01 - /health retorna status=ok')
    try:
        resp = client.health()
        assert resp['status'] == 'ok', f'status={resp["status"]}'
        assert 'policy_version' in resp
        r.ok(f'policy_version={resp["policy_version"]}')
    except Exception as e:
        r.fail(str(e))
    results.append(r)

    # === T02: arms retorna lista correta ==========================
    r = ContractTestResults("T02 — /arms retorna braços corretos")
    try:
        resp = client.arms()
        assert set(resp["arms"]) == set(ARMS), f"arms={resp['arms']}"
        r.ok(f"{len(resp['arms'])} braços")
    except Exception as e:
        r.fail(str(e))
    results.append(r)

    # === T03: decide retorna campos obrigatórios ==================
    r = ContractTestResults("T03 — /decide retorna arm_chosen, event_id, reason_codes")
    try:
        resp = client.decide(ctx)
        assert "event_id"     in resp, "sem event_id"
        assert "arm_chosen"   in resp, "sem arm_chosen"
        assert "reason_codes" in resp, "sem reason_codes"
        assert "estimates"    in resp, "sem estimates"
        r.ok(f"arm_chosen={resp['arm_chosen']}")
    except Exception as e:
        r.fail(str(e))
    results.append(r)

    # === T04: arm_chosen é válido =================================
    r = ContractTestResults("T04 — arm_chosen é um dos ARMS definidos")
    try:
        resp = client.decide(ctx)
        assert resp["arm_chosen"] in ARMS, f"arm inválido: {resp['arm_chosen']}"
        r.ok(resp["arm_chosen"])
    except Exception as e:
        r.fail(str(e))
    results.append(r)

    # === T05: reason_codes tem os campos obrigatórios =============
    r = ContractTestResults("T05 — reason_codes tem estimated_conversion, uncertainty_std, exploring")
    try:
        resp = client.decide(ctx)
        rc   = resp["reason_codes"]
        for field in ["estimated_conversion", "uncertainty_std",
                       "exploring", "ts_sample"]:
            assert field in rc, f"campo ausente: {field}"
        assert 0 <= rc["estimated_conversion"] <= 100, \
            f"conversão fora de [0,100]: {rc['estimated_conversion']}"
        r.ok(f"conv={rc['estimated_conversion']:.1f}% std={rc['uncertainty_std']:.4f}")
    except Exception as e:
        r.fail(str(e))
    results.append(r)

    # === T06: policy_version propagado ============================
    r = ContractTestResults("T06 — policy_version propagado corretamente")
    try:
        resp = client.decide(ctx, policy_version="v_test")
        assert resp["policy_version"] == "v_test", \
            f"policy_version={resp['policy_version']}"
        r.ok()
    except Exception as e:
        r.fail(str(e))
    results.append(r)

    # === T07: features ausentes -> erro ===========================
    r = ContractTestResults("T07 — /decide com features ausentes levanta ValueError")
    try:
        client.decide({"age": 42})   # contexto incompleto
        r.fail("Deveria ter levantado ValueError")
    except ValueError:
        r.ok("ValueError levantado corretamente")
    except Exception as e:
        r.fail(f"Erro inesperado: {e}")
    results.append(r)

    # === T08: reward válido =======================================
    r = ContractTestResults("T08 — /reward com dados válidos retorna status=ok")
    try:
        dec  = client.decide(ctx)
        resp = client.reward(dec["event_id"], dec["arm_chosen"], 1)
        assert resp["status"] == "ok"
        assert "buffer_size" in resp
        r.ok(f"buffer_size={resp['buffer_size']}")
    except Exception as e:
        r.fail(str(e))
    results.append(r)

    # === T09: reward=0 também funciona ============================
    r = ContractTestResults("T09 — /reward com reward=0 (sem conversão) funciona")
    try:
        dec  = client.decide(ctx)
        resp = client.reward(dec["event_id"], dec["arm_chosen"], 0)
        assert resp["status"] == "ok"
        r.ok()
    except Exception as e:
        r.fail(str(e))
    results.append(r)

    # === T10: arm inválido no reward -> erro ======================
    r = ContractTestResults("T10 — /reward com arm inválido levanta ValueError")
    try:
        dec = client.decide(ctx)
        client.reward(dec["event_id"], "braço_inexistente", 1)
        r.fail("Deveria ter levantado ValueError")
    except ValueError:
        r.ok("ValueError levantado corretamente")
    except Exception as e:
        r.fail(f"Erro inesperado: {e}")
    results.append(r)

    # === T11: reward inválido (não 0 ou 1) -> erro ================
    r = ContractTestResults("T11 — /reward com reward=2 levanta ValueError")
    try:
        dec = client.decide(ctx)
        client.reward(dec["event_id"], dec["arm_chosen"], 2)
        r.fail("Deveria ter levantado ValueError")
    except ValueError:
        r.ok("ValueError levantado corretamente")
    except Exception as e:
        r.fail(f"Erro inesperado: {e}")
    results.append(r)

    # === T12: log auditável foi gerado ============================
    r = ContractTestResults("T12 — log auditável gerado em logs/decisions.jsonl")
    try:
        log_path = LOGS_DIR / "decisions.jsonl"
        assert log_path.exists(), f"arquivo não encontrado: {log_path}"
        lines = log_path.read_text().strip().split("\n")
        last  = json.loads(lines[-1])
        for field in ["event_id", "timestamp", "arm_chosen",
                       "policy_version", "reason_codes"]:
            assert field in last, f"campo ausente no log: {field}"
        r.ok(f"{len(lines)} entradas no log")
    except Exception as e:
        r.fail(str(e))
    results.append(r)

    # === T13: estimates cobre todos os braços =====================
    r = ContractTestResults("T13 — estimates cobre todos os ARMS")
    try:
        resp = client.decide(ctx)
        for arm in ARMS:
            assert arm in resp["estimates"], f"arm ausente em estimates: {arm}"
            est = resp["estimates"][arm]
            assert "mean" in est and "std" in est
        r.ok(f"{len(ARMS)} braços estimados")
    except Exception as e:
        r.fail(str(e))
    results.append(r)
    
    return results

# ══════════════════════════════════════════════════════════════════
# 3. EXEMPLO DE CHAMADA CURL
# ══════════════════════════════════════════════════════════════════

def generate_curl_example(feature_cols: list) -> str:
    ctx = {f: 0.0 for f in feature_cols}
    ctx.update({'age': 42.0, 'campaign': 1.0,
                'poutcome': 3.0, 'contacted_before': 1.0})
    
    decide_body = json.dumps({'client_features': ctx}, indent=2)

    return f"""
# ═════ EXEMPLOS DE USO DA API (salve em docs/api-examples.sh) ══════════════

# 1. Healthcheck
curl http://localhost:8000/health
 
# 2. Listar braços disponíveis
curl http://localhost:8000/arms
 
# 3. Pedir uma decisão
curl -X POST http://localhost:8000/decide \\
  -H "Content-Type: application/json" \\
  -d '{decide_body}'
 
# 4. Registrar recompensa (use o event_id retornado acima)
curl -X POST http://localhost:8000/reward \\
  -H "Content-Type: application/json" \\
  -d '{{"event_id": "<EVENT_ID>", "arm": "dep_6m_8pct", "reward": 1}}'
 
# 5. Interface Swagger (abra no navegador)
# http://localhost:8000/docs
"""

# ══════════════════════════════════════════════════════════════════
# 4. RUNNER
# ══════════════════════════════════════════════════════════════════

def run(model_artifacts: dict) -> dict:
    print("\n=== ETAPA 5: SERVIÇO E TESTES DE CONTRATO ===")
    
    bandit       = model_artifacts['bandit']
    feature_cols = model_artifacts['feature_cols']

    client  = BanditAPIClient(bandit, feature_cols)
    results = run_contract_tests(client, feature_cols)

    # Relatório
    passed = [r for r in results if r.passed]
    failed = [r for r in results if not r.passed]

    print(f'\n{"-"*55}')
    for r in results:
        icon = "✓" if r.passed else "✗"
        msg  = f"  {r.message}" if r.message else ""
        print(f"  {icon}  {r.name}{msg}")
    print(f"{'─'*55}")
    print(f"  {len(passed)}/{len(results)} testes passaram")

    if failed:
        print('\n FALHAS:')
        for r in failed:
            print(f'      x {r.name}: {r.message}')

    # Salva relatório
    REPORTS_DIR.mkdir(exist_ok=True)
    report = {
        "total":   len(results),
        "passed":  len(passed),
        "failed":  len(failed),
        "pass_rate": round(len(passed) / len(results), 4),
        "results": [{"name": r.name, "passed": r.passed, "message": r.message}
                    for r in results],
    }
    report_path = REPORTS_DIR / "contract_tests.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n  Relatório salvo: {report_path}")
 
    # Exemplos curl
    curl_examples = generate_curl_example(feature_cols)
    curl_path = REPORTS_DIR / "api_curl_examples.sh"
    with open(curl_path, "w") as f:
        f.write(curl_examples)
    print(f"  Exemplos curl salvos: {curl_path}")
    print(curl_examples)
 
    print("\n  Para subir a API localmente:")
    print("    uvicorn app.main:app --reload --port 8000")
    print("    http://localhost:8000/docs")
 
    return report
 
 
if __name__ == "__main__":
    print("Execute via: python pipeline.py --step 5")