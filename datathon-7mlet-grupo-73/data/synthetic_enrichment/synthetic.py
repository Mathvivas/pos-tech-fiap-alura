"""
ETAPA 2 - Enriquecimento sintético de dados
Gera offer_catalog, offer_events e delayed_rewards separados do dataset Kaggle.
"""
import json
import uuid
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from src_config import *

np.random.seed(SEED)

# ============================== Segmentação de clientes (definida no EDA) ==============================

def assign_segment(row: pd.Series) -> str:
    poutcome = str(row.get('poutcome', 'unknown'))
    job      = str(row.get('job', ''))
    housing  = str(row.get('housing', 'no'))
    loadn    = str(row.get('loan', 'no'))
    pdays    = int(row.get('pdays', -1))

    if poutcome == 'success':
        return 'A_reativacao_positiva'
    elif pdays != -1 and poutcome == 'failure':
        return 'B_reativacao_negativa'
    elif job in ['student', 'retired']:
        return 'C_alta_propensao'
    elif housing == 'yes' and loadn == 'yes':
        return 'D_comprometido_financeiramente'
    else:
        return 'E_cold_start_generico'
    
# ============================== Geração do catálogo de ofertas ==============================

def generate_offer_catalog() -> list:
    """
    Define os braços disponíveis para o bandit.
    base_conversion_rate calibrado pelas taxas reais do JYB por segmento.
    """
    catalog = [
        {
            'offer_id':             arm,
            'name':                 name,
            'channel':              channel,
            'duration_months':      ARM_FEATURES[arm]['duration_months'],
            'rate':                 ARM_FEATURES[arm]['rate'],
            'segment_affinity':     affinity,
            'base_conversion_rate': ARM_TRUE_RATES[arm],
            'description':          desc,
        }
        for arm, name, channel, affinity, desc in [
            ("dep_6m_8pct", "Depósito 6m 8% a.a.", "app", ["A_reativacao_positiva","C_alta_propensao"], "Depósito de curto prazo com rentabilidade atrativa"),
            ("dep_12m_10pct", "Depósito 12m 10% a.a.", "email", ["A_reativacao_positiva","B_reativacao_negativa"], "Depósito de médio prazo com taxa competitiva"),
            ("reativacao", "Oferta de Reativação", "sms", ["A_reativacao_positiva"], "Oferta personalizada para clientes com histórico positivo"),
            ("cashback", "Cashback no débito", "app", ["C_alta_propensao","E_cold_start_generico"], "Benefício imediato para novos engajamentos"),
            ("previdencia", "Previdência Privada", "email", ["C_alta_propensao","D_comprometido_financeiro"], "Produto de longo prazo para planejamento financeiro"),
        ]
    ]
    return catalog

# ============================== Geração de eventos de impressão ==============================

def generate_offer_events(df: pd.DataFrame, n_events: int = 3000) -> pd.DataFrame:
    """
    Cada evento = uma decisão do badit sobre qual oferta mostrar.
    Inclui contexto do cliente no momento da decisão.
    """
    df = df.copy()
    df['segment'] = df.apply(assign_segment, axis=1)

    base_data = datetime(2026, 1, 1)
    events    = []

    # Distribui os n_eventos pelas linhas do dataset
    indices = np.random.choice(len(df), size=n_events, replace=True)

    for i, idx in enumerate(indices):
        row     = df.iloc[idx]
        segment = row['segment']

        # Braço escolhido com leve viés para o segmento (simula política inicial)
        affinity_bonus = {
            arm: (0.3 if segment in catalog_entry['segment_affinity'] else 0.0)
            for arm, catalog_entry in zip(ARMS, generate_offer_catalog())
        }
        probs      = np.array([1.0 + affinity_bonus[arm] for arm in ARMS])
        probs      = probs / probs.sum()
        arm_chosen = np.random.choice(ARMS, p=probs)

        timestamp = base_data + timedelta(
            days=np.random.randint(0, 365),
            hours=np.random.randint(8, 20),
        )

        events.append({
            'event_id':       str(uuid.uuid4()),
            'client_index':   int(idx),
            'timestamp':      timestamp.isoformat(),
            'client_segment': segment,
            'context': {
                'age_group':        str(pd.cut([row['age']],
                                    bins=[17, 25, 35, 45, 55, 65, 90],
                                    labels=['18-25','26-35','36-45','46-55','56-65','66+'])[0]),
                'contacted_before': int(row.get('pdays', -1) != -1),
                'poutcome':         str(row.get('poutcome', 'unknown')),
                'channel':          str(row.get('contact', 'unknown')),
            },
            'arm_chosen':     arm_chosen,
            'algorithm':      'thompson_sampling',
            'policy_version': POLICY_VERSION,
        })

    return pd.DataFrame(events)

