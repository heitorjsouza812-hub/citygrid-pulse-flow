# CityGrid Brain — IA aplicada à gestão de uma rede urbana simulada

[![CI](https://github.com/heitorjsouza812-hub/citygrid-pulse-flow/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/heitorjsouza812-hub/citygrid-pulse-flow/actions/workflows/ci.yml)
![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Node.js 22](https://img.shields.io/badge/Node.js-22-339933?logo=nodedotjs&logoColor=white)
![Dados sintéticos](https://img.shields.io/badge/dados-sint%C3%A9ticos-6C63FF)

O CityGrid Brain é uma plataforma demonstrativa de apoio à decisão para redes elétricas urbanas simuladas. O projeto integra telemetria de oito zonas, previsão de consumo, classificação de risco, recomendações explicáveis e um dashboard web em um fluxo reproduzível, executável localmente e preparado para apresentação em feira científica.

## Destaques verificáveis

- **Aplicação ponta a ponta:** simulador Python, motor de decisão, API FastAPI, WebSocket e dashboard React.
- **Dados reais da execução:** o frontend consome a API e o histórico gerado pelo simulador, sem preencher gráficos com mocks.
- **Previsão multihorizonte:** oito modelos LSTM estimam seis leituras futuras, equivalentes a 30 minutos simulados.
- **Resultado comparativo positivo:** as LSTMs superaram a persistência nas oito zonas, com redução agregada de **22,85% no MAE**.
- **Avaliação temporal protegida:** split 70/15/15 sincronizado entre zonas, embargo de seis ciclos e conjunto de teste reservado.
- **Governança de modelos:** uma previsão só pode gerar recomendação quando supera o baseline em F1 macro sem reduzir o recall de `CRÍTICO`. O XGBoost permanece visível para análise, mas seu gate fica fechado enquanto os dois critérios não são atingidos.
- **Reprodutibilidade:** seed, versões, hash SHA-256 da base, métricas por classe e artefatos do experimento são registrados.
- **Operação segura para demonstração:** as saídas são recomendações para revisão humana; o sistema não envia comandos a equipamentos.
- **Qualidade contínua:** o GitHub Actions executa testes Python, testes frontend, typecheck, lint e build em cada PR e na branch `main`.

## Arquitetura da demonstração

O fluxo principal funciona sem Docker e sem internet:

```text
simulador_iot.py
    ↓ telemetria JSONL
motor_decisao.py --modo=arquivo
    ↓ recomendações auditáveis
backend.py (FastAPI REST + WebSocket)
    ↓
frontend React/Vite
```

Cada ciclo dura cinco segundos reais e avança cinco minutos no relógio simulado. Assim, uma previsão de seis ciclos representa um horizonte de 30 minutos simulados.

## Início rápido no Windows

Requisitos:

- Python 3.12;
- Node.js 22 e npm;
- Docker somente para a integração opcional com Kafka, InfluxDB e Grafana.

Instale as dependências:

```bash
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt
npm ci
```

Valide o ambiente:

```bash
.venv\Scripts\python iniciar.py --check
```

Inicie a demonstração completa:

```bash
.venv\Scripts\python iniciar.py
```

Para iniciar sem abrir o navegador:

```bash
.venv\Scripts\python iniciar.py --sem-navegador
```

| Componente | Endereço |
| --- | --- |
| Dashboard React | `http://127.0.0.1:5173` |
| API FastAPI | `http://127.0.0.1:8000` |
| Swagger da API | `http://127.0.0.1:8000/docs` |
| WebSocket | `ws://127.0.0.1:8000/ws` |

Use `Ctrl+C` no launcher para encerrar os componentes iniciados por ele.

## Pergunta de pesquisa

> Em uma rede urbana sintética, modelos de aprendizado de máquina conseguem prever consumo e risco 30 minutos à frente melhor que baselines simples?

Hipóteses mensuráveis:

1. A LSTM deve reduzir o MAE em relação à persistência do último consumo observado.
2. O classificador de risco deve superar a persistência em F1 macro sem reduzir o recall de `CRÍTICO` antes de participar das recomendações.

## Protocolo experimental

O protocolo completo está em `graficos/metricas_experimento.json`.

- Base: `dados_turbo.csv`, com 100.000 linhas sintéticas.
- Seed: `42`.
- SHA-256 da base: `e94426f69498789305fb11ca0c2add742f0c22119e02fb6ccfc0f13d3cc54726`.
- Intervalo: cinco minutos simulados por ciclo.
- Horizonte: seis ciclos, equivalentes a 30 minutos simulados.
- Divisão por tempo: 70% treino, 15% validação e 15% teste.
- Sincronização: todas as zonas de um mesmo ciclo permanecem no mesmo conjunto.
- Embargo: seis ciclos nas fronteiras para proteger o alvo futuro.
- Seleção: o teste não participa de early stopping, pesos de classe ou ajuste de hiperparâmetros.
- Baselines: classe majoritária e persistência.

Para reproduzir os modelos, métricas e gráficos:

```bash
.venv\Scripts\python treinamento_ml.py
```

## Evidências do experimento

### LSTM — previsão de consumo

| Evidência no teste temporal | Resultado |
| --- | ---: |
| Zonas em que a LSTM superou a persistência | **8 de 8** |
| MAE médio das LSTMs | **2,181 MW** |
| MAE médio da persistência | **2,826 MW** |
| Redução agregada do MAE | **22,85%** |
| Melhor MAE por zona | **0,572 MW** |

O resultado sustenta o uso da LSTM como componente preditivo da demonstração no cenário sintético registrado.

### XGBoost — classificação de risco

| Métrica no teste temporal | XGBoost | Baseline relevante |
| --- | ---: | ---: |
| F1 macro | 0,298 | 0,304 (persistência) |
| Acurácia balanceada | 0,370 | 0,304 (persistência) |
| Recall de `CRÍTICO` | 0,142 | 0,070 (persistência) |

O XGBoost aumenta a cobertura de classes como `CRÍTICO` e `MÉDIO`, mas ainda não cumpriu o critério principal de adoção em F1 macro. Por isso, o projeto aplica uma decisão de engenharia explícita: o modelo é exibido como sinal analítico e **não gera recomendações**. O gate exige ganho em F1 macro e ausência de regressão no recall de `CRÍTICO`, sendo reavaliado a partir das métricas reproduzíveis quando um novo modelo é treinado.

Essa separação entre “modelo disponível” e “modelo aprovado para decisão” é parte da confiabilidade do CityGrid Brain.

## Como interpretar as saídas

- `risco`: estado atual produzido pelo simulador.
- `risco_xgb`: estimativa analítica para 30 minutos simulados à frente.
- `risco_lstm`: risco derivado da previsão de consumo da LSTM.
- `conf_xgb`: maior score bruto do classificador; não é apresentado como probabilidade calibrada.
- Heurísticas: recomendações explicáveis baseadas em limiares definidos.
- Algoritmo genético: cenário hipotético de redistribuição para análise.
- `energia_renovavel_intervalo_mwh`: geração renovável observada no intervalo simulado.

## Integração opcional de streaming

Kafka, InfluxDB e Grafana formam uma trilha opcional de streaming e observabilidade. O dashboard principal continua independente dessa infraestrutura.

1. Copie `.env.example` para `.env` e substitua as credenciais de exemplo.
2. Valide e inicie a infraestrutura:

```bash
docker compose config
docker compose up -d
```

3. Execute os clientes em terminais separados:

```bash
.venv\Scripts\python producer.py
.venv\Scripts\python consumer.py
.venv\Scripts\python motor_decisao.py
```

| Serviço | Endereço |
| --- | --- |
| Kafka no host | `localhost:9092` |
| InfluxDB | `http://localhost:8086` |
| Grafana | `http://localhost:3000` |

As credenciais são carregadas do `.env`, as portas são vinculadas a `127.0.0.1` e o acesso anônimo do Grafana permanece desativado. O modo Kafka `PLAINTEXT` é destinado à demonstração local.

## Verificação de qualidade

A mesma cadeia usada no CI pode ser executada localmente:

```bash
.venv\Scripts\python -m pytest -q
.venv\Scripts\python -m compileall -q .
npm test
npm run typecheck
npm run lint
npm run build
.venv\Scripts\python iniciar.py --check
```

O workflow está em `.github/workflows/ci.yml` e usa Python 3.12, Node.js 22, instalação reproduzível por `npm ci` e cancelamento de execuções duplicadas.

## Estrutura principal

```text
backend.py                     API FastAPI e WebSocket
simulador_iot.py               telemetria urbana simulada
motor_decisao.py               recomendações e inferência em arquivo ou Kafka
producer.py                    simulador → Kafka
consumer.py                    Kafka → InfluxDB
ml_core.py                     split temporal, baselines e métricas
treinamento_ml.py              treinamento e geração de artefatos
iniciar.py                     launcher da demonstração
src/                           dashboard React conectado à API
tests/                         testes Python
graficos/metricas_experimento.json
                               protocolo, versões e resultados reproduzíveis
modelos/                       modelos e scalers treinados
grafana/provisioning/          datasource e dashboard opcionais
```

O CityGrid Brain deve ser apresentado como:

> **Uma plataforma de apoio à decisão para uma rede urbana simulada, com previsão de consumo validada contra baseline, governança de modelos e recomendações explicáveis.**
