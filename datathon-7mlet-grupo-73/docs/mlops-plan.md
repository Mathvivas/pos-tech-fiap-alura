# Plano MLOps — Ciclo de Vida de Políticas

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
