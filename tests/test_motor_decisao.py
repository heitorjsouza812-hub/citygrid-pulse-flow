from __future__ import annotations

import numpy as np
from collections import deque

import motor_decisao as motor


class ModeloStub:
    def __init__(self) -> None:
        self.entrada = None

    def predict_proba(self, entrada):
        self.entrada = entrada
        return np.array([[0.1, 0.1, 0.7, 0.1]])


def test_xgboost_usa_horario_da_amostra_e_rotula_score() -> None:
    modelo = ModeloStub()
    dados = {
        "timestamp": "2026-01-07T23:15:00",
        "pct_carga": 96.0,
        "consumo_mw": 10.0,
    }

    risco, score, explicacao = motor.avaliar_xgboost("zona_norte", dados, modelo)

    assert risco == "CRÍTICO"
    assert score == 0.7
    assert modelo.entrada[0, motor.FEATURES_XGB.index("hora")] == 23
    assert modelo.entrada[0, motor.FEATURES_XGB.index("dia_semana")] == 2
    assert "score" in explicacao.lower()
    assert "confiança" not in explicacao.lower()


def test_heuristica_recomenda_sem_alegar_execucao_automatica() -> None:
    recomendacao = motor.avaliar_heuristicas(
        "zona_norte",
        {
            "pct_carga": 97.0,
            "frequencia_hz": 60.0,
            "thd_tensao_pct": 2.0,
            "fator_potencia": 0.98,
            "consumo_mw": 20.0,
            "perfil": "residencial",
        },
    )

    assert recomendacao is not None
    texto = f"{recomendacao.descricao} {recomendacao.explicacao}".lower()
    assert "recomendar" in texto
    assert "ação automática" not in texto
    assert recomendacao.confianca is None


def test_motor_nao_trata_previsao_xgb_como_risco_atual() -> None:
    instancia = motor.MotorDecisao.__new__(motor.MotorDecisao)
    instancia.modelo_xgb = ModeloStub()
    instancia.modelos_lstm = {}
    instancia.scalers_zona = {}
    instancia.device = "cpu"
    instancia.historicos = {}
    instancia.log_acoes = deque(maxlen=50)
    instancia.ciclo = 0
    instancia.stats = {"total_acoes": 0, "por_origem": {}, "por_urgencia": {}}
    instancia._salvar_log = lambda *_args, **_kwargs: None

    recomendacoes, estados = instancia.processar_ciclo(
        [
            {
                "zona_id": "zona_norte",
                "timestamp": "2026-01-07T23:15:00",
                "ciclo": 10,
                "risco": "BAIXO",
                "pct_carga": 40.0,
                "consumo_mw": 8.0,
                "capacidade_mw": 20.0,
                "frequencia_hz": 60.0,
                "thd_tensao_pct": 2.0,
                "fator_potencia": 0.98,
                "perfil": "residencial",
            }
        ],
        ciclo_id=10,
    )

    assert estados["zona_norte"].risco_atual == "BAIXO"
    assert estados["zona_norte"].risco_xgb == "CRÍTICO"
    assert recomendacoes[0].tipo == "REVISAR_RISCO_PREVISTO_XGB"
    assert recomendacoes[0].timestamp == "2026-01-07T23:15:00"
