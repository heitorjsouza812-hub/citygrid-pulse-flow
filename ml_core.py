"""Funções puras para preparar e avaliar os experimentos do CityGrid Brain.

Este módulo não treina modelos no import. Ele centraliza as regras que precisam
ser testadas para impedir vazamento temporal e métricas enganosas.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Sequence

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)

CLASSES_RISCO: tuple[str, ...] = ("ALTO", "BAIXO", "CRÍTICO", "MÉDIO")
MAPA_RISCO = {classe: indice for indice, classe in enumerate(CLASSES_RISCO)}

FEATURES_XGB: tuple[str, ...] = (
    "pct_carga",
    "consumo_mw",
    "consumo_liquido_mw",
    "clima_temp_c",
    "clima_irrad_wm2",
    "clima_umidade_pct",
    "hora",
    "hora_sin",
    "hora_cos",
    "dia_semana",
    "thd_tensao_pct",
    "fator_potencia",
    "desequilibrio_tensao_pct",
    "frequencia_hz",
    "tensao_media_v",
    "pot_ativa_kw",
    "pot_reativa_kvar",
    "ve_demanda_kw",
    "ve_ocupacao_pct",
    "bat_soc_pct",
    "geracao_total_mw",
    "autoprod_pct",
    "anomalia_flag",
    "evento_flag",
)


@dataclass(frozen=True)
class SplitTemporal:
    treino: pd.DataFrame
    validacao: pd.DataFrame
    teste: pd.DataFrame
    ciclos_descartados: tuple[int, ...]

    def metadados(self) -> dict:
        resultado: dict[str, object] = {
            "ciclos_descartados_embargo": list(self.ciclos_descartados),
        }
        for nome, frame in (
            ("treino", self.treino),
            ("validacao", self.validacao),
            ("teste", self.teste),
        ):
            ciclos = sorted(int(v) for v in frame["ciclo"].unique())
            timestamps = pd.to_datetime(frame["timestamp"])
            resultado[nome] = {
                "linhas": int(len(frame)),
                "ciclos": int(len(ciclos)),
                "ciclo_inicial": ciclos[0],
                "ciclo_final": ciclos[-1],
                "timestamp_inicial": timestamps.min().isoformat(),
                "timestamp_final": timestamps.max().isoformat(),
                "sha256_ciclos": sha256(
                    ",".join(map(str, ciclos)).encode("utf-8")
                ).hexdigest(),
            }
        return resultado


def preparar_dataset_xgb(df: pd.DataFrame, horizonte: int = 6) -> pd.DataFrame:
    """Cria features e o alvo futuro, preservando o ciclo do alvo.

    O deslocamento é feito dentro de cada zona. ``ciclo_alvo`` permite provar
    que nenhuma amostra de treino usa um rótulo pertencente ao período de
    validação ou teste.
    """
    obrigatorias = {"zona_id", "timestamp", "ciclo", "risco"}
    ausentes = obrigatorias.difference(df.columns)
    if ausentes:
        raise ValueError(f"Colunas obrigatórias ausentes: {sorted(ausentes)}")
    if horizonte < 1:
        raise ValueError("horizonte deve ser maior que zero")

    preparado = df.copy()
    preparado["timestamp"] = pd.to_datetime(preparado["timestamp"], errors="raise")
    preparado = preparado.sort_values(["zona_id", "ciclo", "timestamp"]).reset_index(drop=True)
    preparado["hora"] = preparado["timestamp"].dt.hour
    preparado["dia_semana"] = preparado["timestamp"].dt.dayofweek
    preparado["hora_sin"] = np.sin(2 * np.pi * preparado["hora"] / 24)
    preparado["hora_cos"] = np.cos(2 * np.pi * preparado["hora"] / 24)
    preparado["evento_flag"] = preparado.get(
        "evento", pd.Series(index=preparado.index, dtype=object)
    ).notna().astype(int)
    preparado["anomalia_flag"] = preparado.get(
        "anomalia_tipo", pd.Series(index=preparado.index, dtype=object)
    ).notna().astype(int)

    por_zona = preparado.groupby("zona_id", sort=False)
    preparado["risco_futuro"] = por_zona["risco"].shift(-horizonte)
    preparado["ciclo_alvo"] = por_zona["ciclo"].shift(-horizonte)
    preparado = preparado.dropna(subset=["risco_futuro", "ciclo_alvo"]).copy()
    preparado["ciclo"] = preparado["ciclo"].astype(int)
    preparado["ciclo_alvo"] = preparado["ciclo_alvo"].astype(int)

    classes_invalidas = set(preparado["risco_futuro"].unique()).difference(CLASSES_RISCO)
    if classes_invalidas:
        raise ValueError(f"Classes de risco desconhecidas: {sorted(classes_invalidas)}")
    preparado["risco_futuro_label"] = preparado["risco_futuro"].map(MAPA_RISCO).astype(int)

    for coluna in FEATURES_XGB:
        if coluna not in preparado:
            preparado[coluna] = 0.0
    preparado[list(FEATURES_XGB)] = (
        preparado[list(FEATURES_XGB)].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    )
    return preparado.sort_values(["ciclo", "zona_id"]).reset_index(drop=True)


def split_temporal_sincronizado(
    df: pd.DataFrame,
    horizonte: int = 6,
    proporcao_treino: float = 0.70,
    proporcao_validacao: float = 0.15,
) -> SplitTemporal:
    """Divide por ciclos globais e aplica embargo igual ao horizonte.

    Todas as zonas de um ciclo permanecem no mesmo conjunto. Os últimos
    ``horizonte`` ciclos antes de cada fronteira são descartados, impedindo que
    o rótulo futuro de um conjunto alcance o conjunto seguinte.
    """
    if not 0 < proporcao_treino < 1:
        raise ValueError("proporcao_treino inválida")
    if not 0 < proporcao_validacao < 1 - proporcao_treino:
        raise ValueError("proporcao_validacao inválida")
    if horizonte < 1:
        raise ValueError("horizonte deve ser maior que zero")

    ciclos = np.array(sorted(int(v) for v in df["ciclo"].unique()), dtype=int)
    minimo = 3 * (horizonte + 1)
    if len(ciclos) < minimo:
        raise ValueError(
            f"São necessários ao menos {minimo} ciclos para três conjuntos com embargo"
        )

    corte_treino = int(len(ciclos) * proporcao_treino)
    corte_teste = int(len(ciclos) * (proporcao_treino + proporcao_validacao))
    fim_treino = corte_treino - horizonte
    fim_validacao = corte_teste - horizonte
    if fim_treino <= 0 or fim_validacao <= corte_treino or corte_teste >= len(ciclos):
        raise ValueError("Divisão temporal não comporta o embargo solicitado")

    ciclos_treino = ciclos[:fim_treino]
    ciclos_validacao = ciclos[corte_treino:fim_validacao]
    ciclos_teste = ciclos[corte_teste:]
    descartados = np.concatenate(
        (ciclos[fim_treino:corte_treino], ciclos[fim_validacao:corte_teste])
    )

    def selecionar(valores: np.ndarray) -> pd.DataFrame:
        return df[df["ciclo"].isin(valores)].sort_values(["ciclo", "zona_id"]).reset_index(drop=True)

    split = SplitTemporal(
        treino=selecionar(ciclos_treino),
        validacao=selecionar(ciclos_validacao),
        teste=selecionar(ciclos_teste),
        ciclos_descartados=tuple(int(v) for v in descartados),
    )
    if split.treino.empty or split.validacao.empty or split.teste.empty:
        raise ValueError("Um dos conjuntos ficou vazio")
    if split.treino["ciclo_alvo"].max() >= split.validacao["ciclo"].min():
        raise AssertionError("Rótulos do treino atravessam a fronteira da validação")
    if split.validacao["ciclo_alvo"].max() >= split.teste["ciclo"].min():
        raise AssertionError("Rótulos da validação atravessam a fronteira do teste")
    return split


def calcular_pesos_classes(y_treino: np.ndarray, n_classes: int) -> np.ndarray:
    """Retorna sample weights usando exclusivamente a distribuição de treino."""
    y = np.asarray(y_treino, dtype=int)
    if y.ndim != 1 or y.size == 0:
        raise ValueError("y_treino deve ser um vetor não vazio")
    contagens = np.bincount(y, minlength=n_classes)
    pesos_por_classe = np.zeros(n_classes, dtype=float)
    presentes = contagens > 0
    pesos_por_classe[presentes] = y.size / (presentes.sum() * contagens[presentes])
    return pesos_por_classe[y]


def baseline_majoritaria(y_treino: np.ndarray, tamanho: int) -> np.ndarray:
    """Prediz no conjunto futuro apenas a classe mais frequente do treino."""
    y = np.asarray(y_treino, dtype=int)
    if y.size == 0:
        raise ValueError("y_treino não pode estar vazio")
    if tamanho < 0:
        raise ValueError("tamanho não pode ser negativo")
    classe = int(np.bincount(y).argmax())
    return np.full(tamanho, classe, dtype=int)


def previsao_persistencia_risco(frame: pd.DataFrame) -> np.ndarray:
    """Baseline temporal: assume que o risco futuro permanecerá igual ao atual."""
    if "risco" not in frame:
        raise ValueError("A coluna risco é necessária para a baseline de persistência")
    resultado = frame["risco"].map(MAPA_RISCO)
    if resultado.isna().any():
        invalidas = sorted(frame.loc[resultado.isna(), "risco"].unique())
        raise ValueError(f"Classes de risco desconhecidas: {invalidas}")
    return resultado.to_numpy(dtype=int)


def metricas_previsao(
    real: np.ndarray,
    previsto: np.ndarray,
    persistencia: np.ndarray,
) -> dict:
    """Compara uma previsão multihorizonte à baseline de último valor."""
    y = np.asarray(real, dtype=float)
    pred = np.asarray(previsto, dtype=float)
    base = np.asarray(persistencia, dtype=float)
    if y.shape != pred.shape or y.shape != base.shape or y.ndim != 2:
        raise ValueError("real, previsto e persistencia devem ter a mesma forma 2D")

    def resumo(valores: np.ndarray) -> dict:
        erro = y - valores
        return {
            "mae_mw": float(np.mean(np.abs(erro))),
            "rmse_mw": float(np.sqrt(np.mean(np.square(erro)))),
        }

    modelo = resumo(pred)
    baseline = resumo(base)
    return {
        **modelo,
        "mae_por_horizonte_mw": [
            float(np.mean(np.abs(y[:, passo] - pred[:, passo])))
            for passo in range(y.shape[1])
        ],
        "baseline_persistencia": {
            **baseline,
            "mae_por_horizonte_mw": [
                float(np.mean(np.abs(y[:, passo] - base[:, passo])))
                for passo in range(y.shape[1])
            ],
        },
        "supera_persistencia_mae": bool(modelo["mae_mw"] < baseline["mae_mw"]),
    }


def metricas_classificacao(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    classes: Sequence[str] = CLASSES_RISCO,
) -> dict:
    """Calcula métricas que não escondem falhas nas classes minoritárias."""
    labels = list(range(len(classes)))
    relatorio = classification_report(
        y_true,
        y_pred,
        labels=labels,
        target_names=list(classes),
        output_dict=True,
        zero_division=0,
    )
    por_classe = {
        classe: {
            "precision": float(relatorio[classe]["precision"]),
            "recall": float(relatorio[classe]["recall"]),
            "f1": float(relatorio[classe]["f1-score"]),
            "suporte": int(relatorio[classe]["support"]),
        }
        for classe in classes
    }
    return {
        "acuracia": float(accuracy_score(y_true, y_pred)),
        "acuracia_balanceada": float(balanced_accuracy_score(y_true, y_pred)),
        "f1_macro": float(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)),
        "f1_ponderado": float(
            f1_score(y_true, y_pred, labels=labels, average="weighted", zero_division=0)
        ),
        "matriz_confusao": confusion_matrix(y_true, y_pred, labels=labels).astype(int).tolist(),
        "por_classe": por_classe,
    }
