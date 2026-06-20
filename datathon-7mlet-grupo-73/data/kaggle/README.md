Base escolhida: https://www.kaggle.com/datasets/aguado/telemarketing-jyb-dataset


### Dados do Cliente
|Coluna|Tipo|Descrição|
|------|----|---------|
|`age`|Numérico|Idade do cliente
|`job`|Categórico|Tipo de trabalho (admin, blue-collar, management, etc.)
|`marital`|Categórico|Estado civil (married, divorced, single)
|`education`|Categórico|Escolaridade (primary, secondary, tertiary, unknown)
|`default`|Binário|Possui crédito em default? (yes/no)
|`balance`|Numérico|Saldo médio anual em euros
|`housing`|Binário|Possui empréstimo habitacional? (yes/no)
|`loan`|Binário|Possui empréstimo pessoal? (yes/no)

- Crédito em default (ou inadimplência) é o não cumprimento das obrigações de um empréstimo. Ocorre quando o devedor (pessoa, empresa ou governo) deixa de pagar parcelas ou juros no prazo acordado. Isso gera restrição de crédito, aumento da dívida por juros e afeta a credibilidade no mercado.

### Dados do Contato
|Coluna|Tipo|Descrição|
|------|----|---------|
|`contact`|Categórico|Tipo de contato (telephone, cellular, unknown)
|`day`|Numérico|Dia do mês do último contato
|`month`|Categórico|Mês do último contato
|`duration`|Numérico|Duração da última chamada em segundos — **DESCARTAR**

- A duração da chamada só é conhecida após o contato terminar — ou seja, no momento da decisão de qual oferta fazer, essa informação não existe ainda. Usar ela inflacionaria artificialmente qualquer métrica de conversão.

### Dados da Campanha
|Coluna|Tipo|Descrição|
|------|----|---------|
|`campaign`|Numérico|Número de contatos nesta campanha
|`pdays`|Numérico|Dias desde último contato de campanha anterior (-1 = nunca)
|`previous`|Numérico|Contatos realizados antes desta campanha
|`poutcome`|Categórico|Resultado da campanha anterior (success, failure, unknown)

### Dados da Sociais e Econômicos

- Indicadores macroeconômicos externos — ou seja, não são dados do cliente nem da campanha, mas sim do contexto econômico do momento em que o contato foi feito.

|Coluna|Tipo|Descrição|
|------|----|---------|
|`emp.var.rate`|Numérico|Taxa de variação de emprego (trimestral). Valor positivo → economia gerando empregos. Valor negativo → economia perdendo empregos

- **Relevância para o bandit**: em períodos de queda do emprego, ofertas de depósito a prazo (segurança) tendem a ser mais atraentes

|Coluna|Tipo|Descrição|
|------|----|---------|
|`cons.price.idx`|Numérico|Mede a inflação (mensal) — o quanto os preços de uma cesta de produtos variou. CPI alto → inflação alta → poder de compra cai. CPI baixo/estável → ambiente de maior previsibilidade financeira

- **Relevância para o bandit**: inflação alta pode tanto incentivar quanto desincentivar investimentos dependendo do perfil do cliente

|Coluna|Tipo|Descrição|
|------|----|---------|
|`cons.conf.idx`|Numérico|Mede o otimismo dos consumidores em relação à economia (mensal). Valores menos negativos (ex: -20) → consumidor mais otimista. Valores mais negativos (ex: -50) → consumidor pessimista, inseguro

- **Relevância para o bandit**: é um dos melhores sinais de momento econômico para decidir qual oferta apresentar — em momentos de baixa confiança, mensagens de segurança e proteção convertem melhor

|Coluna|Tipo|Descrição|
|------|----|---------|
|`euribor3m`|Numérico|É a taxa de juros interbancária europeia para empréstimos de 3 meses (diário) — funciona como referência para o custo do dinheiro na Europa. Euribor alto → crédito mais caro → clientes com empréstimos pagam mais → menos propensão a novos produtos. Euribor baixo → crédito barato → depósitos a prazo rendem menos → menor atratividade do produto

- **Relevância para o bandit**: provavelmente a variável macroeconômica mais preditiva do dataset — a taxa de juros afeta diretamente a atratividade de um depósito a prazo

|Coluna|Tipo|Descrição|
|------|----|---------|
|`nr.employed`|Numérico|Total de pessoas empregadas na economia (em milhares) (trimestral). Número alto → mercado de trabalho aquecido → mais renda disponível. Número baixo → recessão ou contração → clientes mais conservadores

- **Relevância para o bandit**: contexto de mercado de trabalho influencia a receptividade a produtos financeiros de longo prazo

### Target
|Coluna|Tipo|Descrição|
|------|----|---------|
|`y`|Binário|Cliente assinou depósito a prazo (investimento no banco)? (yes/no)