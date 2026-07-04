# Datathon 7MLET — Grupo 73
### Plataforma de Experimentação Adaptativa com Multi-Armed Bandit

> Uma instituição financeira digital precisa decidir, em tempo real, qual oferta mostrar para cada cliente.  
> Em vez de regras fixas ou testes A/B longos, usamos **Thompson Sampling Contextual** com uma rede neural (PyTorch)  
> que aprende com cada interação e equilibra exploração e explotação automaticamente.

---

## Sumário

- [O problema](#o-problema)
- [Instalação](#instalação)
- [Como rodar](#como-rodar)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Etapa 0 — Configuração](#etapa-0--configuração)
- [Etapa 1 — Base Kaggle e EDA](#etapa-1--base-kaggle-e-eda)
- [Etapa 2 — Enriquecimento Sintético](#etapa-2--enriquecimento-sintético)
- [Etapa 3 — Modelagem e Algoritmo Bandit](#etapa-3--modelagem-e-algoritmo-bandit)
- [Etapa 4 — Avaliação Offline](#etapa-4--avaliação-offline)
- [Etapa 5 — API e Testes de Contrato](#etapa-5--api-e-testes-de-contrato)
- [Etapa 6 — Arquitetura Azure](#etapa-6--arquitetura-azure)
- [Etapa 7 — MLOps](#etapa-7--mlops)
- [Limitações conhecidas](#limitações-conhecidas)

---

## O problema

Bancos digitais precisam personalizar ofertas (depósitos, cashback, previdência) para cada cliente.  
Regras fixas são rígidas demais. Testes A/B demoram semanas. O **Multi-Armed Bandit** resolve isso:

- **Exploração** → testa ofertas menos conhecidas para descobrir novas oportunidades
- **Explotação** → aproveita o que já sabe para maximizar conversão
- **Contexto** → considera o perfil do cliente para tomar decisões mais inteligentes

---

## Instalação

**Pré-requisito:** Python 3.11+

```bash
# Clone o repositório
git clone https://github.com/Mathvivas/pos-tech-fiap-alura.git
cd datathon-7mlet-grupo-73

# Crie e ative o ambiente virtual
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Instale o PyTorch sem CUDA (CPU-only, mais leve)
pip install torch --index-url https://download.pytorch.org/whl/cpu

# Instale o restante das dependências
pip install .
```

**Configure as variáveis de ambiente:**

```bash
cp .env.example .env
# Edite o .env com seus valores (veja a seção Etapa 0)
```

---

## Como rodar

```bash
# Pipeline completo (todas as etapas em sequência)
python pipeline.py

# Rodar apenas uma etapa específica
python pipeline.py --step 1    # só dados
python pipeline.py --step 3    # só treino
python pipeline.py --step 5    # só testes de contrato
python pipeline.py --step 7    # só MLOps

# Pular o treino (reutiliza modelo já salvo)
python pipeline.py --skip-train

# Subir a API localmente (após rodar o pipeline ao menos uma vez)
uvicorn app.main:app --reload --port 8000
# Acesse a documentação interativa: http://localhost:8000/docs
```

---

## Estrutura do projeto

```
datathon-7mlet-grupo-73/
│
├── pipeline.py               # Orquestrador principal — roda tudo em sequência
├── src_config.py             # Constantes globais (braços, colunas, paths, seeds)
│
├── app/
│   ├── model.py              # Etapa 3: treina o modelo e roda o bandit
│   ├── evaluation.py         # Etapa 4: avaliação offline e análise de fairness
│   ├── api.py                # Etapa 5: testes de contrato da API
│   ├── azure.py              # Etapa 6: gera documentação de arquitetura Azure
│   ├── mlops.py              # Etapa 7: drift, retreino, approval gate, rollback
│   ├── pipeline.py
│   └── main.py               # API FastAPI (/decide, /reward, /health, /arms)
│
├── data/
│   ├── kaggle/               # Dataset original do Kaggle
│         └── kaggle.py       # Etapa 1: carrega e limpa o dataset Kaggle
│   ├── processed/            # Dataset limpo, sem leakage
│   ├── synthetic_enrichment/ # Catálogo de ofertas, eventos e recompensas
│         └── synthetic.py    # Etapa 2: gera dados sintéticos de experimentação
│   └── golden_set/           # Casos de avaliação versionados
│
├── models/                   # Modelos treinados (.pt) e artefatos de pré-processamento
├── logs/                     # Log auditável de decisões (decisions.jsonl)
├── reports/                  # Métricas, relatórios de drift e testes de contrato
├── docs/                     # Documentação técnica (arquitetura, MLOps, LGPD)
│
├── Dockerfile                # Empacota a API para deploy no Azure Container Apps
├── pyproject.toml            # Dependências e ponto de entrada
└── .env.example              # Variáveis de ambiente necessárias (sem valores reais)
```

---

## Etapa 0 — Configuração

**Arquivo:** `src_config.py` + `.env`

Define todas as constantes do projeto em um único lugar, evitando valores hardcoded espalhados pelo código.

**O que configurar no `.env`:**

```bash
# Mínimo para rodar localmente
MLFLOW_TRACKING_URI=sqlite:///mlruns.db
POLICY_VERSION=v1.0

# Necessário apenas se for usar o assistente LLM ou deploy Azure
AZURE_OPENAI_API_KEY=
AZURE_BLOB_CONN_STR=
AI_SEARCH_API_KEY=
AI_SEARCH_ENDPOINT=
KEY_VAULT_NAME=
```

**Constantes principais definidas em `src_config.py`:**

| Constante | Valor | Descrição |
|-----------|-------|-----------|
| `ARMS` | 5 ofertas | Braços disponíveis para o bandit |
| `SEED` | 42 | Semente global para reprodutibilidade |
| `POLICY_VERSION` | v1.0 | Versão atual da política de decisão |
| `MLFLOW_EXPERIMENT` | datathon-jyb-bandit | Nome do experimento no MLflow |

---

## Etapa 1 — Base Kaggle e EDA

**Arquivo:** `kaggle.py`  
**Comando:** `python pipeline.py --step 1`

Carrega o dataset [Telemarketing JYB](https://www.kaggle.com/datasets/aguado/telemarketing-jyb-dataset) (campanhas bancárias de telemarketing), remove a coluna `duration` que causa vazamento temporal, e salva a versão processada.

**Por que remover `duration`?**  
A duração da chamada só é conhecida *depois* que o contato termina. Usar essa informação no modelo seria trapaça — no momento da decisão de qual oferta fazer, ela não existe ainda.

**O que esta etapa produz:**

| Arquivo | Descrição |
|---------|-----------|
| `data/kaggle/bank_jyb.csv` | Dataset original baixado do Kaggle |
| `data/processed/bank_jyb_processed.csv` | Dataset limpo, sem `duration`, pronto para modelagem |

**Saída esperada no terminal:**
```
Dataset carregado: 4,521 linhas x 17 colunas
Colunas removidas (leakage): ['duration']
Taxa de conversão: 11.52%
Dataset processado salvo: data/processed/bank_jyb_processed.csv
```

> **Atenção:** a taxa de conversão de ~11% indica dataset desbalanceado.  
> Accuracy não é uma boa métrica — usamos AUC-ROC e Average Precision.

---

## Etapa 2 — Enriquecimento Sintético

**Arquivo:** `synthetic.py`  
**Comando:** `python pipeline.py --step 2`

O dataset Kaggle tem dados históricos de campanhas, mas não tem o formato de experimentação em tempo real que o bandit precisa. Esta etapa cria essa camada sintética em cima dos dados reais.

**O que é criado:**

| Arquivo | O que representa |
|---------|-----------------|
| `data/synthetic_enrichment/offer_catalog.json` | Os 5 braços disponíveis com taxa de conversão base, canal e segmento-alvo |
| `data/synthetic_enrichment/offer_events.jsonl` | 3.000 eventos de impressão: qual oferta foi mostrada, para qual segmento, em qual contexto |
| `data/synthetic_enrichment/delayed_rewards.jsonl` | Resultado de cada evento: o cliente converteu? Quantos dias depois? |
| `data/golden_set/evaluation_cases.jsonl` | 30 casos de teste com resposta esperada e critério pass/fail |

**Os 5 braços (ofertas):**

| ID | Nome | Canal | Taxa base |
|----|------|-------|-----------|
| `dep_6m_8pct` | Depósito 6m 8% a.a. | App | 18% |
| `dep_12m_10pct` | Depósito 12m 10% a.a. | Email | 14% |
| `reativacao` | Oferta de Reativação | SMS | 28% |
| `cashback` | Cashback no débito | App | 9% |
| `previdencia` | Previdência Privada | Email | 12% |

**Os 5 segmentos de clientes (definidos no EDA):**

| Segmento | Perfil | Taxa esperada |
|----------|--------|---------------|
| A — Reativação positiva | Tinha convertido antes (`poutcome=success`) | Alta |
| B — Reativação negativa | Tinha rejeitado antes (`poutcome=failure`) | Baixa |
| C — Alta propensão | Estudante ou aposentado | Acima da média |
| D — Comprometido financeiro | Tem empréstimo habitacional ou pessoal | Abaixo da média |
| E — Cold-start | Nunca foi contactado (`pdays=-1`) | Base |

**Por que delayed rewards?**  
Na vida real, um cliente não converte na hora — pode levar de 1 a 30 dias. O arquivo `delayed_rewards.jsonl` simula isso com uma distribuição exponencial truncada (maioria em 1–7 dias, cauda até 30 dias).

---

## Etapa 3 — Modelagem e Algoritmo Bandit

**Arquivo:** `model.py`  
**Comando:** `python pipeline.py --step 3`

O coração do projeto. Esta etapa treina a rede neural, inicializa o bandit e roda a simulação comparando o Thompson Sampling contra o baseline determinístico.

### Como o modelo funciona

```
Contexto do cliente (15 features)
        +
Features da oferta (2 features: prazo e taxa)
        ↓
  ConversionNet (PyTorch)
  - LayerNorm + Dropout(0.3)
  - 2 camadas ocultas (64 → 32 neurônios)
        ↓
  Logit → Sigmoid → P(conversão)
        ↓
  MC Dropout (30 passagens)
  → média = estimativa de conversão
  → desvio padrão = incerteza
        ↓
  Thompson Sampling
  → sorteia Normal(média, std) para cada braço
  → escolhe o braço com maior amostra
```

### Por que MC Dropout?

O Dropout normalmente é desligado na inferência. Aqui deixamos **ligado** — isso faz cada passagem pelo modelo dar um resultado ligeiramente diferente. A variância entre as 30 passagens é nossa medida de **incerteza**. Alta incerteza → o modelo está explorando. Baixa incerteza → o modelo está confiante e explotando.

### Baseline determinístico

Para comparar com o bandit, implementamos uma política simples que sempre escolhe o braço com maior taxa histórica (`reativacao`, 28%). Isso nos permite medir o ganho real do Thompson Sampling.

**O que esta etapa produz:**

| Arquivo | Descrição |
|---------|-----------|
| `models/conversion_net.pt` | Modelo treinado (pesos + metadados) |
| `models/preprocessing.pkl` | Encoders, scaler e feature_cols para inferência |
| `reports/simulation_metrics.json` | Comparativo bandit vs baseline |

**Saída esperada no terminal:**
```
input_dim: 15 (cliente) + 2 (oferta) = 17
Treino: 18,084 | Val: 4,522 | pos_tr=11.52% | pos_vl=11.48%

  Epoch  10 | train=0.4821 | val=0.4634 | auc=0.6981 | apr=0.2341
  Epoch  20 | train=0.4712 | val=0.4521 | auc=0.7124 | apr=0.2489
  ...
  Epoch  80 | train=0.4301 | val=0.4198 | auc=0.7312 | apr=0.2701

=== COMPARATIVO: BANDIT vs BASELINE ===
  total_reward               1432         1187
  conversion_rate          0.1589       0.1319
  cumulative_regret       524.32       763.41
  exploration_rate         0.8124       0.0000
```

> O bandit converte mais que o baseline e tem regret acumulado menor — mesmo explorando 81% do tempo.

---

## Etapa 4 — Avaliação Offline

**Arquivo:** `evaluation.py`  
**Comando:** `python pipeline.py --step 4`

Antes de servir o modelo, avaliamos sua qualidade de forma controlada e reproduzível.

**Golden set:** 30 casos versionados em `data/golden_set/evaluation_cases.jsonl`, cobrindo:
- Casos típicos por segmento
- Casos de borda (cold-start, clientes comprometidos)
- Cenários adversariais (ex: oferta de previdência para cold-start — não deve ocorrer)

Cada caso tem contexto, oferta esperada, recompensa esperada e critério explícito de **pass/fail**.

**Análise de fairness:** verifica se todos os segmentos estão sendo servidos com proporções equitativas de exposição — nenhum grupo deve ser sistematicamente ignorado pelo bandit.

**O que esta etapa produz:**

| Arquivo | Descrição |
|---------|-----------|
| `reports/evaluation_report.json` | Pass rate do golden set + fairness por segmento |

**Saída esperada:**
```
=== AVALIAÇÃO GOLDEN SET (30 casos) ===
Pass rate: 100.0%
type
adversarial    1.0
edge           1.0
random         1.0
typical        1.0
```

---

## Etapa 5 — API e Testes de Contrato

**Arquivo:** `api.py` + `main.py`  
**Comando:** `python pipeline.py --step 5`

Expõe o bandit como serviço HTTP com log auditável de cada decisão.

### Endpoints disponíveis

| Método | Endpoint | O que faz |
|--------|----------|-----------|
| `GET` | `/health` | Status da API e versão da política |
| `GET` | `/arms` | Lista os braços disponíveis |
| `POST` | `/decide` | Recebe contexto do cliente → retorna oferta escolhida |
| `POST` | `/reward` | Registra se o cliente converteu (pode ser enviado dias depois) |

### Exemplo de chamada

```bash
# Pedir uma decisão
curl -X POST http://localhost:8000/decide \
  -H "Content-Type: application/json" \
  -d '{
    "client_features": {
      "age": 42, "campaign": 1, "pdays_clean": 0,
      "previous": 0, "contacted_before": 0,
      "job": 2, "marital": 1, "education": 3,
      "default": 0, "housing": 1, "loan": 0,
      "contact": 2, "month": 4, "poutcome": 0
    }
  }'

# Resposta
{
  "event_id": "a3f2b1c4-...",
  "arm_chosen": "reativacao",
  "policy_version": "v1.0",
  "reason_codes": {
    "estimated_conversion": 18.42,
    "uncertainty_std": 0.0389,
    "exploring": false,
    "ts_sample": 0.1923
  },
  "estimates": {
    "dep_6m_8pct":   {"mean": 0.1421, "std": 0.0312},
    "dep_12m_10pct": {"mean": 0.1187, "std": 0.0298},
    "reativacao":    {"mean": 0.1842, "std": 0.0389},
    "cashback":      {"mean": 0.0934, "std": 0.0271},
    "previdencia":   {"mean": 0.1102, "std": 0.0301}
  }
}
```

### Log auditável

Cada chamada ao `/decide` gera uma entrada em `logs/decisions.jsonl` com:
- `event_id` — identificador único da decisão
- `timestamp` — momento exato
- `arm_chosen` — qual oferta foi escolhida
- `policy_version` — qual versão da política foi usada
- `reason_codes` — estimativa de conversão, incerteza e flag de exploração

### Testes de contrato (13 testes)

A etapa 5 roda automaticamente 13 testes que verificam que a API se comporta corretamente:

```
✓  T01 — /health retorna status=ok
✓  T02 — /arms retorna braços corretos
✓  T03 — /decide retorna arm_chosen, event_id, reason_codes
✓  T04 — arm_chosen é um dos ARMS definidos
✓  T05 — reason_codes tem estimated_conversion, uncertainty_std, exploring
✓  T06 — policy_version propagado corretamente
✓  T07 — /decide com features ausentes levanta ValueError
✓  T08 — /reward com dados válidos retorna status=ok
✓  T09 — /reward com reward=0 (sem conversão) funciona
✓  T10 — /reward com arm inválido levanta ValueError
✓  T11 — /reward com reward=2 levanta ValueError
✓  T12 — log auditável gerado em logs/decisions.jsonl
✓  T13 — estimates cobre todos os ARMS
```

**O que esta etapa produz:**

| Arquivo | Descrição |
|---------|-----------|
| `reports/contract_tests.json` | Resultado dos 13 testes com pass/fail individual |
| `reports/api_curl_examples.sh` | Exemplos prontos de chamadas curl |
| `logs/decisions.jsonl` | Log auditável das decisões |

---

## Etapa 6 — Arquitetura Azure

**Arquivo:** `azure.py`  
**Comando:** `python pipeline.py --step 6`

Documenta como a solução seria operada em produção no Azure, com todas as camadas obrigatórias.

**Serviços Azure mapeados:**

| Camada | Serviço |
|--------|---------|
| Treino e experimentação | Azure Machine Learning + MLflow |
| API de decisão | Azure Container Apps (FastAPI) |
| Armazenamento | Azure Blob Storage |
| Assistente LLM + RAG | Azure OpenAI + Azure AI Search |
| Segredos | Azure Key Vault + Managed Identity |
| Observabilidade | Azure Monitor + Application Insights |
| CI/CD + Approval gate | GitHub Actions |
| Governança | Azure Policy |

**Gestão de segredos (sem credenciais no código):**

```
Container Apps
  └── Managed Identity (sem senha)
        └── Azure Key Vault
              └── Segredos: MLflow URI, OpenAI Key, Blob Conn String...
```

**O que esta etapa produz:**

| Arquivo | Descrição |
|---------|-----------|
| `docs/architecture-azure.md` | Diagrama Mermaid + mapeamento completo de serviços |
| `.env.example` | Template de variáveis de ambiente (sem valores reais) |

---

## Etapa 7 — MLOps

**Arquivo:** `mlops.py`  
**Comando:** `python pipeline.py --step 7`

Simula o ciclo completo de vida de uma política: detecção de drift → retreino → approval gate → promoção → rollback disponível.

### Ciclo de vida de uma nova política

```
Monitoramento contínuo
        ↓
  Drift detectado?
   ↓           ↓
  Sim          Não → continua monitorando
   ↓
Retreino do candidato (v2.0)
        ↓
   Approval Gate
   ↓           ↓
Aprovado    Rejeitado → investigação humana
   ↓
Promoção para produção
        ↓
Versão anterior salva para rollback
```

### Detecção de drift

**Drift de recompensa:** compara a taxa de conversão em janelas de 7 dias. Se a variação entre janelas consecutivas passar de 5 pontos percentuais, o retreino é acionado.

**Drift de features (PSI):** compara a distribuição das features numéricas (`age`, `campaign`, `previous`, `pdays_clean`) entre dados de treino e dados recentes.

| PSI | Ação |
|-----|------|
| < 0.10 | Estável — nenhuma ação |
| 0.10 – 0.20 | Monitorar com atenção |
| > 0.20 | Retreino necessário |

### Approval gate

O candidato é aprovado automaticamente se:
1. AUC ≥ AUC atual − 2pp (não regrediu significativamente)
2. AUC ≥ 0.60 (mínimo absoluto de qualidade)

Se algum critério falhar, o candidato fica com status `pending_human_approval` e o modelo em produção permanece inalterado.

### Rollback

Se um modelo promovido degradar em produção:

```bash
# A versão anterior é sempre salva automaticamente
# models/conversion_net_v1.0_rollback.pt
python pipeline.py --rollback v1.0
```

**O que esta etapa produz:**

| Arquivo | Descrição |
|---------|-----------|
| `reports/drift_report.json` | PSI por feature e variação de recompensa por janela |
| `reports/mlops_cycle.json` | Histórico completo do ciclo: drift → candidato → aprovação → promoção |
| `docs/mlops-plan.md` | Plano documentado com critérios, cadência e responsáveis |
| `models/conversion_net_v2.0.pt` | Modelo candidato (se retreino foi acionado) |

---

## Limitações conhecidas

- **Dataset sintético:** os dados de eventos e recompensas são gerados sinteticamente com base nas taxas reais do JYB. Uma produção real exigiria eventos de interação genuína com clientes.
- **Sem dados reais de clientes:** nenhum dado identificável, patrimônio, renda, gênero ou raça é usado. Todas as decisões sensíveis mantêm humano no loop.
- **AUC em torno de 0.70:** o sinal preditivo do dataset JYB é moderado (Upper bound com GBM ≈ 0.72). Variáveis macroeconômicas do dataset estendido (`euribor3m`, `cons.conf.idx`) melhorariam significativamente esse número.
- **Retreino online limitado:** o `retrain()` usa apenas 5 épocas para não distorcer o modelo base. Em produção, retreinos mais completos seriam agendados fora do horário de pico.
- **Não pronto para produção regulada:** este projeto demonstra maturidade técnica e de engenharia. Antes de operar em ambiente bancário real, seriam necessárias auditorias de segurança, validação regulatória e aprovação do compliance.

---

## Referências

- Moro, S., Cortez, P., & Rita, P. (2014). *A Data-Driven Approach to Predict the Success of Bank Telemarketing.* Decision Support Systems.
- Dataset: [aguado/telemarketing-jyb-dataset](https://www.kaggle.com/datasets/aguado/telemarketing-jyb-dataset) — Kaggle, CC0
- Thompson, W. R. (1933). *On the likelihood that one unknown probability exceeds another.*
- Chapelle, O., & Li, L. (2011). *An empirical evaluation of Thompson Sampling.*
- Gal, Y., & Ghahramani, Z. (2016). *Dropout as a Bayesian Approximation.*