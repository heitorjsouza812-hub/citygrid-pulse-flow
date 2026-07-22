from __future__ import annotations

import numpy as np
import pandas as pd

from ml_core import (
    CLASSES_RISCO,
    baseline_majoritaria,
    calcular_pesos_classes,
    metricas_classificacao,
    metricas_previsao,
    preparar_dataset_xgb,
    previsao_persistencia_risco,
    split_temporal_sincronizado,
)


def _dataset_sintetico(ciclos: int = 60, zonas: int = 3) -> pd.DataFrame:
    rows = []
    classes = list(CLASSES_RISCO)
    for ciclo in range(1, ciclos + 1):
        timestamp = pd.Timestamp("2026-01-01") + pd.Timedelta(minutes=5 * ciclo)
        for zona in range(zonas):
            risco = classes[(ciclo // 5 + zona) % len(classes)]
            rows.append(
                {
                    "ciclo": ciclo,
                    "timestamp": timestamp,
                    "zona_id": f"zona_{zona}",
                    "risco": risco,
                    "pct_carga": 20 + ciclo + zona,
                    "consumo_mw": 5 + ciclo / 10 + zona,
                    "consumo_liquido_mw": 4 + ciclo / 10 + zona,
                    "clima_temp_c": 25.0,
                    "clima_irrad_wm2": 500.0,
                    "clima_umidade_pct": 60.0,
                    "thd_tensao_pct": 2.0,
                    "fator_potencia": 0.96,
                    "desequilibrio_tensao_pct": 1.0,
                    "frequencia_hz": 60.0,
                    "tensao_media_v": 220.0,
                    "pot_ativa_kw": 5000.0,
                    "pot_reativa_kvar": 1000.0,
                    "ve_demanda_kw": 10.0,
                    "ve_ocupacao_pct": 30.0,
                    "bat_soc_pct": 70.0,
                    "geracao_total_mw": 1.0,
                    "autoprod_pct": 10.0,
                    "anomalia_tipo": None,
                    "evento": None,
                }
            )
    return pd.DataFrame(rows)


def test_split_sincroniza_zonas_e_aplica_embargo_ao_horizonte() -> None:
    preparado = preparar_dataset_xgb(_dataset_sintetico(), horizonte=6)
    split = split_temporal_sincronizado(preparado, horizonte=6)

    ciclos = {
        nome: set(frame["ciclo"].unique())
        for nome, frame in {
            "treino": split.treino,
            "validacao": split.validacao,
            "teste": split.teste,
        }.items()
    }

    assert ciclos["treino"].isdisjoint(ciclos["validacao"])
    assert ciclos["treino"].isdisjoint(ciclos["teste"])
    assert ciclos["validacao"].isdisjoint(ciclos["teste"])
    assert max(split.treino["ciclo_alvo"]) < min(split.validacao["ciclo"])
    assert max(split.validacao["ciclo_alvo"]) < min(split.teste["ciclo"])

    for frame in (split.treino, split.validacao, split.teste):
        assert frame.groupby("ciclo")["zona_id"].nunique().nunique() == 1
        assert frame.groupby("ciclo")["zona_id"].nunique().iloc[0] == 3


def test_pesos_de_classe_sao_balanceados_e_finitos() -> None:
    y_treino = np.array([0, 0, 0, 1, 2, 3])
    pesos = calcular_pesos_classes(y_treino, n_classes=4)

    assert pesos.shape == y_treino.shape
    assert np.isfinite(pesos).all()
    assert pesos[y_treino == 0][0] < pesos[y_treino == 1][0]


def test_metricas_expoem_desempenho_por_classe_e_balanceado() -> None:
    y_true = np.array([0, 1, 2, 3])
    y_pred = np.array([0, 1, 1, 1])

    metricas = metricas_classificacao(y_true, y_pred, CLASSES_RISCO)

    assert metricas["matriz_confusao"] == [
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 1, 0, 0],
        [0, 1, 0, 0],
    ]
    assert metricas["por_classe"]["CRÍTICO"]["recall"] == 0.0
    assert 0.0 <= metricas["f1_macro"] <= 1.0
    assert 0.0 <= metricas["acuracia_balanceada"] <= 1.0


def test_baselines_usam_apenas_treino_e_estado_atual() -> None:
    preparado = preparar_dataset_xgb(_dataset_sintetico(), horizonte=6)
    split = split_temporal_sincronizado(preparado, horizonte=6)
    y_treino = split.treino["risco_futuro_label"].to_numpy()

    majoritaria = baseline_majoritaria(y_treino, len(split.teste))
    persistencia = previsao_persistencia_risco(split.teste)

    assert set(majoritaria) == {int(np.bincount(y_treino).argmax())}
    esperado = split.teste["risco"].map(
        {classe: indice for indice, classe in enumerate(CLASSES_RISCO)}
    )
    assert persistencia.tolist() == esperado.tolist()


def test_metricas_previsao_comparam_modelo_e_persistencia_por_horizonte() -> None:
    real = np.array([[10.0, 12.0], [20.0, 22.0]])
    previsto = np.array([[11.0, 11.0], [19.0, 24.0]])
    persistencia = np.array([[9.0, 9.0], [21.0, 21.0]])

    metricas = metricas_previsao(real, previsto, persistencia)

    assert metricas["mae_mw"] == 1.25
    assert metricas["baseline_persistencia"]["mae_mw"] == 1.5
    assert metricas["mae_por_horizonte_mw"] == [1.0, 1.5]
    assert metricas["supera_persistencia_mae"] is True
