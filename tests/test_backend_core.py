from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime

import backend


def _reset_cache() -> None:
    backend._cache.update(
        {
            "zonas": {},
            "historicos": defaultdict(lambda: deque(maxlen=backend.JANELA_LSTM * 4)),
            "alertas": deque(maxlen=50),
            "stats": {},
            "ciclo_atual": 0,
            "ultima_leitura": None,
            "ultima_chave_por_zona": {},
        }
    )


def test_features_de_tempo_usam_timestamp_simulado_da_amostra() -> None:
    instante = backend.extrair_instante_amostra(
        {"timestamp": "2026-01-07T23:15:00"}
    )

    assert instante == datetime(2026, 1, 7, 23, 15)
    assert instante.hour == 23
    assert instante.weekday() == 2


def test_cache_nao_duplica_uma_leitura_reprocessada() -> None:
    _reset_cache()
    leitura = {
        "zona_id": "zona_norte",
        "ciclo": 10,
        "timestamp": "2026-01-01T00:50:00",
    }

    backend.incorporar_leituras_cache([leitura, leitura])
    backend.incorporar_leituras_cache([leitura])

    assert len(backend._cache["historicos"]["zona_norte"]) == 1

    proxima = {**leitura, "ciclo": 11, "timestamp": "2026-01-01T00:55:00"}
    backend.incorporar_leituras_cache([proxima])
    assert len(backend._cache["historicos"]["zona_norte"]) == 2


def test_stats_rotulam_energia_renovavel_sem_alegar_economia() -> None:
    zonas = [
        {
            "consumo_mw": 10.0,
            "geracao_total_mw": 2.0,
            "risco": "CRÍTICO",
            "risco_xgb": "BAIXO",
            "anomalia_tipo": None,
            "evento": None,
        }
    ]

    stats = backend.calcular_stats(zonas, total_recomendacoes=3, intervalo_minutos=5)

    assert "economia_mwh" not in stats
    assert stats["energia_renovavel_intervalo_mwh"] == 0.1667
    assert stats["total_recomendacoes"] == 3
    assert stats["zonas_criticas"] == 1
