"""Acceptance tests for the deterministic CityGrid decision-support SFT dataset."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "llm_decision" / "data"
EXPECTED_SCENARIOS = {
    "monitorar_rotina": 600,
    "sobrecarga_nao_critica": 350,
    "proteger_zona_critica": 280,
    "frequencia_fora_faixa": 320,
    "qualidade_energia_thd": 280,
    "fator_potencia_baixo": 260,
    "microfalta_ou_medicao": 180,
    "acao_preventiva_lstm": 360,
    "dados_insuficientes": 220,
    "sinais_conflitantes": 150,
}
EXPECTED_SPLITS = {"train": 2400, "validation": 300, "test": 300}


def _read_jsonl(path: Path) -> list[dict]:
    assert path.exists(), f"dataset file missing: {path}"
    rows = []
    with path.open(encoding="utf-8") as source:
        for line_number, raw in enumerate(source, start=1):
            assert raw.strip(), f"blank line in {path}:{line_number}"
            rows.append(json.loads(raw))
    return rows


def _canonical_digest(path: Path) -> str:
    # Dataset manifests are generated with LF. Normalize checkout line endings so
    # the reproducibility assertion is identical on Windows and CI/Linux.
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def test_dataset_contract_and_exact_distributions() -> None:
    main_rows = _read_jsonl(DATA_DIR / "citygrid_decision_3000.jsonl")
    manifest = json.loads((DATA_DIR / "manifest.json").read_text(encoding="utf-8"))

    assert len(main_rows) == 3000
    assert len({row["id"] for row in main_rows}) == 3000
    assert Counter(row["metadata"]["scenario"] for row in main_rows) == EXPECTED_SCENARIOS
    assert manifest["seed"] == 42
    assert manifest["synthetic"] is True
    assert manifest["total_rows"] == 3000
    assert manifest["scenario_counts"] == EXPECTED_SCENARIOS
    assert manifest["sha256"]["citygrid_decision_3000.jsonl"] == _canonical_digest(
        DATA_DIR / "citygrid_decision_3000.jsonl"
    )

    for row in main_rows:
        assert row["metadata"]["synthetic"] is True
        assert row["metadata"]["contains_personal_data"] is False
        messages = row["messages"]
        assert [message["role"] for message in messages] == ["system", "user", "assistant"]
        output = json.loads(messages[-1]["content"])
        assert set(output) == {
            "schema_version",
            "decision",
            "urgency",
            "zone_id",
            "recommended_action",
            "reason_codes",
            "human_review_required",
            "automation_permitted",
            "data_quality",
        }
        assert output["human_review_required"] is True
        assert output["automation_permitted"] is False
        assert output["zone_id"].startswith("zona_")
        assert output["urgency"] in {"BAIXA", "MÉDIA", "ALTA", "CRÍTICA"}
        assert output["data_quality"] in {"ALTA", "MÉDIA", "BAIXA"}


def test_splits_are_exact_disjoint_and_cover_main_dataset() -> None:
    main_rows = _read_jsonl(DATA_DIR / "citygrid_decision_3000.jsonl")
    split_ids: dict[str, set[str]] = {}

    for split_name, expected_size in EXPECTED_SPLITS.items():
        rows = _read_jsonl(DATA_DIR / f"{split_name}.jsonl")
        assert len(rows) == expected_size
        split_ids[split_name] = {row["id"] for row in rows}
        assert len(split_ids[split_name]) == expected_size

    assert not split_ids["train"] & split_ids["validation"]
    assert not split_ids["train"] & split_ids["test"]
    assert not split_ids["validation"] & split_ids["test"]
    assert set().union(*split_ids.values()) == {row["id"] for row in main_rows}


def test_inputs_have_substantive_diversity_and_no_real_identifiers() -> None:
    rows = _read_jsonl(DATA_DIR / "citygrid_decision_3000.jsonl")
    inputs = [row["messages"][1]["content"] for row in rows]
    assert len(set(inputs)) >= 2950
    combined = "\n".join(inputs).lower()
    assert "cpf" not in combined
    assert "@gmail.com" not in combined
    assert "telefone" not in combined
