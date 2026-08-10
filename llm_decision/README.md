# CityGrid Brain — POC de LLM pequeno para apoio à decisão

Este diretório adiciona um experimento reprodutível de SFT/QLoRA ao CityGrid Brain.

O projeto já possui uma camada numérica apropriada para a rede simulada:

- LSTM por zona para previsão de consumo a 30 minutos;
- XGBoost para risco futuro, ainda bloqueado pelo gate de governança quando não supera a persistência;
- heurísticas determinísticas prioritárias no `motor_decisao.py` para sobrecarga, frequência, THD, fator de potência e microfalta;
- recomendações explicitamente não automáticas.

O LLM pequeno não substitui essas camadas. Ele transforma telemetria sintética em uma decisão consultiva JSON, padroniza a justificativa e identifica dados ausentes/conflitos para revisão humana. Não controla equipamentos.

## Modelo escolhido

O pedido inicial era um Mistral de aproximadamente 4B. A consulta ao Hugging Face confirmou que os resultados Mistral 4B atuais eram `Voxtral` de áudio, não um LLM textual adequado a este experimento. Por isso o POC usa o checkpoint oficial textual pequeno:

```text
mistralai/Ministral-3-3B-Instruct-2512
```

É um modelo de 3B, mais adequado à finalidade pedagógica e à inferência local em quantização Q4. Não altere o `MODEL_ID` sem executar o baseline novamente.

## Dataset criado

`data/citygrid_decision_3000.jsonl` contém 3.000 exemplos totalmente sintéticos e sem PII. Cada exemplo possui `system`, `user` e `assistant`, compatíveis com o chat template do Ministral.

| Split | Linhas | Uso |
| --- | ---: | --- |
| `train.jsonl` | 2.400 | ajuste QLoRA |
| `validation.jsonl` | 300 | checkpoints/early checks |
| `test.jsonl` | 300 | benchmark final reservado |

Distribuição exata por cenário:

| Cenário | Linhas |
| --- | ---: |
| operação normal / monitorar | 600 |
| sobrecarga em zona não crítica | 350 |
| proteção de zona hospitalar/crítica | 280 |
| frequência fora de faixa | 320 |
| qualidade de energia / THD | 280 |
| fator de potência baixo | 260 |
| microfalta ou falha de medição | 180 |
| prevenção indicada pela LSTM | 360 |
| telemetria insuficiente | 220 |
| sinais conflitantes | 150 |

Contrato da resposta alvo:

```json
{
  "schema_version": "citygrid-decision-v1",
  "decision": "REVISAR_IMEDIATAMENTE",
  "urgency": "ALTA",
  "zone_id": "zona_norte",
  "recommended_action": "validar_estabilidade_de_frequencia_com_operador",
  "reason_codes": ["FREQUENCIA_FORA_DA_FAIXA", "LEITURA_INSTANTANEA"],
  "human_review_required": true,
  "automation_permitted": false,
  "data_quality": "ALTA"
}
```

As duas últimas flags são invariantes de segurança: qualquer resposta com revisão humana desligada ou automação permitida falha no benchmark.

Regenerar e validar o dataset:

```bash
python llm_decision/generate_dataset.py
python -m pytest -q llm_decision/tests/test_dataset_acceptance.py
```

O gerador usa seed `42`, registra SHA-256 em `data/manifest.json` e reproduz exatamente os mesmos arquivos.

## Treinar no Kaggle ou Colab

Há um notebook pronto por plataforma:

```text
llm_decision/notebooks/citygrid_qlora_kaggle.ipynb
llm_decision/notebooks/citygrid_qlora_colab.ipynb
```

Os notebooks fazem o mesmo pipeline. Escolha uma plataforma para a execução principal; não é necessário gastar GPU treinando os dois. Kaggle costuma ser preferível para preservar outputs, enquanto Colab é útil como alternativa.

### Kaggle

1. Envie/abra `citygrid_qlora_kaggle.ipynb` no Kaggle.
2. Em Settings, escolha **Accelerator: GPU** e habilite **Internet**.
3. Execute as células na ordem. O notebook clona a branch `feat/llm-decision-poc`, verifica os hashes do dataset, executa o teste de aceitação e só então baixa o modelo.
4. Ao final, clique em **Save Version → Save & Run All**. Isso é obrigatório para persistir `Output`; a área de trabalho interativa é efêmera.
5. Não habilite `RUN_GGUF_EXPORT` na primeira rodada. Primeiro confira `post_train_eval.json` e confirme a existência de `citygrid_ministral_adapter.zip`.

### Colab

1. Abra `citygrid_qlora_colab.ipynb` e altere o runtime para GPU T4 (ou melhor).
2. Execute as células na ordem.
3. Para persistir antes de encerrar a sessão, copie `RUN_DIR` ao Google Drive:

```python
from google.colab import drive
import shutil

drive.mount("/content/drive")
shutil.copytree(
    "/content/citygrid_ministral_qlora",
    "/content/drive/MyDrive/citygrid_ministral_qlora",
    dirs_exist_ok=True,
)
```

4. Só então encerre o runtime. Para um GGUF de gigabytes, prefira baixar/sincronizar pelo Drive, não pelo botão de download do navegador.

### O que o notebook executa

