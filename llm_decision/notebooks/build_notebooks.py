"""Build portable Colab and Kaggle QLoRA notebooks for the CityGrid POC."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_DIR = Path(__file__).resolve().parent
REPO_URL = "https://github.com/heitorjsouza812-hub/citygrid-pulse-flow.git"
REPO_REF = "feat/llm-decision-poc"
MODEL_ID = "mistralai/Ministral-3-3B-Instruct-2512"


def _source(text: str) -> list[str]:
    return [line + "\n" for line in text.strip("\n").splitlines()]


def _markdown(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": _source(text)}


def _code(text: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": _source(text),
    }


def _notebook(environment: str) -> dict:
    output_root = "/content" if environment == "colab" else "/kaggle/working"
    platform_note = (
        "No Colab: Runtime > Change runtime type > T4 GPU (ou melhor)."
        if environment == "colab"
        else "No Kaggle: Settings > Accelerator > GPU e habilite Internet para clonar o repositório e baixar o modelo."
    )
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.11"},
            "colab": {"provenance": []},
        },
        "cells": [
            _markdown(
                f"""# CityGrid Brain — QLoRA de um Ministral 3B para apoio à decisão

Este notebook ajusta `{MODEL_ID}` com o dataset sintético versionado do CityGrid Brain.

- O modelo é um **assistente consultivo**, não um controlador de equipamentos.
- Toda saída exige `human_review_required=true` e `automation_permitted=false`.
- O teste `test.jsonl` é reservado: não altere hiperparâmetros com base nele.
- {platform_note}

> Nota de escolha: a consulta ao Hub identificou o Ministral 3B Instruct oficial como a variante textual pequena adequada. Os resultados de 4B encontrados no namespace Mistral eram modelos de áudio, não um LLM textual para este caso.
"""
            ),
            _code(
                f"""# Configuração explícita e reproduzível.
from pathlib import Path

ENVIRONMENT = \"{environment}\"
REPO_URL = \"{REPO_URL}\"
REPO_REF = \"{REPO_REF}\"
MODEL_ID = \"{MODEL_ID}\"
SEED = 42
MAX_LENGTH = 1024
EPOCHS = 3
EFFECTIVE_BATCH = 8
EVAL_LIMIT = 100  # amostra fixa do teste, somente para relatório final
RUN_GGUF_EXPORT = False  # deixe False até o adapter passar na avaliação

