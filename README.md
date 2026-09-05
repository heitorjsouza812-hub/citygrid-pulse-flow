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

## POC de LLM pequeno

O diretório [`llm_decision/`](llm_decision/README.md) contém um POC reprodutível de um **Ministral 3B ajustado com QLoRA**. Ele converte telemetria sintética em JSON de apoio à decisão, sem substituir as heurísticas determinísticas, LSTM, XGBoost ou revisão humana. Inclui dataset sintético de 3.000 amostras, notebooks Kaggle/Colab, validação de artefatos, benchmark local com Ollama e modelo de publicação de adapter/GGUF.

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

O XGBoost aumenta a cobertura de classes como `CRÍTICO` e `MÉDIO`, mas ainda não cumpriu o critério principal de adoção em F1 macro. Por isso, o projeto aplica uma decisão de engenharia explícita: o modelo é exibido como sinal analítico. O gate exige ganho em F1 macro e ausência de regressão no recall de `CRÍTICO`, sendo reavaliado a partir das métricas reproduzíveis quando um novo modelo é treinado.

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

## Central de Decisão da Plateia

A Central de Decisão da Plateia transforma a demonstração em uma experiência coletiva para apresentações, feiras e salas de aula. Ela não substitui o dashboard: o modo operacional, mapa, timeline, cenários manuais, histórico e recomendações existentes continuam disponíveis.

- Apresentador: abra `/apresentador`, crie uma sala e projete o QR Code.
- Participante: leia o QR Code (ou abra `/participar/CG-0000`), informe um apelido opcional e vote sem conta.
- O apresentador é o único ator que cria sala, inicia eventos, abre/fecha/revela votos, aplica projeções, decide empates e encerra a apresentação.
- Cada sala tem código público curto e token privado de apresentador. O token fica apenas no `sessionStorage` do navegador do apresentador e nunca é colocado no QR/link/estado público.

### Fluxo de três rodadas

1. Crie a sala; o lobby mostra QR, link, código e presença conectada.
2. Escolha um evento já existente: tempestade severa, incêndio urbano ou pico de consumo.
3. Abra a votação de zona e depois a votação de ação. Cada participante tem um voto por etapa e pode alterá-lo enquanto o servidor mantém a votação aberta.
4. Feche, resolva qualquer empate explicitamente, revele **Plateia × Recomendação do sistema** e aplique a projeção educacional.
5. Após três rodadas, encerre para obter o resumo final, total de votos, participantes, comparações com a recomendação e melhor/rodada de maior atenção.

O padrão é **resultado oculto** durante a votação. O apresentador pode ativar resultado ao vivo e escolher 10, 15, 20, 30 segundos ou sem limite. O prazo é decidido pelo backend, não pelo relógio do celular.

### Arquitetura e regras da sala

```text
/apresentador e /participar/$codigo
  ├─ REST /api/salas/* (ações administrativas exigem X-Presenter-Token)
  └─ WS /ws/salas/{codigo} (estado e presença em tempo real)
       └─ RoomManager em memória → regras, votos, cronômetro e projeções
```

O backend é a única fonte de verdade. As mensagens WS são tipadas (`sala_atualizada`, `participante_entrou`, `rodada_iniciada`, `votacao_aberta`, `voto_registrado`, `contagem_atualizada`, `votacao_encerrada`, `resultado_revelado`, `consequencia_aplicada`, `apresentacao_encerrada` e `erro`). Desconectar e reconectar não remove o voto: o cliente usa um identificador anônimo persistido por sala no `localStorage`.

O placar começa em estabilidade 75, reserva 70, controle de custos 70 e satisfação 75. Cada ação tem deltas específicos por evento no único mapa de regras `audience_rooms.py`; todos os valores são limitados a 0–100. A pontuação geral é `0,40×estabilidade + 0,25×reserva + 0,15×controle_custos + 0,20×satisfação`. As consequências são projeções guardadas somente na sala, identificadas visualmente como **PROJEÇÃO DE CENÁRIO**; elas nunca escrevem JSONL, histórico ou modelos.

A recomendação compara heurísticas explicáveis, prioridade do cenário e contexto LSTM. O XGBoost permanece sinal analítico enquanto seu gate permanece fechado; seu score bruto não é probabilidade calibrada. O POC Ministral é experimental e não é consultado ao vivo por essa funcionalidade.

### Uso em Wi-Fi e publicação

1. Copie `.env.example` para `.env` e defina `CITYGRID_PUBLIC_APP_URL` como um endereço realmente alcançável pelos celulares, por exemplo `http://192.168.1.25:5173` na mesma rede.
2. Para escutar na LAN, use `CITYGRID_HOST=0.0.0.0` e `CITYGRID_FRONTEND_HOST=0.0.0.0`; adicione explicitamente `http://IP-DO-PC:5173` a `CITYGRID_CORS_ORIGINS`.
3. Inicie `python iniciar.py --sem-navegador` e abra `/apresentador` no computador. Em ambiente publicado, use URLs HTTPS/WSS, preencha `VITE_CITYGRID_API_URL` e `VITE_CITYGRID_WS_URL` se API e frontend forem domínios distintos, e mantenha uma lista exata de origens CORS.

Nunca use `*` em CORS de produção. O QR é produzido com `CITYGRID_PUBLIC_APP_URL` no backend; configure-o antes de criar uma sala.

### Limitações e solução de problemas

- Salas são em memória e expiram após `CITYGRID_ROOM_TTL_MINUTES` de inatividade. Execute FastAPI com **um único worker**. Para múltiplos workers/replicas, implemente uma store Redis compartilhada e um pub/sub de WebSocket.
- Backend indisponível, sala ausente/encerrada, votação fora da fase/prazo e token de apresentador inválido devolvem mensagens de erro explícitas. O cliente tenta reconexão com backoff.
- Se um celular não abrir o QR, confirme o mesmo Wi-Fi, firewall/porta, URL pública correta e CORS com a origem exata. `127.0.0.1` no celular aponta para o próprio celular, nunca para o computador.
- Se ninguém votar, não há escolha automática. Se houver empate, o apresentador deve escolher uma das opções empatadas.

Todos os dados são sintéticos; esta é uma simulação educacional. Nenhuma ação é enviada a rede elétrica real, nenhuma decisão é certa com certeza e recomendações requerem avaliação humana.
