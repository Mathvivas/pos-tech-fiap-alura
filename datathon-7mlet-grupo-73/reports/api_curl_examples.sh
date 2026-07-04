
# ═════ EXEMPLOS DE USO DA API (salve em docs/api-examples.sh) ══════════════

# 1. Healthcheck
curl http://localhost:8000/health
 
# 2. Listar braços disponíveis
curl http://localhost:8000/arms
 
# 3. Pedir uma decisão
curl -X POST http://localhost:8000/decide \
  -H "Content-Type: application/json" \
  -d '{
  "client_features": {
    "age": 42.0,
    "campaign": 1.0,
    "pdays_clean": 0.0,
    "previous": 0.0,
    "contacted_before": 1.0,
    "job": 0.0,
    "marital": 0.0,
    "education": 0.0,
    "default": 0.0,
    "housing": 0.0,
    "loan": 0.0,
    "contact": 0.0,
    "month": 0.0,
    "poutcome": 3.0,
    "emp.var.rate": 0.0,
    "cons.price.idx": 0.0,
    "cons.conf.idx": 0.0,
    "euribor3m": 0.0,
    "nr.employed": 0.0
  }
}'
 
# 4. Registrar recompensa (use o event_id retornado acima)
curl -X POST http://localhost:8000/reward \
  -H "Content-Type: application/json" \
  -d '{"event_id": "<EVENT_ID>", "arm": "dep_6m_8pct", "reward": 1}'
 
# 5. Interface Swagger (abra no navegador)
# http://localhost:8000/docs
