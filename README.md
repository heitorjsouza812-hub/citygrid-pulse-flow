# CityGrid Brain — protótipo experimental de rede elétrica simulada

> Prova de conceito para uma feira de ciências de curso técnico em IA. O sistema usa dados integralmente sintéticos, simulação acelerada e modelos experimentais de apoio à decisão. Não controla uma rede real e não executa ações automaticamente.

## O que o projeto demonstra

- Simulação de telemetria elétrica de oito zonas urbanas.
- Dashboard React conectado ao backend por REST e WebSocket, sem dados mockados.
- Regras técnicas que geram recomendações para revisão humana.
- XGBoost para estimar a classe de risco 30 minutos simulados à frente.
- LSTM por zona para prever seis pontos de consumo, equivalentes a 30 minutos simulados.
- Logs de recomendações para auditoria.
- Integração opcional com Kafka, InfluxDB e Grafana.

## Fluxo canônico da feira

O modo recomendado para a apresentação não depende de Docker nem de internet:

```text
simulador_iot.py
    ↓ dados_citygrid.jsonl
motor_decisao.py --modo=arquivo
    ↓ logs/decisoes.jsonl
backend.py (FastAPI REST + WebSocket)
    ↓
frontend React/Vite
```

O relógio é acelerado: cada ciclo demora cinco segundos reais, mas avança cinco minutos no tempo simulado.

## Instalação

Requisitos:

- Python 3.12 recomendado.
- Node.js e npm.
- Docker apenas para a integração opcional.

No Windows:

```bash
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt
npm install
```

Os pins de `scikit-learn` e `kafka-python` preservam a compatibilidade dos artefatos treinados e dos clientes Kafka usados pelo projeto.

## Executar a demonstração local

Verifique os pré-requisitos:

```bash
.venv\Scripts\python iniciar.py --check
```

Inicie o fluxo completo:

```bash
.venv\Scripts\python iniciar.py
```

Para não abrir o navegador automaticamente:

```bash
.venv\Scripts\python iniciar.py --sem-navegador
```

URLs:

| Componente          | URL                          |
| ------------------- | ---------------------------- |
| Dashboard React     | `http://127.0.0.1:5173`      |
| API FastAPI         | `http://127.0.0.1:8000`      |
| Documentação da API | `http://127.0.0.1:8000/docs` |
| WebSocket           | `ws://127.0.0.1:8000/ws`     |

Pressione `Ctrl+C` no launcher para encerrar todos os componentes iniciados por ele.

## Pergunta e protocolo experimental

Pergunta de pesquisa:

> Em uma rede urbana sintética, os modelos aprendidos conseguem prever consumo e risco 30 minutos à frente melhor que baselines ingênuos?

Hipóteses mensuráveis:

1. A LSTM deve reduzir o MAE em relação à persistência do último consumo observado.
2. O XGBoost deve superar a persistência do risco atual em F1 macro.

Protocolo registrado em `graficos/metricas_experimento.json`:

- Base: `dados_turbo.csv`, com 100.000 linhas sintéticas.
- Seed: `42`.
- Hash SHA-256 da base: `e94426f69498789305fb11ca0c2add742f0c22119e02fb6ccfc0f13d3cc54726`.
- Intervalo simulado: cinco minutos por ciclo.
- Horizonte: seis ciclos, ou 30 minutos simulados.
- Split sincronizado por ciclo: 70% treino, 15% validação e 15% teste.
- Todas as zonas de um ciclo permanecem no mesmo conjunto.
- Embargo de seis ciclos nas duas fronteiras para evitar vazamento do alvo futuro.
- O teste não é usado para ajuste ou early stopping.
- Baselines: classe majoritária e persistência.

Para regenerar os modelos e gráficos:

```bash
.venv\Scripts\python treinamento_ml.py
```

## Resultados atuais

### XGBoost — classificação de risco futuro

Resultados no teste temporal:

| Métrica             | Resultado |
| ------------------- | --------: |
| Acurácia            |     0,606 |
| Acurácia balanceada |     0,370 |
| F1 macro            |     0,298 |
| Recall de `CRÍTICO` |     0,142 |

Comparação:

- Supera a classe majoritária em F1 macro: `0,298` contra `0,226`.
- Não supera a persistência em F1 macro: `0,298` contra `0,304`.
- A acurácia simples também fica abaixo da classe majoritária por causa do desbalanceamento.

Conclusão honesta: o XGBoost ainda é fraco para as classes de risco e não deve ser apresentado como modelo confiável ou validado para operação.

