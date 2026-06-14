# CityGrid Brain 🧠⚡

> Sistema inteligente de monitoramento e gerenciamento de energia urbana para Smart Cities.
> Motor de decisão híbrido com IA explicável (XAI), pipeline em tempo real e validação científica.

---

## Arquitetura

```
Simulador IoT → Kafka → Consumer → InfluxDB → Grafana
                  ↓
           Motor de Decisão (4 camadas):
             1. Heurísticas ANEEL/PRODIST
             2. XGBoost (risco futuro t+30min)
             3. LSTM (previsão de consumo)
             4. Algoritmo Genético (otimização)
                  ↓
           Backend FastAPI → Dashboard Web (WS)
```

---

## Instalação

```bash
# 1. Clone e instale dependências
pip install -r requirements.txt

# 2. Suba a infraestrutura (Kafka + InfluxDB + Grafana)
docker-compose up -d

# 3. Treine os modelos (necessário na 1ª vez)
python treinamento_ml.py

# 4. Em terminais separados:
python simulador_iot.py    # terminal 1 — gera dados
python consumer.py          # terminal 2 — persiste no InfluxDB
python motor_decisao.py     # terminal 3 — decisões IA
python backend.py           # terminal 4 — API REST + WebSocket

# 5. Abra o dashboard
start front-end/dashboard.html
```

---

## Interfaces

| Interface | URL | Descrição |
|---|---|---|
| Dashboard Web | `front-end/dashboard.html` | Monitor em tempo real |
| Backend API | `http://localhost:8000` | REST + WebSocket |
| Grafana | `http://localhost:3000` | Séries temporais |
| InfluxDB | `http://localhost:8086` | Banco de dados |

---

## Motor de Decisão — 4 Camadas

### Camada 1: Heurísticas (prioridade máxima)
Regras baseadas em normas técnicas ANEEL PRODIST Módulo 8:
- **R0** — Zona crítica (hospital/UPA): **NUNCA** cortar carga — proteção à vida humana
- **R1** — Sobrecarga ≥ 95%: corte imediato de carga não essencial
- **R2** — Frequência fora de 59,5–60,5 Hz: alerta de desequilíbrio
- **R3** — THD > 8%: alerta de qualidade de energia
- **R4** — FP < 0,92: alerta de fator de potência
- **R5** — Consumo zero: detecção de microfalta

### Camada 2: XGBoost
- **Tarefa**: classifica risco **futuro** (t+30min) — BAIXO / MÉDIO / ALTO / CRÍTICO
- **Anti-data-leakage**: label deslocado HORIZONTE_LSTM ciclos à frente
- **Split temporal**: treino nos primeiros 80% do tempo, teste nos últimos 20%
- **XAI**: SHAP values exportados em `graficos/shap_xgboost.png`

### Camada 3: LSTM
- **Tarefa**: prevê consumo MW nos próximos 30 minutos (6 passos × 5s)
- **Modelos por zona**: 8 LSTMs especializados (janela de 24 ciclos)
- **Split correto**: StandardScaler fitado apenas no conjunto de treino

### Camada 4: Algoritmo Genético
- **Tarefa**: redistribuição ótima de carga entre todas as zonas
- **Critério**: minimizar sobrecarga nas zonas de alto risco

---

## Referências Científicas

- ANEEL. **PRODIST Módulo 8** — Qualidade da Energia Elétrica. 2023.
- ONS. **Atlas de Energia Elétrica do Brasil**. 2022.
- INMET. **Normais Climatológicas do Brasil 1991–2020**. 2022.
- Hochreiter & Schmidhuber. **Long Short-Term Memory**. Neural Computation, 1997.
- Chen & Guestrin. **XGBoost: A Scalable Tree Boosting System**. KDD 2016.
- Lundberg & Lee. **A Unified Approach to Interpreting Model Predictions**. NIPS 2017.

---

## Embasamento Normativo

| Parâmetro | Referência | Valor |
|---|---|---|
| Frequência (limite precário) | ANEEL PRODIST M8 | 59,5 – 60,5 Hz |
| THD de tensão (limite) | ANEEL PRODIST M8, §3.6 | 8% |
| Fator de potência mínimo | Res. ANEEL 456/2000 | 0,92 |
| Tensão nominal BT | NBR 5410 | 220/127 V |
| Índices de continuidade | ANEEL (DEC/FEC) | por zona |

---

## Estrutura de Arquivos

```
Smartcity/
├── simulador_iot.py       # Gerador de dados sintéticos
├── consumer.py            # Consumer Kafka → InfluxDB
├── motor_decisao.py       # Motor de decisão IA híbrido
├── treinamento_ml.py      # Pipeline de treinamento ML
├── backend.py             # API FastAPI + WebSocket
├── docker-compose.yml     # Infraestrutura (Kafka/InfluxDB/Grafana)
├── requirements.txt       # Dependências Python
├── modelos/               # Modelos treinados (.pt, .json, .pkl)
├── graficos/              # Gráficos de métricas e SHAP
├── logs/decisoes.jsonl    # Log de auditoria das decisões
├── dados_citygrid.jsonl   # Leituras do simulador
├── grafana/provisioning/  # Configuração automática Grafana
└── front-end/
    └── dashboard.html     # Dashboard web em tempo real
```

---

## Limitações e Trabalhos Futuros

- **Dados sintéticos**: o simulador é calibrado com normas reais (ANEEL, ONS, INMET), mas não substitui dados coletados de redes reais.
- **Escala**: testado com 8 zonas; a arquitetura suporta expansão horizontal via Kafka.
- **Modelos**: retreinamento periódico recomendado à medida que novos dados acumulam.
- **Trabalhos futuros**: integração com SCADA real, federated learning entre cidades, previsão de demanda com dados meteorológicos em tempo real (API INMET).
