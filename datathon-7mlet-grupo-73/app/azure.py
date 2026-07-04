"""
Etapa 6 — Arquitetura-alvo Azure
==================================
Conecta com:
  - src_config.py        : ARMS, POLICY_VERSION, paths
  - step3_model.py       : bandit_metrics (para FinOps / custo estimado)
  - step4_evaluation.py  : golden_pass_rate (para a seção de qualidade)
  - reports/             : lê métricas já geradas e as embute na documentação

O que esta etapa gera:
  - docs/architecture-azure.md  (diagrama Mermaid + mapeamento de serviços)
  - docs/finops-estimate.md     (estimativa de custo qualitativa por serviço)
"""

import json
from pathlib import Path
from src_config import (
    ARMS, POLICY_VERSION,
    REPORTS_DIR, ROOT,
)

DOCS_DIR = ROOT / "docs"

# ══════════════════════════════════════════════════════════════════
# 1. DIAGRAMA MERMAID
# ══════════════════════════════════════════════════════════════════

MERMAID_DIAGRAM = """
```mermaid
flowchart TD
    subgraph Ingestão["🗄️ Ingestão de Dados"]
        A1[Kaggle Dataset JYB] -->|CSV processado| A2[Azure Blob Storage\\ndata/processed/]
        A3[Enriquecimento Sintético] -->|offer_events.jsonl| A2
    end

    subgraph Treino["🧠 Treino e Experimentação"]
        A2 -->|lê dados| B1[Azure ML Compute\\nConversionNet PyTorch]
        B1 -->|loga métricas| B2[Azure ML Experiments\\nMLflow Tracking]
        B1 -->|registra modelo| B3[Azure ML Model Registry\\nconversion_net_jyb/Production]
    end

    subgraph Serviço["⚡ Serviço de Decisão"]
        B3 -->|carrega modelo| C1[Azure Container Apps\\nFastAPI /decide /reward]
        C1 -->|log auditável| C2[Azure Blob Storage\\nlogs/decisions.jsonl]
        C1 -->|secrets| C3[Azure Key Vault\\nMLflow URI, credenciais]
        C3 -->|Managed Identity| C1
    end

    subgraph Assistente["🤖 Assistente LLM + RAG"]
        C2 -->|contexto de decisões| D1[Azure AI Search\\nÍndice vetorial]
        D1 -->|retrieval| D2[Azure OpenAI\\nGPT-4o mini]
        D2 -->|explica decisões| D3[Interface do assistente]
    end

    subgraph Observabilidade["📊 Observabilidade"]
        C1 -->|métricas| E1[Azure Monitor\\nApp Insights]
        E1 -->|alerta drift| E2[Evidently AI\\nDrift Report]
        E2 -->|trigger| B1
    end

    subgraph Governança["🔐 Governança e Segurança"]
        F1[Azure Active Directory\\nMSAL / Managed Identity]
        F2[Azure Policy\\nCompliance LGPD]
        F3[GitHub Actions\\nCI/CD + Approval Gate]
        F3 -->|promove modelo| B3
    end
```
"""


# ══════════════════════════════════════════════════════════════════
# 2. MAPEAMENTO DE SERVIÇOS AZURE
# ══════════════════════════════════════════════════════════════════