# ============================== Geração de recomepensas atrasadas ==============================

def generate_delayed_rewards(events_df: pd.DataFrame,
                             df_orginal: pd.DataFrame) -> pd.DataFrame:
    """
    Simula o fechamento da recompensa após horizonte de observação.
    Delay: distribuição exponencial truncada (maioria converte em 1-7 dias).
    Reward = 0 ou 1, calibrado pela taxa real do braço + segmento do cliente.
    """
    rewards = []

    for _, ev in events_df.iterrows():
        arm       = ev['arm_chosen']
        segment   = ev['client_segment']
        base_rate = ARM_TRUE_RATES.get(arm, 0.10)

        # Ajuste por segmento
        segment_multiplier = {
            'A_reativacao_positiva':          2.0,
            'B_reativacao_negativa':          0.5,
            'C_alta_propensao':               1.3,
            'D_comprometido_financeiramente': 0.7,
            'E_cold_start_generico':          1.0,
        }.get(segment, 1.0)

        conv_prob = np.clip(base_rate * segment_multiplier, 0.02, 0.90)
        reward    = int(np.random.random() < conv_prob)

        # Delay: exponencial truncada em REWARD_HORIZON_DAYS dias
        if reward == 1:
            delay = int(min(
                np.random.exponential(scale=REWARD_MEAN_DAYS),
                REWARD_HORIZON_DAYS
            )) + 1
        else:
            delay = REWARD_HORIZON_DAYS  # Não converteu -> observado no fim do horizonte

        obs_time = datetime.fromisoformat(ev['timestamp']) + timedelta(days=delay)

        rewards.append({
            'event_id':           ev['event_id'],
            'reward':             reward,
            'delay_days':         delay,
            'reward_observed_at': obs_time.isoformat(),
            'horizon_days':       REWARD_HORIZON_DAYS,
        })

        return pd.DataFrame(rewards)

# ============================== Golden set ==============================