### LSTM — previsão de consumo

As oito LSTMs superaram o baseline de persistência em MAE nesta única base sintética.

- Melhor MAE: Zona Universitária, `0,572 MW`.
- Pior MAE: Zona Oeste, `5,820 MW`.

Conclusão honesta: a previsão de consumo é a parte mais defensável do experimento, mas o resultado ainda não demonstra generalização para outra geração sintética, outra cidade ou uma rede real.

### Sistema híbrido

Nenhum estudo de ablação conjunto foi executado. O projeto não publica uma métrica híbrida estimada e não afirma que a combinação dos componentes supera os modelos isolados.

## Significado das saídas

- `risco`: estado sintético atual produzido pelo simulador.
- `risco_xgb`: previsão experimental para 30 minutos simulados à frente.
- `risco_lstm`: risco derivado da previsão de consumo da LSTM.
- `confianca` do XGBoost: maior probabilidade bruta produzida pelo modelo; não é garantia de acerto nem confiança calibrada.
- Regras e algoritmo genético geram recomendações ou cenários hipotéticos; não acionam equipamentos.
- `energia_renovavel_intervalo_mwh` mede geração renovável no intervalo simulado. Não mede economia causada pela IA.

## Integração opcional Kafka/InfluxDB/Grafana

Esta integração é experimental e separada do fluxo canônico do dashboard. Ela demonstra streaming e observabilidade, mas o React/FastAPI continua lendo o JSONL local.

1. Copie `.env.example` para `.env` e substitua todas as credenciais de exemplo.
2. Valide e suba a infraestrutura:

```bash
docker compose config
docker compose up -d
```

3. Em terminais separados, execute:

```bash
.venv\Scripts\python producer.py
.venv\Scripts\python consumer.py
.venv\Scripts\python motor_decisao.py
```

Serviços opcionais:

| Serviço       | URL/porta               |
| ------------- | ----------------------- |
| Kafka no host | `localhost:9092`        |
| InfluxDB      | `http://localhost:8086` |
| Grafana       | `http://localhost:3000` |

As credenciais não ficam no código e as portas são vinculadas a `127.0.0.1`. O Kafka ainda usa `PLAINTEXT`; portanto, esse Compose é adequado apenas para demonstração local, não para produção.

## Verificação

```bash
.venv\Scripts\python -m pytest -q
.venv\Scripts\python -m compileall -q .
npm test
npm run typecheck
npm run lint
npm run build
.venv\Scripts\python iniciar.py --check
```

## Estrutura principal

```text
backend.py                     API FastAPI e WebSocket
simulador_iot.py               simulador em tempo real acelerado
motor_decisao.py               recomendações em modo JSONL ou Kafka
producer.py                    simulador → Kafka, integração opcional
consumer.py                    Kafka → InfluxDB, integração opcional
treinamento_ml.py              treinamento e geração dos artefatos
ml_core.py                     split, baselines e métricas reutilizáveis
iniciar.py                     launcher canônico da demonstração
src/                           dashboard React conectado à API
tests/                         testes Python
modelos/                       modelos e scalers treinados
graficos/metricas_experimento.json
                               protocolo, ambiente e métricas reproduzíveis
grafana/provisioning/          dashboards da integração opcional
docker-compose.yml             infraestrutura opcional
```

As interfaces antigas `front-end/dashboard.html` e `dashboard_cientifico.py`, os gráficos contraditórios e o modelo LSTM genérico sem proveniência foram removidos.

## Limitações e ameaças à validade

- Todos os dados são sintéticos.
- Há somente uma geração principal da base; não há validação entre várias sementes ou cidades.
- O simulador usa regras próprias que também influenciam os padrões aprendidos.
- O XGBoost não supera o baseline de persistência em F1 macro.
- O score do XGBoost não foi calibrado como probabilidade confiável.
- Não há atuadores, SCADA, medidores reais nem validação de fluxo de potência.
- O algoritmo genético calcula apenas uma distribuição hipotética; não garante viabilidade elétrica.
- Não foi medido um cenário contrafactual “com IA versus sem IA”; portanto, não há alegação de economia causada pela IA.
- A integração Docker precisa ser executada em um host com Docker antes de ser usada na apresentação.

## Uso responsável na feira

Apresente o CityGrid Brain como:

> “Prova de conceito de um sistema de apoio à decisão para uma rede urbana simulada, com dados sintéticos e simulação acelerada.”

Não o apresente como produto operacional, sistema autônomo, solução validada pela ANEEL ou prova de economia real de energia.