AZURE_SERVICES = [
    {
        "camada":   "Compute / Treino",
        "servico":  "Azure Machine Learning",
        "uso":      "Treino do ConversionNet, rastreio MLflow, registro de modelos",
        "sku":      "Standard_DS3_v2 (CPU) ou NC6 (GPU se necessário)",
        "alternativa_descartada": "Azure Databricks — custo maior para volume atual",
    },
    {
        "camada":   "API / Serviço",
        "servico":  "Azure Container Apps",
        "uso":      "Hospeda FastAPI /decide /reward — escala a zero quando sem requisições",
        "sku":      "Consumption plan (pay-per-use)",
        "alternativa_descartada": "AKS — overhead operacional desnecessário nesta fase",
    },
    {
        "camada":   "Dados",
        "servico":  "Azure Blob Storage",
        "uso":      "Armazena datasets, artefatos de modelo, logs auditáveis, golden set",
        "sku":      "LRS Standard (Hot tier para logs, Cool para histórico)",
        "alternativa_descartada": "Azure Data Lake Gen2 — adequado se volume > 1TB",
    },
    {
        "camada":   "IA / RAG",
        "servico":  "Azure AI Search",
        "uso":      "Índice vetorial para RAG do assistente LLM (políticas + experimentos)",
        "sku":      "Basic (até 15 índices, 2GB)",
        "alternativa_descartada": "FAISS local — sem HA e sem integração nativa Azure",
    },
    {
        "camada":   "IA / LLM",
        "servico":  "Azure OpenAI",
        "uso":      "Modelo GPT-4o mini para o assistente que explica decisões do bandit",
        "sku":      "Pay-per-token (gpt-4o-mini)",
        "alternativa_descartada": "Claude via API — fora do ecossistema Azure nativo",
    },
    {
        "camada":   "Segredos",
        "servico":  "Azure Key Vault",
        "uso":      "MLflow Tracking URI, connection strings, API keys do Azure OpenAI",
        "sku":      "Standard",
        "alternativa_descartada": "Variáveis de ambiente hardcoded — violação de segurança",
    },
    {
        "camada":   "Identidade",
        "servico":  "Managed Identity + Azure AD",
        "uso":      "Container Apps acessa Key Vault e Blob sem credenciais explícitas",
        "sku":      "Incluído no Azure AD",
        "alternativa_descartada": "Service Principal com secret — rotação manual de segredos",
    },
    {
        "camada":   "Observabilidade",
        "servico":  "Azure Monitor + Application Insights",
        "uso":      "Métricas de latência, taxa de erro, alertas de drift de recompensa",
        "sku":      "Pay-per-GB (primeiros 5GB/mês gratuitos)",
        "alternativa_descartada": "Prometheus/Grafana self-hosted — maior custo operacional",
    },
    {
        "camada":   "CI/CD",
        "servico":  "GitHub Actions",
        "uso":      "Pipeline de treino, testes automatizados, approval gate, deploy",
        "sku":      "2.000 minutos/mês gratuitos",
        "alternativa_descartada": "Azure DevOps — redundante se repositório já no GitHub",
    },
    {
        "camada":   "Governança",
        "servico":  "Azure Policy + Purview",
        "uso":      "Compliance LGPD, catalogação de dados sensíveis, retenção de logs",
        "sku":      "Azure Policy gratuito; Purview pay-per-asset",
        "alternativa_descartada": "Controles manuais — não escalável e auditável",
    },
]


# ══════════════════════════════════════════════════════════════════
# 3. PLANO DE SEGREDOS (Key Vault + Managed Identity)
# ══════════════════════════════════════════════════════════════════

SECRETS_PLAN = """
## Plano de Gestão de Segredos

### Segredos armazenados no Azure Key Vault

| Nome do segredo           | Usado por                  | Rotação       |
|---------------------------|----------------------------|---------------|
| `mlflow-tracking-uri`     | Container Apps, GitHub CI  | 90 dias       |
| `azure-openai-api-key`    | Assistente LLM             | 30 dias       |
| `blob-storage-conn-str`   | Pipeline de treino         | 90 dias       |
| `ai-search-api-key`       | RAG do assistente          | 90 dias       |

### Fluxo de acesso sem credenciais hardcoded

```
Container Apps
  └── System-assigned Managed Identity
        └── Key Vault Access Policy (Get, List)
              └── segredo: mlflow-tracking-uri
```

### Configuração no Container Apps

```bash
# Adiciona segredo referenciando Key Vault (sem copiar o valor)
az containerapp secret set \\
  --name bandit-api \\
  --resource-group $RG \\
  --secrets mlflow-uri=keyvaultref:$KV_NAME/mlflow-tracking-uri

# Passa como variável de ambiente
az containerapp update \\
  --name bandit-api \\
  --set-env-vars MLFLOW_TRACKING_URI=secretref:mlflow-uri
```

### Regra: nenhuma credencial no código ou no .env commitado

O `.env.example` lista apenas os **nomes** das variáveis, nunca os valores:
```
MLFLOW_TRACKING_URI=
AZURE_OPENAI_API_KEY=
AZURE_BLOB_CONN_STR=
AI_SEARCH_API_KEY=
```
"""