def generate_golden_set(df: pd.DataFrame,
                        events_df: pd.DataFrame,
                        rewards_df: pd.DataFrame,
                        n_cases: int = 30) -> list:
    """
    Gera casos de avaliação com contexto, ação esperada e critério pass/fail.
    Cobre: típicos, borda, adversariais e segemtnos de fairness.
    """
    merged = events_df.merge(rewards_df, on='event_id')
    cases  = []

    case_templates = [
        # (segmento,                  arm_esperado,    justificativa,                                                      tipo)
        ("A_reativacao_positiva",     "reativacao",    "Cliente com histórico positivo deve receber oferta de reativação", "typical"),
        ("A_reativacao_positiva",     "dep_6m_8pct",   "Alternativa válida para reativação positiva",                      "typical"),
        ("C_alta_propensao",          "dep_6m_8pct",   "Estudante/aposentado: alta propensão para depósito curto",         "typical"),
        ("E_cold_start_generico",     "cashback",      "Cold-start: oferta de baixo compromisso para engajamento inicial", "edge"),
        ("D_comprometido_financeiro", "cashback",      "Cliente endividado: não deve receber produtos de alto valor",      "edge"),
        ("B_reativacao_negativa",     "cashback",      "Reativação negativa: oferta simples para reconquistar",            "adversarial"),
        ("E_cold_start_generico",     "previdencia",   "Cold-start NÃO deve receber previdência — produto de longo prazo", "adversarial"),
    ]

    case_id = 1
    for seg, arm_exp, justif, tipo in case_templates:
        subset = merged[merged['client_segment'] == seg]
        if len(subset) == 0:
            continue
        sample = subset.sample(n=1, random_state=SEED + case_id).iloc[0]

        cases.append({
            'case_id':         f'GS_{case_id:03d}',
            'type':            tipo,
            'segment':         seg,
            'context':         sample['context'],
            'arm_expected':    arm_exp,
            'reward_expected': int(ARM_TRUE_RATES.get(arm_exp, 0.1) > 0.12),
            'justification':   justif,
            'pass_criteria':   f'arm_chosen == "{arm_exp}" OU conversion_rate > 0.12',
            'fail_criteria':   f'arm_chosen em braços com afinidade zero para {seg}'
        })
        case_id += 1

    # Complementa com cases aleatórios para chegar em n_cases
    while len(cases) < n_cases and len(merged) > 0:
        sample = merged.sample(n=1, random_state=SEED + case_id).iloc[0]
        cases.append({
            'case_id':         f'GS_{case_id:03d}',
            'type':            'random',
            'segment':         sample['client_segment'],
            'context':         sample['context'],
            'arm_expected':    sample['client_segment'],
            'reward_expected': int(sample['reward']),
            'justification':   'Caso gerado automaticamente do histórico de eventos',
            'pass_criteria':   'reward >= reward_expected',
            'fail_criteria':   'reward = 0 E arm_expected tem alta taxa histórica'
        })
        case_id += 1

    return cases

# ============================== Runner ==============================

def run(df: pd.DataFrame) -> dict:
    print('=== ENRIQUECIMENTO SINTÉTICO ===')

    # Catálogo de ofertas
    catalog = generate_offer_catalog()
    catalog_path = DATA_SYNTH / "offer_catalog.json"
    with open(catalog_path, 'w') as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
    print(f'offer_catalog salvo: {catalog_path}  ({len(catalog)} braços)')

    # Eventos de impressão
    events_df = generate_offer_events(df, n_events=3000)
    events_path = DATA_SYNTH / "offer_events.jsonl"
    events_df.to_json(events_path, orient='records', lines=True, force_ascii=False)
    print(f'offer_events salvo: {events_path}  ({len(events_df):,} eventos)')

    # Distribuição por segmento
    print(events_df['client_segment'].value_counts().to_string())

    # Recompensas atrasadas
    rewards_df = generate_delayed_rewards(events_df, df)
    rewards_path = DATA_SYNTH / "delayed_rewards.jsonl"
    rewards_df.to_json(rewards_path, orient='records', lines=True, force_ascii=False)
    conv_rate = rewards_df['reward'].mean()
    mean_delay = rewards_df[rewards_df['reward'] == 1]['delay_days'].mean()
    print(f'delayed_rewards salvo: {rewards_path}  (conv={conv_rate:.2%}), delay_medio={mean_delay:.1f} dias)')

    # Conversão por braço
    events_rewards = events_df.merge(rewards_df, on='event_id')
    print('\nConversão por braço:')
    print(events_rewards.groupby('arm_chosen')['reward'].mean().round(3).to_string())

    # Golden set
    golden = generate_golden_set(df, events_df, rewards_df, n_cases=30)
    golden_path = DATA_GOLDEN / "evaluation_cases.jsonl"
    with open(golden_path, 'w') as f:
        for case in golden:
            f.write(json.dumps(case, ensure_ascii=False) + '\n')
    print(f'\nGolden set salvo: {golden_path}  ({len(golden)} casos)')
    print(pd.Series([c['type'] for c in golden]).value_counts().to_string())

    return {
        'events_df':    events_df,
        'rewards_df':   rewards_df,
        'catalog':      catalog,
        'golden':       golden,
    }

if __name__ == "__main__":
    from kaggle import run as run_step1
    df = run_step1()
    run(df)