"""Treinamento reproduzível do CityGrid Brain.

O experimento usa dados sintéticos, três períodos temporais sincronizados entre
zonas e um embargo de seis ciclos nas fronteiras. O conjunto de teste não é
usado para early stopping, pesos de classe ou escolha de hiperparâmetros.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pickle
import platform
import random
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import sklearn
import torch
import torch.nn as nn
import xgboost as xgb
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset

from ml_core import (
    CLASSES_RISCO,
    FEATURES_XGB,
    baseline_majoritaria,
    calcular_pesos_classes,
    metricas_classificacao,
    metricas_previsao,
    preparar_dataset_xgb,
    previsao_persistencia_risco,
    split_temporal_sincronizado,
)

ARQUIVO_CSV = Path("dados_turbo.csv")
PASTA_MODELOS = Path("modelos")
PASTA_GRAFICOS = Path("graficos")
JANELA_LSTM = 24
HORIZONTE_LSTM = 6
BATCH_SIZE = 64
SEED = 42
FEATURES_LSTM = (
    "consumo_mw",
    "pct_carga",
    "clima_temp_c",
    "clima_irrad_wm2",
    "hora_sin",
    "hora_cos",
    "evento_flag",
    "anomalia_flag",
    "geracao_total_mw",
)
TARGET_LSTM = "consumo_mw"


class LSTMConsumo(nn.Module):
    """Mesma arquitetura carregada por backend.py e motor_decisao.py."""

    def __init__(
        self,
        n_features: int = len(FEATURES_LSTM),
        hidden: int = 64,
        n_layers: int = 2,
        horizonte: int = HORIZONTE_LSTM,
        dropout: float = 0.2,
    ) -> None:
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=n_features,
            hidden_size=hidden,
            num_layers=n_layers,
            batch_first=True,
            dropout=dropout if n_layers > 1 else 0,
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, horizonte),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])


def configurar_reprodutibilidade(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    try:
        torch.use_deterministic_algorithms(True, warn_only=True)
    except AttributeError:
        pass


def sha256_arquivo(caminho: Path) -> str:
    digest = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            digest.update(bloco)
    return digest.hexdigest()


def distribuicao(frame: pd.DataFrame) -> dict[str, int]:
    contagens = frame["risco_futuro"].value_counts()
    return {classe: int(contagens.get(classe, 0)) for classe in CLASSES_RISCO}


def treinar_xgboost(split) -> tuple[xgb.XGBClassifier, dict]:
    X_treino = split.treino[list(FEATURES_XGB)].to_numpy(dtype=float)
    y_treino = split.treino["risco_futuro_label"].to_numpy(dtype=int)
    X_validacao = split.validacao[list(FEATURES_XGB)].to_numpy(dtype=float)
    y_validacao = split.validacao["risco_futuro_label"].to_numpy(dtype=int)
    X_teste = split.teste[list(FEATURES_XGB)].to_numpy(dtype=float)
    y_teste = split.teste["risco_futuro_label"].to_numpy(dtype=int)

    modelo = xgb.XGBClassifier(
        objective="multi:softprob",
        num_class=len(CLASSES_RISCO),
        n_estimators=600,
        max_depth=6,
        learning_rate=0.04,
        min_child_weight=2,
        subsample=0.85,
        colsample_bytree=0.85,
        reg_lambda=1.0,
        reg_alpha=0.05,
        eval_metric="mlogloss",
        early_stopping_rounds=30,
        random_state=SEED,
        n_jobs=max(1, (os.cpu_count() or 2) - 1),
    )
    pesos = calcular_pesos_classes(y_treino, len(CLASSES_RISCO))
    modelo.fit(
        X_treino,
        y_treino,
        sample_weight=pesos,
        eval_set=[(X_validacao, y_validacao)],
        verbose=False,
    )

    pred_validacao = modelo.predict(X_validacao)
    pred_teste = modelo.predict(X_teste)
    pred_majoritaria = baseline_majoritaria(y_treino, len(y_teste))
    pred_persistencia = previsao_persistencia_risco(split.teste)

    metricas = {
        "validacao": metricas_classificacao(y_validacao, pred_validacao),
        "teste": metricas_classificacao(y_teste, pred_teste),
        "baselines_teste": {
            "classe_majoritaria_treino": metricas_classificacao(y_teste, pred_majoritaria),
            "persistencia_risco_atual": metricas_classificacao(y_teste, pred_persistencia),
        },
        "melhor_iteracao_validacao": int(getattr(modelo, "best_iteration", 599)),
    }
    metricas["conclusao"] = {
        "supera_majoritaria_f1_macro": bool(
            metricas["teste"]["f1_macro"]
            > metricas["baselines_teste"]["classe_majoritaria_treino"]["f1_macro"]
        ),
        "supera_persistencia_f1_macro": bool(
            metricas["teste"]["f1_macro"]
            > metricas["baselines_teste"]["persistencia_risco_atual"]["f1_macro"]
        ),
        "recall_critico": metricas["teste"]["por_classe"]["CRÍTICO"]["recall"],
    }
    modelo.save_model(PASTA_MODELOS / "xgboost_risco.json")
    gerar_grafico_xgboost(modelo, y_teste, pred_teste, metricas)
    return modelo, metricas


def gerar_grafico_xgboost(
    modelo: xgb.XGBClassifier,
    y_teste: np.ndarray,
    pred_teste: np.ndarray,
    metricas: dict,
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.5))
    teste = metricas["teste"]
    fig.suptitle(
        "XGBoost — avaliação no teste temporal intocado\n"
        f"F1 macro={teste['f1_macro']:.3f} | "
        f"acurácia balanceada={teste['acuracia_balanceada']:.3f}",
        fontsize=13,
        fontweight="bold",
    )
    sns.heatmap(
        np.asarray(teste["matriz_confusao"]),
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=CLASSES_RISCO,
        yticklabels=CLASSES_RISCO,
        ax=axes[0],
    )
    axes[0].set_title("Matriz de confusão")
    axes[0].set_xlabel("Predito")
    axes[0].set_ylabel("Real")

    importancias = pd.Series(modelo.feature_importances_, index=FEATURES_XGB)
    importancias.nlargest(12).sort_values().plot(kind="barh", ax=axes[1], color="steelblue")
    axes[1].set_title("Importância interna do XGBoost")
    axes[1].set_xlabel("Ganho relativo")
    plt.tight_layout()
    plt.savefig(PASTA_GRAFICOS / "xgboost_resultados.png", dpi=160, bbox_inches="tight")
    plt.close()


def gerar_shap(modelo: xgb.XGBClassifier, frame_teste: pd.DataFrame) -> bool:
    try:
        import shap

        amostra = frame_teste[list(FEATURES_XGB)].head(500).to_numpy(dtype=float)
        explainer = shap.TreeExplainer(modelo)
        valores = np.asarray(explainer.shap_values(amostra))
        if valores.ndim == 3 and valores.shape[1] == len(FEATURES_XGB):
            medias = np.abs(valores).mean(axis=(0, 2))
        elif valores.ndim == 3:
            medias = np.abs(valores).mean(axis=(0, 1))
        else:
            medias = np.abs(valores).reshape(-1, len(FEATURES_XGB)).mean(axis=0)
        tabela = pd.DataFrame({"feature": FEATURES_XGB, "shap_mean_abs": medias})
        tabela = tabela.sort_values("shap_mean_abs", ascending=False)
        tabela.to_csv(PASTA_GRAFICOS / "shap_importancias.csv", index=False)
        fig, ax = plt.subplots(figsize=(10, 6))
        top = tabela.head(15).iloc[::-1]
        ax.barh(top["feature"], top["shap_mean_abs"], color="steelblue")
        ax.set_title("SHAP global — impacto médio absoluto no teste")
        ax.set_xlabel("|SHAP| médio")
        ax.grid(axis="x", alpha=0.3)
        plt.tight_layout()
        plt.savefig(PASTA_GRAFICOS / "shap_xgboost.png", dpi=160, bbox_inches="tight")
        plt.close()
        return True
    except Exception as exc:  # SHAP é opcional e não invalida as métricas centrais
        print(f"  [AVISO] SHAP não foi gerado: {exc}")
        return False


def criar_janelas_lstm(
    frame: pd.DataFrame,
    scaler_x: StandardScaler,
    scaler_y: StandardScaler,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    ordenado = frame.sort_values("ciclo")
    features = scaler_x.transform(ordenado[list(FEATURES_LSTM)].to_numpy(dtype=float))
    alvo_real = ordenado[TARGET_LSTM].to_numpy(dtype=float)
    alvo_norm = scaler_y.transform(alvo_real.reshape(-1, 1)).ravel()
    entradas: list[np.ndarray] = []
    alvos: list[np.ndarray] = []
    persistencias: list[np.ndarray] = []
    limite = len(ordenado) - JANELA_LSTM - HORIZONTE_LSTM + 1
    for indice in range(max(0, limite)):
        entradas.append(features[indice : indice + JANELA_LSTM])
        alvos.append(
            alvo_norm[
                indice + JANELA_LSTM : indice + JANELA_LSTM + HORIZONTE_LSTM
            ]
        )
        ultimo = alvo_real[indice + JANELA_LSTM - 1]
        persistencias.append(np.repeat(ultimo, HORIZONTE_LSTM))
    return np.asarray(entradas), np.asarray(alvos), np.asarray(persistencias)


def treinar_lstm_zona(
    zona_id: str,
    treino: pd.DataFrame,
    validacao: pd.DataFrame,
    teste: pd.DataFrame,
    epochs: int,
) -> dict | None:
    if min(len(treino), len(validacao), len(teste)) < JANELA_LSTM + HORIZONTE_LSTM + 5:
        return None

    scaler_x = StandardScaler().fit(treino[list(FEATURES_LSTM)].to_numpy(dtype=float))
    scaler_y = StandardScaler().fit(treino[[TARGET_LSTM]].to_numpy(dtype=float))
    X_tr, y_tr, _ = criar_janelas_lstm(treino, scaler_x, scaler_y)
    X_val, y_val, _ = criar_janelas_lstm(validacao, scaler_x, scaler_y)
    X_te, y_te, persistencia_te = criar_janelas_lstm(teste, scaler_x, scaler_y)
    if min(len(X_tr), len(X_val), len(X_te)) == 0:
        return None

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    modelo = LSTMConsumo().to(device)
    gerador = torch.Generator().manual_seed(SEED)
    loader = DataLoader(
        TensorDataset(torch.tensor(X_tr, dtype=torch.float32), torch.tensor(y_tr, dtype=torch.float32)),
        batch_size=BATCH_SIZE,
        shuffle=True,
        generator=gerador,
    )
    X_validacao = torch.tensor(X_val, dtype=torch.float32, device=device)
    y_validacao = torch.tensor(y_val, dtype=torch.float32, device=device)
    otimizador = torch.optim.Adam(modelo.parameters(), lr=0.001, weight_decay=1e-5)
    criterio = nn.MSELoss()
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        otimizador, patience=4, factor=0.5
    )

    melhor_loss = float("inf")
    melhor_estado: dict[str, torch.Tensor] | None = None
    paciencia = 0
    historico_treino: list[float] = []
    historico_validacao: list[float] = []

    for _ in range(epochs):
        modelo.train()
        perdas = []
        for xb, yb in loader:
            xb = xb.to(device)
            yb = yb.to(device)
            otimizador.zero_grad()
            perda = criterio(modelo(xb), yb)
            perda.backward()
            nn.utils.clip_grad_norm_(modelo.parameters(), 1.0)
            otimizador.step()
            perdas.append(float(perda.item()))
        perda_treino = float(np.mean(perdas))
        modelo.eval()
        with torch.no_grad():
            perda_validacao = float(criterio(modelo(X_validacao), y_validacao).item())
        historico_treino.append(perda_treino)
        historico_validacao.append(perda_validacao)
        scheduler.step(perda_validacao)

        if perda_validacao < melhor_loss - 1e-6:
            melhor_loss = perda_validacao
            melhor_estado = {
                chave: valor.detach().cpu().clone()
                for chave, valor in modelo.state_dict().items()
            }
            paciencia = 0
        else:
            paciencia += 1
            if paciencia >= 10:
                break

    if melhor_estado is None:
        return None
    modelo.load_state_dict(melhor_estado)
    modelo.to(device).eval()
    X_teste = torch.tensor(X_te, dtype=torch.float32, device=device)
    with torch.no_grad():
        previsto_norm = modelo(X_teste).cpu().numpy()
    previsto_real = scaler_y.inverse_transform(previsto_norm)
    real = scaler_y.inverse_transform(y_te)
    metricas = metricas_previsao(real, previsto_real, persistencia_te)

    torch.save(modelo.state_dict(), PASTA_MODELOS / f"lstm_{zona_id}.pt")
    with (PASTA_MODELOS / f"scaler_{zona_id}.pkl").open("wb") as arquivo:
        pickle.dump({"sx": scaler_x, "sy": scaler_y}, arquivo)

    return {
        "zona_id": zona_id,
        "epocas": len(historico_treino),
        "melhor_loss_validacao": melhor_loss,
        "metricas_teste": metricas,
        "historico_treino": historico_treino,
        "historico_validacao": historico_validacao,
        "real": real,
        "previsto": previsto_real,
    }


def treinar_lstms(split, epochs: int) -> dict[str, dict]:
    resultados: dict[str, dict] = {}
    zonas = sorted(split.treino["zona_id"].unique())
    for zona_id in zonas:
        print(f"  LSTM {zona_id}...", end=" ", flush=True)
        resultado = treinar_lstm_zona(
            zona_id,
            split.treino[split.treino["zona_id"] == zona_id],
            split.validacao[split.validacao["zona_id"] == zona_id],
            split.teste[split.teste["zona_id"] == zona_id],
            epochs,
        )
        if resultado is None:
            print("dados insuficientes")
            continue
        resultados[zona_id] = resultado
        m = resultado["metricas_teste"]
        print(
            f"MAE={m['mae_mw']:.3f} MW | "
            f"persistência={m['baseline_persistencia']['mae_mw']:.3f} MW | "
            f"épocas={resultado['epocas']}"
        )
    gerar_graficos_lstm(resultados)
    return resultados


def gerar_graficos_lstm(resultados: dict[str, dict]) -> None:
    if not resultados:
        return
    zonas = list(resultados)
    colunas = 4
    linhas = (len(zonas) + colunas - 1) // colunas

    fig, axes = plt.subplots(linhas, colunas, figsize=(18, 4 * linhas), squeeze=False)
    fig.suptitle("LSTM — loss de treino e validação (teste não usado)", fontweight="bold")
    for ax, zona in zip(axes.ravel(), zonas):
        resultado = resultados[zona]
        ax.plot(resultado["historico_treino"], label="Treino")
        ax.plot(resultado["historico_validacao"], label="Validação")
        ax.set_title(zona)
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
    for ax in axes.ravel()[len(zonas) :]:
        ax.set_visible(False)
    plt.tight_layout()
    plt.savefig(PASTA_GRAFICOS / "lstm_loss_por_zona.png", dpi=160, bbox_inches="tight")
    plt.close()

    fig, axes = plt.subplots(linhas, colunas, figsize=(18, 4 * linhas), squeeze=False)
    fig.suptitle("LSTM — primeiro horizonte no teste temporal", fontweight="bold")
    for ax, zona in zip(axes.ravel(), zonas):
        resultado = resultados[zona]
        n = min(120, len(resultado["real"]))
        ax.plot(resultado["real"][:n, 0], label="Real")
        ax.plot(resultado["previsto"][:n, 0], label="LSTM", linestyle="--")
        ax.set_title(zona)
        ax.set_ylabel("MW")
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
    for ax in axes.ravel()[len(zonas) :]:
        ax.set_visible(False)
    plt.tight_layout()
    plt.savefig(PASTA_GRAFICOS / "lstm_real_vs_predito.png", dpi=160, bbox_inches="tight")
    plt.close()

    maes = [resultados[z]["metricas_teste"]["mae_mw"] for z in zonas]
    baselines = [
        resultados[z]["metricas_teste"]["baseline_persistencia"]["mae_mw"]
        for z in zonas
    ]
    x = np.arange(len(zonas))
    largura = 0.38
    fig, ax = plt.subplots(figsize=(14, 5.5))
    ax.bar(x - largura / 2, maes, largura, label="LSTM")
    ax.bar(x + largura / 2, baselines, largura, label="Persistência")
    ax.set_xticks(x, [z.replace("zona_", "") for z in zonas], rotation=25)
    ax.set_ylabel("MAE no teste (MW) — menor é melhor")
    ax.set_title("LSTM vs baseline de último valor por zona")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(PASTA_GRAFICOS / "lstm_comparativo_zonas.png", dpi=160, bbox_inches="tight")
    plt.close()


def gerar_comparativo_final(metricas_xgb: dict, resultados_lstm: dict[str, dict]) -> None:
    teste = metricas_xgb["teste"]
    bases = metricas_xgb["baselines_teste"]
    nomes = ["XGBoost", "Majoritária", "Persistência"]
    f1s = [
        teste["f1_macro"],
        bases["classe_majoritaria_treino"]["f1_macro"],
        bases["persistencia_risco_atual"]["f1_macro"],
    ]
    balanceadas = [
        teste["acuracia_balanceada"],
        bases["classe_majoritaria_treino"]["acuracia_balanceada"],
        bases["persistencia_risco_atual"]["acuracia_balanceada"],
    ]
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    x = np.arange(len(nomes))
    axes[0].bar(x - 0.18, f1s, 0.36, label="F1 macro")
    axes[0].bar(x + 0.18, balanceadas, 0.36, label="Acurácia balanceada")
    axes[0].set_xticks(x, nomes)
    axes[0].set_ylim(0, 1)
    axes[0].set_title("Classificação de risco — teste")
    axes[0].legend()
    axes[0].grid(axis="y", alpha=0.3)

    if resultados_lstm:
        mae_modelo = np.mean(
            [r["metricas_teste"]["mae_mw"] for r in resultados_lstm.values()]
        )
        mae_base = np.mean(
            [
                r["metricas_teste"]["baseline_persistencia"]["mae_mw"]
                for r in resultados_lstm.values()
            ]
        )
        axes[1].bar(["LSTM", "Persistência"], [mae_modelo, mae_base], color=["steelblue", "gray"])
        axes[1].set_ylabel("MAE médio (MW) — menor é melhor")
        axes[1].set_title("Previsão de consumo — teste")
        axes[1].grid(axis="y", alpha=0.3)
    else:
        axes[1].text(0.5, 0.5, "LSTM não avaliado", ha="center", va="center")
        axes[1].set_axis_off()
    fig.suptitle("Resultados medidos e baselines — sem híbrido estimado", fontweight="bold")
    plt.tight_layout()
    plt.savefig(PASTA_GRAFICOS / "comparativo_final.png", dpi=160, bbox_inches="tight")
    plt.close()


def serializar_resultados_lstm(resultados: dict[str, dict]) -> dict:
    return {
        zona: {
            "epocas": resultado["epocas"],
            "melhor_loss_validacao": resultado["melhor_loss_validacao"],
            "metricas_teste": resultado["metricas_teste"],
        }
        for zona, resultado in resultados.items()
    }


def limpar_artefatos_sem_proveniencia() -> None:
    obsoletos = (
        PASTA_GRAFICOS / "ablation_study.png",
        PASTA_GRAFICOS / "comparativo_modelos.png",
        PASTA_GRAFICOS / "lstm_resultados.png",
        PASTA_MODELOS / "lstm_consumo_melhor.pt",
    )
    for caminho in obsoletos:
        caminho.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Treina e avalia o CityGrid Brain")
    parser.add_argument("--dados", type=Path, default=ARQUIVO_CSV)
    parser.add_argument("--epochs-lstm", type=int, default=60)
    parser.add_argument("--sem-shap", action="store_true")
    args = parser.parse_args()

    configurar_reprodutibilidade(SEED)
    PASTA_MODELOS.mkdir(exist_ok=True)
    PASTA_GRAFICOS.mkdir(exist_ok=True)
    limpar_artefatos_sem_proveniencia()

    print("=" * 72)
    print("CITYGRID BRAIN — EXPERIMENTO REPRODUZÍVEL")
    print("Dados sintéticos | treino/validação/teste temporal | embargo de 6 ciclos")
    print("=" * 72)
    bruto = pd.read_csv(args.dados)
    preparado = preparar_dataset_xgb(bruto, HORIZONTE_LSTM)
    split = split_temporal_sincronizado(preparado, HORIZONTE_LSTM)
    meta_split = split.metadados()
    for nome in ("treino", "validacao", "teste"):
        print(f"  {nome:10s}: {meta_split[nome]['linhas']:,} linhas | "
              f"ciclos {meta_split[nome]['ciclo_inicial']}–{meta_split[nome]['ciclo_final']}")

    print("\nTreinando XGBoost com pesos calculados somente no treino...")
    modelo_xgb, metricas_xgb = treinar_xgboost(split)
    teste = metricas_xgb["teste"]
    print(
        f"  Teste: F1 macro={teste['f1_macro']:.3f} | "
        f"balanceada={teste['acuracia_balanceada']:.3f} | "
        f"recall CRÍTICO={teste['por_classe']['CRÍTICO']['recall']:.3f}"
    )
    shap_gerado = False if args.sem_shap else gerar_shap(modelo_xgb, split.teste)

    print("\nTreinando LSTMs com early stopping somente na validação...")
    resultados_lstm = treinar_lstms(split, args.epochs_lstm)
    gerar_comparativo_final(metricas_xgb, resultados_lstm)

    proveniencia = {
        "experimento": "CityGrid Brain — avaliação temporal reproduzível",
        "gerado_em_utc": datetime.now(timezone.utc).isoformat(),
        "seed": SEED,
        "dados": {
            "arquivo": str(args.dados),
            "sha256": sha256_arquivo(args.dados),
            "linhas_brutas": int(len(bruto)),
            "tipo": "sintético",
            "intervalo_simulado_minutos": 5,
        },
        "ambiente": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__,
            "xgboost": xgb.__version__,
            "torch": torch.__version__,
        },
        "protocolo": {
            "horizonte_ciclos": HORIZONTE_LSTM,
            "horizonte_minutos": HORIZONTE_LSTM * 5,
            "janela_lstm_ciclos": JANELA_LSTM,
            "proporcoes_nominais": {"treino": 0.70, "validacao": 0.15, "teste": 0.15},
            "embargo_ciclos_em_cada_fronteira": HORIZONTE_LSTM,
            "teste_usado_para_ajuste": False,
            "split": meta_split,
            "distribuicao_alvo": {
                "treino": distribuicao(split.treino),
                "validacao": distribuicao(split.validacao),
                "teste": distribuicao(split.teste),
            },
        },
        "xgboost": metricas_xgb,
        "lstm_por_zona": serializar_resultados_lstm(resultados_lstm),
        "shap_global_gerado": shap_gerado,
        "ablation_hibrido": {
            "executado": False,
            "motivo": "Não existe experimento conjunto alinhado; nenhuma métrica híbrida foi estimada.",
        },
        "limitacoes": [
            "Os dados são integralmente sintéticos e não provam desempenho em uma rede real.",
            "Uma única geração sintética não demonstra generalização para outras cidades.",
            "As saídas do motor são recomendações simuladas; não existem atuadores reais.",
            "Economia de energia causada pela IA não foi medida contra um cenário contrafactual.",
        ],
    }
    caminho_metricas = PASTA_GRAFICOS / "metricas_experimento.json"
    caminho_metricas.write_text(
        json.dumps(proveniencia, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nMétricas e proveniência: {caminho_metricas}")
    print("Nenhuma métrica híbrida estimada foi produzida.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
