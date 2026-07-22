from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from citygrid_config import carregar_env_local
import producer


ROOT = Path(__file__).resolve().parents[1]


def test_carregar_env_local_le_arquivo_sem_sobrescrever_ambiente(tmp_path, monkeypatch) -> None:
    arquivo = tmp_path / ".env"
    arquivo.write_text("CITYGRID_TESTE_ENV=arquivo\nCITYGRID_PRESERVAR=arquivo\n", encoding="utf-8")
    monkeypatch.delenv("CITYGRID_TESTE_ENV", raising=False)
    monkeypatch.setenv("CITYGRID_PRESERVAR", "processo")

    carregar_env_local(arquivo)

    assert os.environ["CITYGRID_TESTE_ENV"] == "arquivo"
    assert os.environ["CITYGRID_PRESERVAR"] == "processo"


def test_streaming_alinha_relogio_simulado_ao_utc_atual(monkeypatch) -> None:
    instante = datetime(2026, 7, 22, 19, 30, tzinfo=timezone.utc)
    monkeypatch.setitem(producer.sim.estado, "tempo_simulado", datetime(2026, 1, 1))
    monkeypatch.setitem(producer.sim.estado, "ciclo", 99)

    inicio = producer.alinhar_relogio_streaming(instante)

    assert inicio == datetime(2026, 7, 22, 19, 30)
    assert producer.sim.estado["tempo_simulado"] == inicio
    assert producer.sim.estado["ciclo"] == 0


def test_grafana_usa_bucket_do_datasource_e_janela_selecionada() -> None:
    dashboard = json.loads(
        (ROOT / "grafana/provisioning/dashboards/citygrid.json").read_text(encoding="utf-8")
    )
    consultas = [
        alvo["query"]
        for painel in dashboard["panels"]
        for alvo in painel.get("targets", [])
        if "query" in alvo
    ]

    assert consultas
    assert all("from(bucket: v.defaultBucket)" in consulta for consulta in consultas)
    assert all("v.timeRangeStart" in consulta for consulta in consultas)
    assert all('from(bucket: "citygrid")' not in consulta for consulta in consultas)
    assert all("range(start: -2m)" not in consulta for consulta in consultas)

    titulos = " ".join(painel.get("title", "") for painel in dashboard["panels"])
    assert "limite ANEEL: 8%" not in titulos