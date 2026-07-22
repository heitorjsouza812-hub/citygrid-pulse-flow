from __future__ import annotations

from datetime import datetime, timezone

import pytest

import consumer


def test_extrair_timestamp_aceita_iso_e_preserva_relogio_simulado() -> None:
    instante = consumer.extrair_timestamp({"timestamp": "2026-01-07T23:15:00"})
    assert instante == datetime(2026, 1, 7, 23, 15, tzinfo=timezone.utc)


def test_extrair_timestamp_rejeita_amostra_sem_timestamp() -> None:
    with pytest.raises(ValueError, match="timestamp"):
        consumer.extrair_timestamp({})


def test_montar_point_usa_precisao_suportada_pelo_influxdb() -> None:
    point = consumer.montar_point(
        {
            "timestamp": "2026-01-07T23:15:00",
            "zona_id": "zona_norte",
            "zona_nome": "Zona Norte",
            "perfil": "residencial",
            "risco": "BAIXO",
            "consumo_mw": 10.5,
            "ciclo": 42,
        }
    )

    assert point is not None