WORK_ROOT = Path(\"{output_root}\")
REPO_DIR = WORK_ROOT / \"citygrid-pulse-flow\"
RUN_DIR = WORK_ROOT / \"citygrid_ministral_qlora\"
ADAPTER_DIR = RUN_DIR / \"adapter\"
RUN_DIR.mkdir(parents=True, exist_ok=True)
print({{\"environment\": ENVIRONMENT, \"model\": MODEL_ID, \"run_dir\": str(RUN_DIR)}})
"""
            ),
            _code(
                """# Dependências de treinamento. O runtime já fornece PyTorch/CUDA; não o reinstale aqui.
import subprocess, sys
subprocess.run(
    [
        sys.executable, "-m", "pip", "install", "-q", "-U",
        "transformers", "peft", "accelerate", "bitsandbytes", "datasets",
        "safetensors", "sentencepiece", "pytest",
    ],
    check=True,
)
"""
            ),
            _code(
                """# Busca uma cópia limpa e pública do projeto, incluindo o dataset e os testes de aceitação.
import subprocess

if REPO_DIR.exists():
    subprocess.run(["git", "-C", str(REPO_DIR), "fetch", "--depth", "1", "origin", REPO_REF], check=True)
    subprocess.run(["git", "-C", str(REPO_DIR), "reset", "--hard", "FETCH_HEAD"], check=True)
else:
    subprocess.run(["git", "clone", "--depth", "1", "--branch", REPO_REF, REPO_URL, str(REPO_DIR)], check=True)

subprocess.run(
    [sys.executable, "-m", "pytest", "-q", "llm_decision/tests/test_dataset_acceptance.py"],
    cwd=REPO_DIR,
    check=True,
)
"""
            ),
            _code(
                """# Verifica hashes e carrega os splits. Falhe cedo se houver dado alterado ou incompleto.
import hashlib, json
from datasets import load_dataset

DATA_DIR = REPO_DIR / "llm_decision" / "data"
manifest = json.loads((DATA_DIR / "manifest.json").read_text(encoding="utf-8"))
for name, expected_sha in manifest["sha256"].items():
    actual_sha = hashlib.sha256((DATA_DIR / name).read_bytes()).hexdigest()
    assert actual_sha == expected_sha, f"SHA-256 divergente: {name}"
assert manifest["split_counts"] == {"train": 2400, "validation": 300, "test": 300}

raw = load_dataset(
    "json",
    data_files={
        "train": str(DATA_DIR / "train.jsonl"),
        "validation": str(DATA_DIR / "validation.jsonl"),
        "test": str(DATA_DIR / "test.jsonl"),
    },
)
print(raw)
print(manifest["scenario_counts"])
"""
            ),
            _code(
                """# Carrega base 4-bit, injeta LoRA e tokeniza apenas a resposta do assistente.
import json
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, TaskType, get_peft_model, prepare_model_for_kbit_training

assert torch.cuda.is_available(), "Ative GPU antes de continuar."
print(torch.cuda.get_device_name(0))

tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, use_fast=True)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

def tokenize_messages(example):
    messages = example["messages"]
    prefix_ids = tokenizer.apply_chat_template(
        messages[:2], tokenize=True, add_generation_prompt=True, truncation=True, max_length=MAX_LENGTH
    )
    full_ids = tokenizer.apply_chat_template(
        messages, tokenize=True, add_generation_prompt=False, truncation=True, max_length=MAX_LENGTH
    )
    if full_ids[:len(prefix_ids)] != prefix_ids:
        raise ValueError("A máscara prompt/resposta não está alinhada ao chat template do modelo.")
    if len(full_ids) <= len(prefix_ids):
        raise ValueError("A resposta foi truncada; aumente MAX_LENGTH antes de treinar.")
    labels = list(full_ids)
    labels[:len(prefix_ids)] = [-100] * len(prefix_ids)
    return {"input_ids": full_ids, "attention_mask": [1] * len(full_ids), "labels": labels}

columns = raw["train"].column_names
tokenized = raw.map(tokenize_messages, remove_columns=columns)
assert all(label == -100 for label in tokenized["train"][0]["labels"][:10])

bnb = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True,
    bnb_4bit_compute_dtype=torch.float16,
)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    quantization_config=bnb,
    device_map="auto",
    torch_dtype=torch.float16,
)
model.config.use_cache = False
model = prepare_model_for_kbit_training(model)
model = get_peft_model(
    model,
    LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    ),
)
model.print_trainable_parameters()
"""
            ),
            _code(
                """# Avaliação estrutural determinística. Execute antes e depois do QLoRA para comparação.
import time
from statistics import median

REQUIRED_KEYS = {
    "schema_version", "decision", "urgency", "zone_id", "recommended_action",
    "reason_codes", "human_review_required", "automation_permitted", "data_quality",
}

def evaluate_structured(current_model, rows, limit=EVAL_LIMIT):
    current_model.eval()
    records, latencies = [], []
    for row in list(rows)[:limit]:
        prompt_ids = tokenizer.apply_chat_template(
            row["messages"][:2], tokenize=True, add_generation_prompt=True, return_tensors="pt"
        ).to(current_model.device)
        started = time.perf_counter()
        with torch.inference_mode():
            generated = current_model.generate(
                prompt_ids,
                max_new_tokens=180,
                do_sample=False,
                temperature=None,
                pad_token_id=tokenizer.eos_token_id,
            )
        latency_ms = (time.perf_counter() - started) * 1000
        raw_response = tokenizer.decode(generated[0][prompt_ids.shape[1]:], skip_special_tokens=True).strip()
        target = json.loads(row["messages"][2]["content"])
        try:
            predicted = json.loads(raw_response)
            schema_valid = isinstance(predicted, dict) and set(predicted) == REQUIRED_KEYS
            safe = bool(schema_valid and predicted["human_review_required"] is True and predicted["automation_permitted"] is False)
            decision_match = bool(schema_valid and predicted["decision"] == target["decision"])
            action_match = bool(schema_valid and predicted["recommended_action"] == target["recommended_action"])
            exact_match = bool(schema_valid and predicted == target)
        except (TypeError, json.JSONDecodeError):
            schema_valid = safe = decision_match = action_match = exact_match = False
        latencies.append(latency_ms)
        records.append({
            "id": row["id"], "scenario": row["metadata"]["scenario"], "target": target,
            "raw_response": raw_response, "schema_valid": schema_valid, "safe": safe,
            "decision_match": decision_match, "action_match": action_match,
            "exact_match": exact_match, "latency_ms": round(latency_ms, 2),
        })
    count = len(records)
    summary = {
        "rows": count,
        "schema_valid": sum(x["schema_valid"] for x in records) / count,
        "safe": sum(x["safe"] for x in records) / count,
        "decision_match": sum(x["decision_match"] for x in records) / count,
        "action_match": sum(x["action_match"] for x in records) / count,
        "exact_match": sum(x["exact_match"] for x in records) / count,
        "latency_ms_median": median(latencies),
    }
    return summary, records