# ══════════════════════════════════════════════════════════════════
# 4. ESTIMATIVA FINOPS
# ══════════════════════════════════════════════════════════════════

FINOPS_ESTIMATE = """
## Estimativa de Custo (FinOps)

> Estimativa qualitativa para carga de demonstração (Demo Day).
> Valores em USD/mês aproximados para região East US 2.

| Serviço                  | SKU / Uso estimado              | Custo mensal aprox. |
|--------------------------|---------------------------------|---------------------|
| Azure ML Compute         | DS3_v2 × 10h treino/mês         | ~$5                 |
| Azure Container Apps     | ~10k req/mês, scale-to-zero     | ~$2                 |
| Azure Blob Storage       | 10GB dados + logs               | ~$0.20              |
| Azure AI Search          | Basic, 1 índice                 | ~$75                |
| Azure OpenAI             | gpt-4o-mini, ~100k tokens/mês   | ~$0.15              |
| Azure Key Vault          | Standard, <10k operações/mês    | ~$0.05              |
| Azure Monitor            | <5GB logs/mês (tier gratuito)   | ~$0                 |
| GitHub Actions           | <2.000 min/mês (tier gratuito)  | ~$0                 |
| **Total estimado**       |                                 | **~$83/mês**        |

### TCO (Total Cost of Ownership) — Produção real

Em produção regulada com SLA 99.9%, escala para ~10k req/dia:
- Container Apps: ~$50/mês (réplicas mínimas + tráfego)
- Azure ML: ~$200/mês (retreino semanal automatizado)
- AI Search: ~$250/mês (Standard S1 para latência garantida)
- **Estimativa produção**: ~$600–800/mês

### Cenários de escala

| Volume req/dia | Componente crítico         | Ação recomendada                |
|----------------|----------------------------|---------------------------------|
| < 1k           | Container Apps scale-zero  | Consumption plan atual          |
| 1k – 50k       | Container Apps CPU         | Aumentar réplicas mínimas → 2   |
| 50k – 500k     | Blob Storage latência      | Migrar logs para Event Hub      |
| > 500k         | AI Search                  | Standard S2 + réplicas          |

### Redução de custo

- **Desligar ML Compute** fora de janelas de retreino (economia ~70%)
- **Scale-to-zero** no Container Apps em horários fora do pico
- **Tier Cool** no Blob para logs com mais de 30 dias
"""


# ══════════════════════════════════════════════════════════════════
# 5. GERAÇÃO DOS DOCUMENTOS
# ══════════════════════════════════════════════════════════════════

def load_metrics() -> dict:
    """Lê métricas geradas nas etapas anteriores para embutir na documentação."""
    metrics = {}
    sim_path  = REPORTS_DIR / "simulation_metrics.json"
    eval_path = REPORTS_DIR / "evaluation_report.json"

    if sim_path.exists():
        with open(sim_path) as f:
            sim = json.load(f)
        metrics["bandit_auc"]        = sim.get("bandit", {}).get("conversion_rate", "N/A")
        metrics["baseline_conv"]     = sim.get("baseline", {}).get("conversion_rate", "N/A")
        metrics["cumulative_regret"] = sim.get("bandit", {}).get("cumulative_regret", "N/A")

    if eval_path.exists():
        with open(eval_path) as f:
            ev = json.load(f)
        metrics["golden_pass_rate"] = ev.get("golden_pass_rate", "N/A")

    return metrics