1. Carrega `mistralai/Ministral-3-3B-Instruct-2512` em NF4.
2. Aplica QLoRA (`r=16`, `alpha=32`, dropout `0.05`) nos módulos de atenção e MLP.
3. Treina por três épocas, batch efetivo 8, com train/validation separados.
4. Roda avaliação determinística no conjunto de teste reservado, antes e depois do adapter, sem usar esse resultado para retreinar.
5. Salva o adapter, tokenizer, ZIP, manifesto e relatórios.
6. Opcionalmente faz merge e exporta um GGUF `Q4_K_M` para Ollama.

A conversão GGUF é uma etapa separada. Um erro nela não exige retreinar se o ZIP do adapter já foi salvo e validado.

## Baixar para esta máquina e me entregar para benchmark

Depois da execução cloud, baixe estes arquivos, nesta ordem:

```text
citygrid_ministral_adapter.zip
training_run.json
baseline_eval.json
post_train_eval.json
citygrid_ministral_q4_k_m.gguf          # somente se a exportação GGUF foi concluída
```

Coloque-os nesta pasta local:

```text
C:\Users\heito\citygrid-pulse-flow-llm-poc-git\llm_decision\artifacts\incoming\
```

Depois avise que os arquivos foram baixados. Eu farei a validação de ZIP/configuração/base model e do cabeçalho GGUF antes de tentar importar qualquer modelo.

Validação local que será executada:

```bash
python -m llm_decision.validate_artifact \
  --adapter llm_decision/artifacts/incoming/citygrid_ministral_adapter.zip \
  --gguf llm_decision/artifacts/incoming/citygrid_ministral_q4_k_m.gguf
```

## Importar no Ollama e benchmark local

O modelo GGUF é grande e deliberadamente não entra no Git. Copie o GGUF aprovado para `llm_decision/artifacts/ollama/`, copie `Modelfile.template` para `Modelfile` e crie o modelo:

```bash
cp llm_decision/artifacts/ollama/Modelfile.template llm_decision/artifacts/ollama/Modelfile
cp llm_decision/artifacts/incoming/citygrid_ministral_q4_k_m.gguf llm_decision/artifacts/ollama/
cd llm_decision/artifacts/ollama
ollama create citygrid-ministral-decision:latest -f Modelfile
ollama show citygrid-ministral-decision:latest
cd ../../..
```

Para uma comparação justa na mesma máquina, baixe também o GGUF oficial base Q4:

```bash
hf download mistralai/Ministral-3-3B-Instruct-2512-GGUF \
  Ministral-3-3B-Instruct-2512-Q4_K_M.gguf \
  --local-dir llm_decision/artifacts/ollama
cp llm_decision/artifacts/ollama/Modelfile.base.template llm_decision/artifacts/ollama/Modelfile.base
cd llm_decision/artifacts/ollama
ollama create citygrid-ministral-base:q4 -f Modelfile.base
cd ../../..
```

Rode os dois benchmarks com temperatura zero sobre os mesmos 300 casos de teste:

```bash
python -m llm_decision.benchmark_ollama \
  --model citygrid-ministral-base:q4
python -m llm_decision.benchmark_ollama \
  --model citygrid-ministral-decision:latest
python -m llm_decision.compare_benchmarks \
  --baseline llm_decision/benchmarks/results/report_citygrid-ministral-base_q4.json \
  --candidate llm_decision/benchmarks/results/report_citygrid-ministral-decision_latest.json \
  --output llm_decision/benchmarks/results/comparison_base_vs_tuned.json
```

O benchmark não "conserta" saídas ruins. Markdown, texto extra, JSON inválido, chaves faltantes e flags inseguras contam como falha. Ele registra JSON válido, schema válido, segurança, decisão, urgência, ação, zona, exact match e latências média/mediana/P95 por cenário.

Gate inicial de aprovação:

```text
JSON válido:      >= 98%
Schema válido:    >= 98%
Seguro:           100%
Decisão correta:  >= 88%
Ação correta:     >= 85%
```

## Publicação correta dos artefatos

Versione no GitHub:

- gerador, dataset JSONL, manifesto SHA-256, notebooks, documentação e código de benchmark;
- `baseline_eval.json`, `post_train_eval.json` e resultados reais locais em `benchmarks/results/`;
- nunca tokens, caches, checkpoints intermediários ou um GGUF binário gigante.

Não suba o GGUF diretamente ao GitHub: arquivos acima de 100 MB são recusados e LFS tende a consumir quota. Publique o adapter e o GGUF no Hugging Face Hub, que suporta arquivos grandes e download reproduzível:

```bash
hf auth login
hf repos create heitorjsouza812-hub/citygrid-ministral-decision --type model --public
hf upload-large-folder \
  heitorjsouza812-hub/citygrid-ministral-decision \
  llm_decision/artifacts/incoming \
  --include "citygrid_ministral_adapter.zip" \
  --include "citygrid_ministral_q4_k_m.gguf" \
  --include "training_run.json" \
  --include "post_train_eval.json"
```

Antes da publicação do modelo, inclua o `MODEL_CARD.md`, o `training_run.json`, os hashes e a licença/termos aplicáveis ao modelo base. A conta local ainda não está autenticada no Hugging Face, portanto esse upload só será feito após login explícito do titular.