baseline_summary, baseline_records = evaluate_structured(model, raw["test"])
print(json.dumps(baseline_summary, indent=2))
(RUN_DIR / "baseline_eval.json").write_text(json.dumps({"summary": baseline_summary, "records": baseline_records}, ensure_ascii=False, indent=2), encoding="utf-8")
"""
            ),
            _code(
                """# QLoRA: 3 épocas, batch efetivo 8, validação e checkpoints separados do teste.
from transformers import DataCollatorForSeq2Seq, Trainer, TrainingArguments, set_seed

set_seed(SEED)
collator = DataCollatorForSeq2Seq(tokenizer=tokenizer, padding=True, label_pad_token_id=-100, return_tensors="pt")
args = TrainingArguments(
    output_dir=str(RUN_DIR / "checkpoints"),
    num_train_epochs=EPOCHS,
    per_device_train_batch_size=1,
    per_device_eval_batch_size=1,
    gradient_accumulation_steps=EFFECTIVE_BATCH,
    learning_rate=2e-4,
    lr_scheduler_type="cosine",
    warmup_ratio=0.03,
    logging_steps=10,
    eval_strategy="steps",
    eval_steps=50,
    save_strategy="steps",
    save_steps=50,
    save_total_limit=2,
    fp16=True,
    bf16=False,
    optim="paged_adamw_8bit",
    report_to=[],
    seed=SEED,
    data_seed=SEED,
    remove_unused_columns=False,
)
trainer = Trainer(
    model=model,
    args=args,
    train_dataset=tokenized["train"],
    eval_dataset=tokenized["validation"],
    data_collator=collator,
)
train_result = trainer.train()
validation_metrics = trainer.evaluate()
print(train_result.metrics)
print(validation_metrics)
"""
            ),
            _code(
                """# Avaliação final no conjunto de teste reservado. Não retreine usando estes resultados.
post_summary, post_records = evaluate_structured(model, raw["test"])
post_report = {
    "model_id": MODEL_ID,
    "seed": SEED,
    "train_metrics": train_result.metrics,
    "validation_metrics": validation_metrics,
    "baseline": baseline_summary,
    "adapter": post_summary,
    "records": post_records,
}
(RUN_DIR / "post_train_eval.json").write_text(json.dumps(post_report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"baseline": baseline_summary, "adapter": post_summary}, ensure_ascii=False, indent=2))
"""
            ),
            _code(
                """# Salva e verifica o adapter antes de qualquer conversão GGUF.
import platform, zipfile
from datetime import datetime, timezone

model.save_pretrained(ADAPTER_DIR, safe_serialization=True)
tokenizer.save_pretrained(ADAPTER_DIR)
required_adapter_files = ["adapter_model.safetensors", "adapter_config.json"]
for name in required_adapter_files:
    path = ADAPTER_DIR / name
    assert path.exists() and path.stat().st_size > 0, f"Adapter ausente ou vazio: {path}"

adapter_config = json.loads((ADAPTER_DIR / "adapter_config.json").read_text(encoding="utf-8"))
assert adapter_config["base_model_name_or_path"] == MODEL_ID
archive_path = RUN_DIR / "citygrid_ministral_adapter.zip"
with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(ADAPTER_DIR.rglob("*")):
        if path.is_file():
            archive.write(path, path.relative_to(ADAPTER_DIR.parent))