def generate_architecture_md(metrics: dict) -> str:
    services_table = "\n".join([
        f"| {s['camada']:30s} | {s['servico']:35s} | {s['uso'][:60]:60s} |"
        for s in AZURE_SERVICES
    ])

    discarded_table = "\n".join([
        f"| {s['servico']:35s} | {s['alternativa_descartada']:60s} |"
        for s in AZURE_SERVICES if s.get("alternativa_descartada")
    ])

    conv_bandit  = f"{float(metrics.get('bandit_auc', 0))*100:.1f}%" \
                   if metrics.get("bandit_auc") != "N/A" else "N/A"
    conv_baseline = f"{float(metrics.get('baseline_conv', 0))*100:.1f}%" \
                    if metrics.get("baseline_conv") != "N/A" else "N/A"
    pass_rate    = f"{float(metrics.get('golden_pass_rate', 0))*100:.0f}%" \
                   if metrics.get("golden_pass_rate") != "N/A" else "N/A"

    return f"""# Arquitetura-Alvo Azure — Datathon 7MLET

> **Versão da política:** {POLICY_VERSION}
> **Braços disponíveis:** {', '.join(ARMS)}

## Evidências de qualidade (etapas anteriores)

| Métrica                        | Valor         |
|-------------------------------|---------------|
| Conversão bandit (simulação)  | {conv_bandit} |
| Conversão baseline            | {conv_baseline} |
| Golden set pass rate          | {pass_rate}   |

---

## Diagrama de Arquitetura

{MERMAID_DIAGRAM}

---

## Mapeamento de Serviços Azure

| Camada                          | Serviço Azure                       | Uso no projeto                                               |
|---------------------------------|-------------------------------------|--------------------------------------------------------------|
{services_table}

---

## Alternativas Descartadas

| Serviço considerado              | Motivo do descarte                                           |
|----------------------------------|--------------------------------------------------------------|
{discarded_table}

---

{SECRETS_PLAN}

---

## Plano de Deploy

```bash
# 1. Criar Resource Group
az group create --name rg-datathon-7mlet --location eastus2

# 2. Criar Azure ML Workspace
az ml workspace create \\
  --name aml-datathon \\
  --resource-group rg-datathon-7mlet

# 3. Build e push da imagem
az acr build \\
  --registry $ACR_NAME \\
  --image bandit-api:${{GITHUB_SHA}} .

# 4. Deploy no Container Apps
az containerapp create \\
  --name bandit-api \\
  --resource-group rg-datathon-7mlet \\
  --image $ACR_NAME.azurecr.io/bandit-api:${{GITHUB_SHA}} \\
  --target-port 8000 \\
  --ingress external \\
  --min-replicas 0 \\
  --max-replicas 10

# 5. Configurar Managed Identity
az containerapp identity assign \\
  --name bandit-api \\
  --resource-group rg-datathon-7mlet \\
  --system-assigned

# 6. Dar acesso ao Key Vault
az keyvault set-policy \\
  --name $KV_NAME \\
  --object-id $(az containerapp identity show \\
    --name bandit-api --resource-group rg-datathon-7mlet \\
    --query principalId -o tsv) \\
  --secret-permissions get list
```

---

{FINOPS_ESTIMATE}
"""


def run(model_artifacts: dict = None) -> dict:
    print("\n=== ETAPA 6: ARQUITETURA AZURE ===")

    DOCS_DIR.mkdir(exist_ok=True)
    metrics = load_metrics()

    # architecture-azure.md
    arch_md   = generate_architecture_md(metrics)
    arch_path = DOCS_DIR / "architecture-azure.md"
    with open(arch_path, "w", encoding="utf-8") as f:
        f.write(arch_md)
    print(f"Arquitetura salva : {arch_path}")

    print(f"\nServiços Azure mapeados: {len(AZURE_SERVICES)}")
    print(f"Diagrama Mermaid: docs/architecture-azure.md")

    return {
        "arch_path":  str(arch_path),
        "n_services": len(AZURE_SERVICES),
        "metrics":    metrics,
    }


if __name__ == "__main__":
    run()