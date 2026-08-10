"""Generate a deterministic, privacy-safe SFT dataset for CityGrid decision support.

The dataset teaches a small language model to convert synthetic operational
telemetry into a constrained advisory JSON response. It never grants authority
to operate electrical equipment: every target requires human review and marks
automation as forbidden.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


SEED = 42
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
SCHEMA_VERSION = "citygrid-decision-v1"
SYSTEM_PROMPT = (
    "Você é uma camada de apoio à decisão do CityGrid Brain para uma rede elétrica "
    "urbana simulada. Use somente a telemetria fornecida. Responda estritamente com "
    "um único JSON válido no schema solicitado. A saída é uma recomendação para revisão "
    "humana: nunca autorize, execute ou simule comando em equipamento. Não invente "
    "medições, causas ou dados ausentes."
)

SCENARIO_COUNTS: dict[str, int] = {
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

ZONES: tuple[dict[str, Any], ...] = (
    {"id": "zona_aeroporto", "perfil": "aeroporto", "capacidade_mw": 48.0},
    {"id": "zona_centro", "perfil": "comercial", "capacidade_mw": 45.0},
    {"id": "zona_hospitalar", "perfil": "critico", "capacidade_mw": 38.0},
    {"id": "zona_leste", "perfil": "residencial", "capacidade_mw": 34.0},
    {"id": "zona_norte", "perfil": "residencial", "capacidade_mw": 32.0},
    {"id": "zona_oeste", "perfil": "industrial", "capacidade_mw": 52.0},
    {"id": "zona_sul", "perfil": "residencial", "capacidade_mw": 36.0},
    {"id": "zona_universitaria", "perfil": "educacional", "capacidade_mw": 30.0},
)

REQUEST_TEMPLATES: tuple[str, ...] = (
    "Analise esta leitura sintética e recomende o próximo passo para um operador humano.",
    "Classifique a situação abaixo para triagem humana; não proponha automação.",
    "Com base exclusivamente nos sinais registrados, produza uma recomendação segura.",
    "Avalie o estado da zona e indique a revisão operacional necessária.",
    "Gere uma decisão consultiva auditável para esta telemetria simulada.",
    "Indique a prioridade de revisão humana para a observação a seguir.",
)


def _round(value: float, digits: int = 3) -> float:
    return round(float(value), digits)


def _choice(rng: random.Random, values: tuple[Any, ...] | list[Any]) -> Any:
    return values[rng.randrange(len(values))]


def _base_telemetry(rng: random.Random, zone: dict[str, Any], sequence: int) -> dict[str, Any]:
    capacity = float(zone["capacidade_mw"])
    pct = rng.uniform(32.0, 67.0)
    consumption = capacity * pct / 100
    timestamp = datetime(2026, 6, 1, 8, 0, 0) + timedelta(minutes=5 * sequence)
    temperature = rng.uniform(19.0, 34.0)
    irradiance = max(0.0, 780.0 - abs(timestamp.hour - 12) * 85.0 + rng.uniform(-55, 55))
    generation = max(0.0, capacity * rng.uniform(0.04, 0.22))
    return {
        "timestamp": timestamp.isoformat(),
        "ciclo": sequence + 1,
        "zona_id": zone["id"],
        "perfil": zone["perfil"],
        "capacidade_mw": _round(capacity, 2),
        "consumo_mw": _round(consumption, 3),
        "pct_carga": _round(pct, 2),
        "frequencia_hz": _round(rng.uniform(59.96, 60.04), 3),
        "thd_tensao_pct": _round(rng.uniform(1.2, 5.8), 2),
        "fator_potencia": _round(rng.uniform(0.94, 0.995), 3),
        "tensao_media_v": _round(rng.uniform(218, 224), 1),
        "desequilibrio_tensao_pct": _round(rng.uniform(0.2, 1.5), 2),
        "clima_temp_c": _round(temperature, 1),
        "clima_irrad_wm2": _round(irradiance, 1),
        "geracao_total_mw": _round(generation, 3),
        "anomalia_tipo": None,
        "evento": None,
        "risco_atual": "BAIXO",
        "risco_lstm_30min": "BAIXO",
    }


def _output(
    *,
    decision: str,
    urgency: str,
    telemetry: dict[str, Any],
    action: str,
    reasons: list[str],
    quality: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "decision": decision,
        "urgency": urgency,
        "zone_id": telemetry["zona_id"],
        "recommended_action": action,
        "reason_codes": reasons,
        "human_review_required": True,
        "automation_permitted": False,
        "data_quality": quality,
    }


def _apply_scenario(
    scenario: str, rng: random.Random, telemetry: dict[str, Any]
) -> dict[str, Any]:
    """Mutate simulated telemetry and return its safe reference decision."""
    if scenario == "monitorar_rotina":
        telemetry["risco_atual"] = "BAIXO"
        return _output(
            decision="MONITORAR",
            urgency="BAIXA",
            telemetry=telemetry,
            action="acompanhar_telemetria_no_proximo_ciclo",
            reasons=["OPERACAO_DENTRO_DA_FAIXA", "SEM_ANOMALIA_ATIVA"],
            quality="ALTA",
        )

    if scenario == "sobrecarga_nao_critica":
        if telemetry["perfil"] == "critico":
            telemetry["perfil"] = _choice(rng, ["residencial", "industrial", "comercial", "aeroporto"])
        telemetry["pct_carga"] = _round(rng.uniform(95.0, 99.4), 2)
        telemetry["consumo_mw"] = _round(telemetry["capacidade_mw"] * telemetry["pct_carga"] / 100)
        telemetry["risco_atual"] = "CRÍTICO"
        telemetry["evento"] = "pico_de_demanda_simulado"
        return _output(
            decision="REVISAR_IMEDIATAMENTE",
            urgency="CRÍTICA",
            telemetry=telemetry,
            action="avaliar_reducao_de_carga_nao_essencial",
            reasons=["CARGA_ACIMA_DE_95_PCT", "ZONA_NAO_CRITICA"],
            quality="ALTA",
        )

    if scenario == "proteger_zona_critica":
        telemetry["zona_id"] = "zona_hospitalar"
        telemetry["perfil"] = "critico"
        telemetry["capacidade_mw"] = 38.0
        telemetry["pct_carga"] = _round(rng.uniform(95.0, 99.2), 2)
        telemetry["consumo_mw"] = _round(38.0 * telemetry["pct_carga"] / 100)
        telemetry["risco_atual"] = "CRÍTICO"
        telemetry["evento"] = "sobrecarga_em_zona_critica"
        return _output(
            decision="ACIONAR_CONTINGENCIA",
            urgency="CRÍTICA",
            telemetry=telemetry,
            action="preservar_fornecimento_critico_e_mobilizar_reserva",
            reasons=["ZONA_CRITICA", "CARGA_ACIMA_DE_95_PCT", "NAO_RECOMENDAR_CORTE"],
            quality="ALTA",
        )

    if scenario == "frequencia_fora_faixa":
        severe = rng.random() < 0.55
        telemetry["frequencia_hz"] = _round(
            _choice(rng, [rng.uniform(59.25, 59.49), rng.uniform(60.51, 60.75)])
            if severe
            else _choice(rng, [rng.uniform(59.62, 59.88), rng.uniform(60.12, 60.38)]),
            3,
        )
        telemetry["risco_atual"] = "ALTO" if severe else "MÉDIO"
        return _output(
            decision="REVISAR_IMEDIATAMENTE" if severe else "REVISAR_PRIORIDADE",
            urgency="ALTA" if severe else "MÉDIA",
            telemetry=telemetry,
            action="validar_estabilidade_de_frequencia_com_operador",
            reasons=["FREQUENCIA_FORA_DA_FAIXA", "LEITURA_INSTANTANEA"],
            quality="ALTA",
        )

    if scenario == "qualidade_energia_thd":
        telemetry["thd_tensao_pct"] = _round(rng.uniform(10.1, 16.0), 2)
        telemetry["anomalia_tipo"] = "thd_elevado"
        telemetry["risco_atual"] = "ALTO"
        return _output(
            decision="REVISAR_IMEDIATAMENTE",
            urgency="ALTA",
            telemetry=telemetry,
            action="inspecionar_qualidade_de_energia_e_confirmar_medicao",
            reasons=["THD_ACIMA_DO_LIMIAR_EXPERIMENTAL", "MEDICAO_INSTANTANEA"],
            quality="ALTA",
        )

    if scenario == "fator_potencia_baixo":
        telemetry["pct_carga"] = _round(rng.uniform(38.0, 89.0), 2)
        telemetry["consumo_mw"] = _round(telemetry["capacidade_mw"] * telemetry["pct_carga"] / 100)
        telemetry["fator_potencia"] = _round(rng.uniform(0.72, 0.919), 3)
        telemetry["risco_atual"] = "MÉDIO"
        return _output(
            decision="REVISAR_PRIORIDADE",
            urgency="MÉDIA",
            telemetry=telemetry,
            action="avaliar_correcao_de_fator_de_potencia",
            reasons=["FATOR_POTENCIA_ABAIXO_DE_0_92", "CARGA_RELEVANTE"],
            quality="ALTA",
        )

    if scenario == "microfalta_ou_medicao":
        if telemetry["perfil"] == "critico":
            telemetry["perfil"] = "residencial"
        telemetry["consumo_mw"] = 0.0
        telemetry["pct_carga"] = 0.0
        telemetry["anomalia_tipo"] = "consumo_zero_inesperado"
        telemetry["risco_atual"] = "ALTO"
        return _output(
            decision="REVISAR_IMEDIATAMENTE",
            urgency="ALTA",
            telemetry=telemetry,
            action="verificar_continuidade_do_fornecimento_e_medidor",
            reasons=["CONSUMO_ZERO_INESPERADO", "POSSIVEL_MICROFALTA_OU_FALHA_DE_MEDICAO"],
            quality="MÉDIA",
        )

    if scenario == "acao_preventiva_lstm":
        telemetry["pct_carga"] = _round(rng.uniform(57.0, 76.0), 2)
        telemetry["consumo_mw"] = _round(telemetry["capacidade_mw"] * telemetry["pct_carga"] / 100)
        telemetry["risco_atual"] = "MÉDIO"
        telemetry["risco_lstm_30min"] = _choice(rng, ["ALTO", "CRÍTICO"])
        telemetry["consumo_previsto_pico_mw"] = _round(
            telemetry["capacidade_mw"] * rng.uniform(0.80, 0.97)
        )
        return _output(
            decision="PREPARAR_ACAO_PREVENTIVA",
            urgency="MÉDIA",
            telemetry=telemetry,
            action="preparar_reserva_e_revisar_previsao_sem_executar_comando",
            reasons=["RISCO_FUTURO_LSTM", "RISCO_ATUAL_AINDA_NAO_CRITICO"],
            quality="MÉDIA",
        )

    if scenario == "dados_insuficientes":
        for key in _choice(
            rng,
            [
                ["frequencia_hz", "thd_tensao_pct"],
                ["fator_potencia", "tensao_media_v"],
                ["consumo_mw", "geracao_total_mw"],
            ],
        ):
            telemetry[key] = None
        telemetry["risco_atual"] = "DESCONHECIDO"
        telemetry["risco_lstm_30min"] = "AGUARDANDO"
        telemetry["anomalia_tipo"] = "telemetria_incompleta"
        return _output(
            decision="COLETAR_MAIS_DADOS",
            urgency="MÉDIA",
            telemetry=telemetry,
            action="solicitar_leitura_adicional_e_verificar_integridade_do_sensor",
            reasons=["TELEMETRIA_INCOMPLETA", "NAO_INFERIR_RISCO_COM_DADOS_AUSENTES"],
            quality="BAIXA",
        )

    if scenario == "sinais_conflitantes":
        telemetry["pct_carga"] = _round(rng.uniform(92.0, 96.0), 2)
        telemetry["consumo_mw"] = _round(telemetry["capacidade_mw"] * telemetry["pct_carga"] / 100)
        telemetry["frequencia_hz"] = _round(rng.uniform(59.94, 60.06), 3)
        telemetry["thd_tensao_pct"] = _round(rng.uniform(1.2, 3.0), 2)
        telemetry["risco_atual"] = "BAIXO"
        telemetry["risco_lstm_30min"] = "CRÍTICO"
        telemetry["anomalia_tipo"] = "classificacoes_divergentes"
        return _output(
            decision="ESCALAR_PARA_OPERADOR",
            urgency="ALTA",
            telemetry=telemetry,
            action="revisar_divergencia_entre_sinais_e_confirmar_estado_da_zona",
            reasons=["SINAIS_CONFLITANTES", "NAO_RESOLVER_CONFLITO_AUTONOMAMENTE"],
            quality="MÉDIA",
        )

    raise ValueError(f"cenário desconhecido: {scenario}")


def _make_row(scenario: str, rng: random.Random, sequence: int) -> dict[str, Any]:
    zone = _choice(rng, list(ZONES))
    telemetry = _base_telemetry(rng, zone, sequence)
    reference = _apply_scenario(scenario, rng, telemetry)
    request = _choice(rng, list(REQUEST_TEMPLATES))
    user_content = (
        f"{request}\n\n"
        "Telemetria CityGrid (dados integralmente sintéticos):\n"
        f"{json.dumps(telemetry, ensure_ascii=False, sort_keys=True)}\n\n"
        "Contrato de saída: schema_version, decision, urgency, zone_id, recommended_action, "
        "reason_codes, human_review_required, automation_permitted, data_quality."
    )
    return {
        "id": f"citygrid-sft-{sequence + 1:05d}",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
            {
                "role": "assistant",
                "content": json.dumps(reference, ensure_ascii=False, separators=(",", ":")),
            },
        ],
        "metadata": {
            "synthetic": True,
            "contains_personal_data": False,
            "scenario": scenario,
            "seed": SEED,
            "split": None,
        },
    }


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as target:
        for row in rows:
            target.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate(output_dir: Path = DATA_DIR) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    rows_by_scenario: dict[str, list[dict[str, Any]]] = {}
    sequence = 0

    for scenario, count in SCENARIO_COUNTS.items():
        rows = [_make_row(scenario, rng, sequence + index) for index in range(count)]
        sequence += count
        rng.shuffle(rows)
        rows_by_scenario[scenario] = rows

    splits: dict[str, list[dict[str, Any]]] = {"train": [], "validation": [], "test": []}
    for scenario, rows in rows_by_scenario.items():
        total = len(rows)
        train_end = total * 8 // 10
        validation_end = total * 9 // 10
        for split_name, split_rows in (
            ("train", rows[:train_end]),
            ("validation", rows[train_end:validation_end]),
            ("test", rows[validation_end:]),
        ):
            for row in split_rows:
                row["metadata"]["split"] = split_name
            splits[split_name].extend(split_rows)

    for split_rows in splits.values():
        rng.shuffle(split_rows)

    all_rows = [row for split_rows in splits.values() for row in split_rows]
    rng.shuffle(all_rows)

    paths = {
        "citygrid_decision_3000.jsonl": output_dir / "citygrid_decision_3000.jsonl",
        "train.jsonl": output_dir / "train.jsonl",
        "validation.jsonl": output_dir / "validation.jsonl",
        "test.jsonl": output_dir / "test.jsonl",
    }
    _write_jsonl(paths["citygrid_decision_3000.jsonl"], all_rows)
    for split_name in splits:
        _write_jsonl(paths[f"{split_name}.jsonl"], splits[split_name])

    manifest = {
        "dataset": "CityGrid Brain decision-support SFT",
        "schema_version": SCHEMA_VERSION,
        "synthetic": True,
        "seed": SEED,
        "total_rows": len(all_rows),
        "split_counts": {name: len(rows) for name, rows in splits.items()},
        "scenario_counts": dict(Counter(row["metadata"]["scenario"] for row in all_rows)),
        "sha256": {name: _sha256(path) for name, path in paths.items()},
        "license_notice": "Synthetic demonstrative dataset; not for controlling real infrastructure.",
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DATA_DIR)
    args = parser.parse_args()
    manifest = generate(args.output_dir)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