run_manifest = {
    "project": "CityGrid Brain small-LLM decision-support POC",
    "created_at_utc": datetime.now(timezone.utc).isoformat(),
    "base_model": MODEL_ID,
    "dataset_manifest": manifest,
    "seed": SEED,
    "hyperparameters": {"epochs": EPOCHS, "max_length": MAX_LENGTH, "effective_batch": EFFECTIVE_BATCH, "lora_r": 16, "lora_alpha": 32},
    "adapter_archive": str(archive_path),
    "adapter_archive_bytes": archive_path.stat().st_size,
    "environment": {"python": platform.python_version(), "torch": torch.__version__, "gpu": torch.cuda.get_device_name(0)},
}
(RUN_DIR / "training_run.json").write_text(json.dumps(run_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print(run_manifest)
"""
            ),
            _markdown(
                """## Exportação GGUF (opcional, depois da aprovação do adapter)

Deixe `RUN_GGUF_EXPORT=False` na primeira execução. O adapter ZIP e os relatórios já são o artefato mínimo durável. Se a conversão abaixo falhar por disco/RAM, **não treine de novo**: guarde o ZIP e faça o merge em outro runtime.
"""
            ),
            _code(
                """# Converte base FP16 + LoRA para GGUF Q4_K_M, adequado à inferência local.
# Só execute após validar post_train_eval.json e com espaço temporário suficiente.
if RUN_GGUF_EXPORT:
    import gc, shutil
    from peft import PeftModel

    merged_dir = RUN_DIR / "merged_fp16"
    del model
    gc.collect()
    torch.cuda.empty_cache()
    base_fp16 = AutoModelForCausalLM.from_pretrained(MODEL_ID, torch_dtype=torch.float16, device_map="cpu")
    merged = PeftModel.from_pretrained(base_fp16, ADAPTER_DIR).merge_and_unload()
    merged.save_pretrained(merged_dir, safe_serialization=True)
    tokenizer.save_pretrained(merged_dir)

    llama_dir = RUN_DIR / "llama.cpp"
    if not llama_dir.exists():
        subprocess.run(["git", "clone", "--depth", "1", "https://github.com/ggerganov/llama.cpp", str(llama_dir)], check=True)
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "requirements.txt"], cwd=llama_dir, check=True)
    subprocess.run(["cmake", "-B", "build"], cwd=llama_dir, check=True)
    subprocess.run(["cmake", "--build", "build", "--config", "Release", "-j", "2"], cwd=llama_dir, check=True)

    f16_gguf = RUN_DIR / "citygrid_ministral_f16.gguf"
    q4_gguf = RUN_DIR / "citygrid_ministral_q4_k_m.gguf"
    subprocess.run([sys.executable, "convert_hf_to_gguf.py", str(merged_dir), "--outfile", str(f16_gguf), "--outtype", "f16"], cwd=llama_dir, check=True)
    quantize = llama_dir / "build" / "bin" / "llama-quantize"
    subprocess.run([str(quantize), str(f16_gguf), str(q4_gguf), "Q4_K_M"], check=True)
    assert q4_gguf.read_bytes()[:4] == b"GGUF"
    print({"gguf": str(q4_gguf), "bytes": q4_gguf.stat().st_size})
"""
            ),
            _markdown(
                """## Artefatos a baixar

Baixe/preserve, nesta ordem:

1. `citygrid_ministral_adapter.zip`
2. `training_run.json`
3. `baseline_eval.json`
4. `post_train_eval.json`
5. `citygrid_ministral_q4_k_m.gguf` — somente se a célula de exportação foi executada e confirmou o cabeçalho GGUF.

No Kaggle, use **Save Version → Save & Run All** antes de baixar a aba Output. No Colab, copie `RUN_DIR` para o Google Drive antes de encerrar o runtime.
"""
            ),
        ],
    }


def main() -> None:
    NOTEBOOK_DIR.mkdir(parents=True, exist_ok=True)
    for environment in ("colab", "kaggle"):
        path = NOTEBOOK_DIR / f"citygrid_qlora_{environment}.ipynb"
        path.write_text(json.dumps(_notebook(environment), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(path)


if __name__ == "__main__":
    main()
