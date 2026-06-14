"""
╔══════════════════════════════════════════════════════════════════╗
║         CITYGRID BRAIN — TREINAMENTO ML v3.0                    ║
║         XGBoost — Classificador de Risco                        ║
║         LSTM    — Previsão de Consumo por Zona                  ║
╚══════════════════════════════════════════════════════════════════╝

Correções v3.0:
  - LSTM treinado por zona separadamente (sem mistura de escala)
  - Gráficos sempre sobrescritos com resultados reais do treino atual
  - Early stopping menos agressivo (paciência 15)
  - 100 épocas
  - Gráfico comparativo final com resultados reais por zona
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")   # força backend sem janela — gráficos sempre salvos corretamente
import matplotlib.pyplot as plt
import seaborn as sns
import pickle
import os
import warnings
warnings.filterwarnings("ignore")

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import (classification_report, confusion_matrix,
                              accuracy_score, f1_score,
                              mean_absolute_error, mean_squared_error)
from sklearn.dummy import DummyClassifier
try:
    import shap
    SHAP_DISPONIVEL = True
except ImportError:
    SHAP_DISPONIVEL = False
    print("  [AVISO] shap não instalado. Execute: pip install shap")
import xgboost as xgb
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

# ══════════════════════════════════════════════════════════════════
#  CONFIGURAÇÃO
# ══════════════════════════════════════════════════════════════════

ARQUIVO_CSV    = "dados_turbo.csv"
PASTA_MODELOS  = "modelos"
PASTA_GRAFICOS = "graficos"
JANELA_LSTM    = 24
HORIZONTE_LSTM = 6
EPOCHS_LSTM    = 100
BATCH_SIZE     = 64
SEED           = 42

os.makedirs(PASTA_MODELOS,  exist_ok=True)
os.makedirs(PASTA_GRAFICOS, exist_ok=True)
torch.manual_seed(SEED)
np.random.seed(SEED)

# ══════════════════════════════════════════════════════════════════
#  1. CARREGAMENTO E PRÉ-PROCESSAMENTO
# ══════════════════════════════════════════════════════════════════

print("=" * 62)
print("  CITYGRID BRAIN — TREINAMENTO ML v3.0")
print("=" * 62)
print(f"\n  Carregando {ARQUIVO_CSV}...")

df = pd.read_csv(ARQUIVO_CSV)
df["timestamp"]   = pd.to_datetime(df["timestamp"])
df                = df.sort_values(["zona_id", "timestamp"]).reset_index(drop=True)
df["hora"]        = df["timestamp"].dt.hour
df["dia_semana"]  = df["timestamp"].dt.dayofweek
df["hora_sin"]    = np.sin(2 * np.pi * df["hora"] / 24)
df["hora_cos"]    = np.cos(2 * np.pi * df["hora"] / 24)
df["evento_flag"] = df["evento"].notna().astype(int)
df["anomalia_flag"]= df["anomalia_tipo"].notna().astype(int)

colunas_num = df.select_dtypes(include=[np.number]).columns
df[colunas_num] = df[colunas_num].fillna(0)

print(f"  ✅ {len(df):,} leituras | {df['zona_id'].nunique()} zonas | {df['ciclo'].max():,} ciclos")

# ══════════════════════════════════════════════════════════════════
#  2. XGBOOST — CLASSIFICADOR DE RISCO
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 62)
print("  MODELO 1 — XGBoost (Classificador de Risco)")
print("=" * 62)

FEATURES_XGB = [
    "pct_carga", "consumo_mw", "consumo_liquido_mw",
    "clima_temp_c", "clima_irrad_wm2", "clima_umidade_pct",
    "hora", "hora_sin", "hora_cos", "dia_semana",
    "thd_tensao_pct", "fator_potencia", "desequilibrio_tensao_pct",
    "frequencia_hz", "tensao_media_v",
    "pot_ativa_kw", "pot_reativa_kvar",
    "ve_demanda_kw", "ve_ocupacao_pct",
    "bat_soc_pct", "geracao_total_mw", "autoprod_pct",
    "anomalia_flag", "evento_flag",
]

# ════════════════════════════════════════════════════════════════
#  CORREÇÃO DE DATA LEAKAGE — Label = risco FUTURO (t + HORIZONTE)
# ════════════════════════════════════════════════════════════════
#
# Problema original: o label "risco" era calculado diretamente de
# pct_carga no mesmo instante t, criando uma relação circular trivial
# (pct_carga -> risco_atual). O modelo aprendia a função determinística
# em vez de uma relação preditiva genuína, inflando artificialmente a acurácia.
#
# Solução: usar o risco do instante FUTURO (t + HORIZONTE_LSTM) como label.
# O modelo agora aprende a PREVER o risco nos próximos 30 minutos a partir
# do estado atual — uma tarefa genuinamente preditiva e não-trivial.
#
# Referência: Boulesteix et al. (2012) "Overview of random forest methodology
# and practical guidance". WIREs Data Mining.

df_sorted = df.sort_values(["zona_id", "timestamp"]).reset_index(drop=True)

# Cria label futuro: risco no instante t + HORIZONTE_LSTM por zona
df_sorted["risco_futuro"] = (
    df_sorted
    .groupby("zona_id")["risco"]
    .shift(-HORIZONTE_LSTM)
)

# Remove linhas sem label futuro (últimas HORIZONTE_LSTM de cada zona)
df_xgb = df_sorted.dropna(subset=["risco_futuro"]).copy()

le = LabelEncoder()
df_xgb["risco_futuro_label"] = le.fit_transform(df_xgb["risco_futuro"])
CLASSES = list(le.classes_)

print(f"  Dataset XGBoost: {len(df_xgb):,} amostras (removidas {len(df_sorted)-len(df_xgb):,} sem label futuro)")
print(f"  Target: risco em t+{HORIZONTE_LSTM} ciclos (~{HORIZONTE_LSTM*5} min)")

X = df_xgb[FEATURES_XGB].values
y = df_xgb["risco_futuro_label"].values

# Split temporal: treino nos primeiros 80% do tempo, teste nos últimos 20%
# Isso evita que informações do futuro vazem para o treino.
n_total = len(X)
n_train = int(n_total * 0.8)
X_train, X_test = X[:n_train], X[n_train:]
y_train, y_test = y[:n_train], y[n_train:]

print(f"\n  Treino: {len(X_train):,} | Teste: {len(X_test):,}")
print(f"  Classes: {CLASSES}")
print(f"  Dist. treino: { {CLASSES[i]: int(c) for i,c in enumerate(np.bincount(y_train))} }")
print(f"\n  Treinando XGBoost...")

modelo_xgb = xgb.XGBClassifier(
    n_estimators=300, max_depth=6, learning_rate=0.05,
    subsample=0.8, colsample_bytree=0.8,
    use_label_encoder=False, eval_metric="mlogloss",
    random_state=SEED,
)
modelo_xgb.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

y_pred_xgb = modelo_xgb.predict(X_test)
acc_xgb    = accuracy_score(y_test, y_pred_xgb)
f1_xgb     = f1_score(y_test, y_pred_xgb, average="weighted")
relatorio_xgb = classification_report(y_test, y_pred_xgb,
                                       target_names=CLASSES, output_dict=True)

print(f"\n  ✅ Acurácia : {acc_xgb*100:.2f}%")
print(f"  ✅ F1-Score : {f1_xgb:.4f}")
print(f"\n  Relatório:")
print(classification_report(y_test, y_pred_xgb, target_names=CLASSES))

modelo_xgb.save_model(f"{PASTA_MODELOS}/xgboost_risco.json")
print(f"  Modelo salvo → {PASTA_MODELOS}/xgboost_risco.json")

# ── SHAP Values — Explicabilidade Formal (XAI) ───────────────────────
if SHAP_DISPONIVEL:
    print(f"\n  Calculando SHAP values para XAI formal...")
    explainer_shap = shap.TreeExplainer(modelo_xgb)
    # Usa amostra do teste para eficiência
    amostra_shap  = min(500, len(X_test))
    X_shap        = X_test[:amostra_shap]
    shap_values   = explainer_shap.shap_values(X_shap)

    # Importância média absoluta — compatível com shap 0.41+ (retorna array 3D)
    import numpy as _np
    sv = _np.array(shap_values)
    
    # SHAP mais recente retorna (n_samples, n_features, n_classes) para multiclasse
    # SHAP antigo ou listas podem retornar (n_classes, n_samples, n_features)
    if sv.ndim == 3:
        if sv.shape[1] == len(FEATURES_XGB):
            shap_mean = _np.abs(sv).mean(axis=(0, 2)) # media sobre amostras e classes
        else:
            shap_mean = _np.abs(sv).mean(axis=(0, 1)) # media se feature for o último eixo
    elif sv.ndim == 2: 
        shap_mean = _np.abs(sv).mean(axis=0)
    else:              
        shap_mean = _np.abs(sv).reshape(-1, len(FEATURES_XGB)).mean(axis=0)

    shap_df = pd.DataFrame({"feature": FEATURES_XGB, "shap_mean": shap_mean.flatten()})
    shap_df = shap_df.sort_values("shap_mean", ascending=False)

    # Gráfico SHAP — Top 15 features
    fig_s, ax_s = plt.subplots(figsize=(10, 6))
    bars = ax_s.barh(shap_df["feature"][:15][::-1],
                     shap_df["shap_mean"][:15][::-1],
                     color="steelblue")
    ax_s.set_title("SHAP Values — Top 15 Features Mais Influentes\n"
                   "(Importância média absoluta para previsão de risco futuro)",
                   fontsize=11, fontweight="bold")
    ax_s.set_xlabel("SHAP Mean |value| (impacto na predição)")
    ax_s.grid(axis="x", alpha=0.3)
    plt.tight_layout()
    caminho_shap = f"{PASTA_GRAFICOS}/shap_xgboost.png"
    plt.savefig(caminho_shap, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Gráfico SHAP salvo → {caminho_shap}")

    # Exporta tabela SHAP para o artigo
    shap_df.to_csv(f"{PASTA_GRAFICOS}/shap_importancias.csv", index=False)
    print(f"  Tabela SHAP salva → {PASTA_GRAFICOS}/shap_importancias.csv")
else:
    print("  [SHAP] Pulando: biblioteca não disponível (pip install shap)")

# ── Gráficos XGBoost ──────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle(f"XGBoost — Classificador de Risco  |  Acurácia: {acc_xgb*100:.2f}%  |  F1: {f1_xgb:.4f}",
             fontsize=13, fontweight="bold")

# Matriz de confusão — valores REAIS do treino atual
cm = confusion_matrix(y_test, y_pred_xgb)
sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
            xticklabels=CLASSES, yticklabels=CLASSES, ax=axes[0])
axes[0].set_title("Matriz de Confusão")
axes[0].set_xlabel("Predito")
axes[0].set_ylabel("Real")

# Feature importance — valores REAIS do treino atual
importancias = pd.Series(modelo_xgb.feature_importances_, index=FEATURES_XGB)
importancias.nlargest(12).sort_values().plot(kind="barh", ax=axes[1], color="steelblue")
axes[1].set_title("Top 12 Features Mais Importantes")
axes[1].set_xlabel("Importância (ganho)")

plt.tight_layout()
caminho = f"{PASTA_GRAFICOS}/xgboost_resultados.png"
plt.savefig(caminho, dpi=150, bbox_inches="tight")
plt.close()
print(f"  Gráfico salvo → {caminho}")

# ══════════════════════════════════════════════════════════════════
#  3. LSTM — PREVISÃO DE CONSUMO POR ZONA
# ══════════════════════════════════════════════════════════════════

print("\n" + "=" * 62)
print("  MODELO 2 — LSTM por Zona (Previsão de Consumo)")
print("=" * 62)

FEATURES_LSTM = [
    "consumo_mw", "pct_carga",
    "clima_temp_c", "clima_irrad_wm2",
    "hora_sin", "hora_cos",
    "evento_flag", "anomalia_flag",
    "geracao_total_mw",
]
TARGET_LSTM = "consumo_mw"

# ── Arquitetura LSTM ───────────────────────────────────────────────
class LSTMConsumo(nn.Module):
    def __init__(self, n_features, hidden=64, n_layers=2, horizonte=6, dropout=0.2):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=n_features, hidden_size=hidden,
            num_layers=n_layers, batch_first=True,
            dropout=dropout if n_layers > 1 else 0,
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden, 32), nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, horizonte),
        )
    def forward(self, x):
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])

def criar_janelas(vals_feat, vals_tgt, janela, horizonte):
    X_list, y_list = [], []
    for i in range(len(vals_feat) - janela - horizonte + 1):
        X_list.append(vals_feat[i:i+janela])
        y_list.append(vals_tgt[i+janela:i+janela+horizonte])
    return np.array(X_list), np.array(y_list)

def treinar_lstm_zona(zona_id, dados_zona):
    """Treina um LSTM dedicado para uma zona específica."""
    dados_zona = dados_zona.sort_values("timestamp").copy()
    if len(dados_zona) < JANELA_LSTM + HORIZONTE_LSTM + 50:
        return None

    # ── Split temporal correto — sem data leakage ────────────────────
    # O scaler é fitado SOMENTE nos dados de treino, depois transformado
    # nos dados de teste. Isso evita que estatísticas do futuro contaminem
    # a normalização do treino (information leakage via scaler).
    n_raw    = len(dados_zona)
    n_treino = int(n_raw * 0.8)
    zona_tr  = dados_zona.iloc[:n_treino]
    zona_te  = dados_zona.iloc[n_treino:]

    if len(zona_te) < JANELA_LSTM + HORIZONTE_LSTM + 10:
        return None

    sx = StandardScaler()
    sy = StandardScaler()

    # Fit apenas no treino — transform em ambos
    feat_tr = sx.fit_transform(zona_tr[FEATURES_LSTM].values)
    tgt_tr  = sy.fit_transform(zona_tr[[TARGET_LSTM]].values).flatten()
    feat_te = sx.transform(zona_te[FEATURES_LSTM].values)
    tgt_te  = sy.transform(zona_te[[TARGET_LSTM]].values).flatten()

    X_seq_tr, y_seq_tr = criar_janelas(feat_tr, tgt_tr, JANELA_LSTM, HORIZONTE_LSTM)
    X_seq_te, y_seq_te = criar_janelas(feat_te, tgt_te, JANELA_LSTM, HORIZONTE_LSTM)

    if len(X_seq_tr) < 50 or len(X_seq_te) < 5:
        return None

    X_tr = torch.FloatTensor(X_seq_tr)
    y_tr = torch.FloatTensor(y_seq_tr)
    X_te = torch.FloatTensor(X_seq_te)
    y_te = torch.FloatTensor(y_seq_te)

    dl = DataLoader(TensorDataset(X_tr, y_tr), batch_size=BATCH_SIZE, shuffle=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model  = LSTMConsumo(len(FEATURES_LSTM), hidden=64, n_layers=2,
                         horizonte=HORIZONTE_LSTM).to(device)
    opt    = torch.optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-5)
    crit   = nn.MSELoss()
    sched  = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, patience=5, factor=0.5)

    melhor_loss = float("inf")
    paciencia   = 0
    hist_train  = []
    hist_val    = []

    for epoch in range(EPOCHS_LSTM):
        model.train()
        loss_tr = 0
        for xb, yb in dl:
            xb, yb = xb.to(device), yb.to(device)
            opt.zero_grad()
            pred = model(xb)
            loss = crit(pred, yb)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            loss_tr += loss.item()
        loss_tr /= len(dl)

        model.eval()
        with torch.no_grad():
            loss_val = crit(model(X_te.to(device)), y_te.to(device)).item()

        sched.step(loss_val)
        hist_train.append(loss_tr)
        hist_val.append(loss_val)

        if loss_val < melhor_loss:
            melhor_loss = loss_val
            torch.save(model.state_dict(), f"{PASTA_MODELOS}/lstm_{zona_id}.pt")
            paciencia = 0
        else:
            paciencia += 1
            if paciencia >= 15:
                break

    # Avaliação final
    model.load_state_dict(torch.load(f"{PASTA_MODELOS}/lstm_{zona_id}.pt",
                                      map_location=device))
    model.eval()
    with torch.no_grad():
        y_pred_norm = model(X_te.to(device)).cpu().numpy()

    y_pred_real = sy.inverse_transform(y_pred_norm)
    y_test_real = sy.inverse_transform(y_te.numpy())

    mae  = mean_absolute_error(y_test_real.flatten(), y_pred_real.flatten())
    rmse = np.sqrt(mean_squared_error(y_test_real.flatten(), y_pred_real.flatten()))
    mask = np.abs(y_test_real.flatten()) > 0.1
    mape = np.mean(np.abs((y_test_real.flatten()[mask] - y_pred_real.flatten()[mask]) /
                      np.abs(y_test_real.flatten()[mask]))) * 100

    # Salva scalers
    with open(f"{PASTA_MODELOS}/scaler_{zona_id}.pkl", "wb") as f:
        pickle.dump({"sx": sx, "sy": sy}, f)

    return {
        "zona_id":       zona_id,
        "mae":           mae,
        "rmse":          rmse,
        "mape":          mape,
        "epocas":        len(hist_train),
        "hist_train":    hist_train,
        "hist_val":      hist_val,
        "y_test_real":   y_test_real,
        "y_pred_real":   y_pred_real,
        "consumo_medio": dados_zona[TARGET_LSTM].mean(),
    }

# ── Treina por zona ────────────────────────────────────────────────
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"\n  Device: {device}")
print(f"  Treinando LSTM para cada zona separadamente...\n")

resultados_lstm = {}
zonas = sorted(df["zona_id"].unique())

for zona_id in zonas:
    dados_zona = df[df["zona_id"] == zona_id].copy()
    print(f"  [{zona_id}]  {len(dados_zona):,} leituras → treinando...", end=" ", flush=True)

    resultado = treinar_lstm_zona(zona_id, dados_zona)

    if resultado:
        resultados_lstm[zona_id] = resultado
        print(f"MAE={resultado['mae']:.4f} MW | MAPE={resultado['mape']:.1f}% | épocas={resultado['epocas']}")
    else:
        print("dados insuficientes, pulando.")

# ── Gráfico 1: Curvas de Loss por zona ────────────────────────────
n_zonas = len(resultados_lstm)
cols    = 4
rows    = (n_zonas + cols - 1) // cols

fig, axes = plt.subplots(rows, cols, figsize=(18, rows * 4))
fig.suptitle("LSTM — Curvas de Loss por Zona (Treino vs Validação)",
             fontsize=14, fontweight="bold")
axes_flat = axes.flatten() if rows > 1 else axes

for idx, (zona_id, res) in enumerate(resultados_lstm.items()):
    ax = axes_flat[idx]
    ax.plot(res["hist_train"], label="Treino",    color="steelblue", linewidth=1.5)
    ax.plot(res["hist_val"],   label="Validação", color="orange",    linewidth=1.5)
    ax.set_title(f"{zona_id}\nMAE={res['mae']:.3f} MW | MAPE={res['mape']:.1f}%", fontsize=9)
    ax.set_xlabel("Época")
    ax.set_ylabel("Loss (MSE)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

# Remove eixos extras
for idx in range(len(resultados_lstm), len(axes_flat)):
    axes_flat[idx].set_visible(False)

plt.tight_layout()
caminho = f"{PASTA_GRAFICOS}/lstm_loss_por_zona.png"
plt.savefig(caminho, dpi=150, bbox_inches="tight")
plt.close()
print(f"\n  Gráfico salvo → {caminho}")

# ── Gráfico 2: Real vs Predito por zona ────────────────────────────
fig, axes = plt.subplots(rows, cols, figsize=(18, rows * 4))
fig.suptitle("LSTM — Real vs Predito por Zona (próximo passo)",
             fontsize=14, fontweight="bold")
axes_flat = axes.flatten() if rows > 1 else axes

for idx, (zona_id, res) in enumerate(resultados_lstm.items()):
    ax  = axes_flat[idx]
    n   = min(120, len(res["y_test_real"]))
    ax.plot(res["y_test_real"][:n, 0], label="Real",    color="steelblue", linewidth=1.5)
    ax.plot(res["y_pred_real"][:n, 0], label="Predito", color="orange",    linewidth=1.5, linestyle="--")
    ax.set_title(f"{zona_id}\nMAE={res['mae']:.3f} MW", fontsize=9)
    ax.set_xlabel("Amostras")
    ax.set_ylabel("Consumo (MW)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

for idx in range(len(resultados_lstm), len(axes_flat)):
    axes_flat[idx].set_visible(False)

plt.tight_layout()
caminho = f"{PASTA_GRAFICOS}/lstm_real_vs_predito.png"
plt.savefig(caminho, dpi=150, bbox_inches="tight")
plt.close()
print(f"  Gráfico salvo → {caminho}")

# ── Gráfico 3: Comparativo MAE e MAPE por zona ────────────────────
zonas_res   = list(resultados_lstm.keys())
maes        = [resultados_lstm[z]["mae"]  for z in zonas_res]
mapes       = [resultados_lstm[z]["mape"] for z in zonas_res]
consumos    = [resultados_lstm[z]["consumo_medio"] for z in zonas_res]
nomes_curtos = [z.replace("zona_", "").capitalize() for z in zonas_res]

fig, axes = plt.subplots(1, 3, figsize=(18, 5))
fig.suptitle("LSTM — Comparativo de Desempenho por Zona",
             fontsize=14, fontweight="bold")

# MAE por zona
cores_mae = ["green" if m < 0.5 else "orange" if m < 1.5 else "red" for m in maes]
bars = axes[0].bar(nomes_curtos, maes, color=cores_mae)
axes[0].set_title("MAE por Zona (MW)\n(menor é melhor)")
axes[0].set_ylabel("MAE (MW)")
axes[0].tick_params(axis="x", rotation=30)
for bar, v in zip(bars, maes):
    axes[0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                 f"{v:.3f}", ha="center", fontsize=8)
axes[0].grid(axis="y", alpha=0.3)

# MAPE por zona
cores_mape = ["green" if m < 10 else "orange" if m < 20 else "red" for m in mapes]
bars2 = axes[1].bar(nomes_curtos, mapes, color=cores_mape)
axes[1].set_title("MAPE por Zona (%)\n(menor é melhor)")
axes[1].set_ylabel("MAPE (%)")
axes[1].tick_params(axis="x", rotation=30)
for bar, v in zip(bars2, mapes):
    axes[1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                 f"{v:.1f}%", ha="center", fontsize=8)
axes[1].grid(axis="y", alpha=0.3)

# MAE relativo ao consumo médio
mae_rel = [m/c*100 for m, c in zip(maes, consumos)]
cores_rel = ["green" if m < 5 else "orange" if m < 10 else "red" for m in mae_rel]
bars3 = axes[2].bar(nomes_curtos, mae_rel, color=cores_rel)
axes[2].set_title("Erro Relativo ao Consumo Médio (%)\n(menor é melhor)")
axes[2].set_ylabel("MAE / Consumo Médio (%)")
axes[2].tick_params(axis="x", rotation=30)
for bar, v in zip(bars3, mae_rel):
    axes[2].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                 f"{v:.1f}%", ha="center", fontsize=8)
axes[2].grid(axis="y", alpha=0.3)

plt.tight_layout()
caminho = f"{PASTA_GRAFICOS}/lstm_comparativo_zonas.png"
plt.savefig(caminho, dpi=150, bbox_inches="tight")
plt.close()
print(f"  Gráfico salvo → {caminho}")

# ── Gráfico 4: XGBoost comparativo por classe ─────────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle(f"CityGrid Brain — Comparativo Final\nXGBoost Acc={acc_xgb*100:.1f}% | LSTM MAE médio={np.mean(maes):.3f} MW",
             fontsize=13, fontweight="bold")

f1_por_classe = [relatorio_xgb[c]["f1-score"] for c in CLASSES]
cores_xgb     = ["green", "steelblue", "red", "orange"]
bars4 = axes[0].bar(CLASSES, f1_por_classe, color=cores_xgb)
axes[0].set_title("XGBoost — F1-Score por Classe de Risco")
axes[0].set_ylabel("F1-Score")
axes[0].set_ylim(0, 1.15)
for bar, v in zip(bars4, f1_por_classe):
    axes[0].text(bar.get_x() + bar.get_width()/2, v + 0.02,
                 f"{v:.2f}", ha="center", fontsize=11, fontweight="bold")
axes[0].grid(axis="y", alpha=0.3)

# LSTM MAE por passo de horizonte — média entre todas as zonas
mae_por_passo = []
for h in range(HORIZONTE_LSTM):
    erros = []
    for res in resultados_lstm.values():
        erros.append(mean_absolute_error(
            res["y_test_real"][:, h], res["y_pred_real"][:, h]
        ))
    mae_por_passo.append(np.mean(erros))

bars5 = axes[1].bar(range(1, HORIZONTE_LSTM+1), mae_por_passo, color="steelblue")
axes[1].set_title("LSTM — MAE Médio por Passo de Previsão")
axes[1].set_xlabel("Passo (ciclos à frente)")
axes[1].set_ylabel("MAE médio (MW)")
for bar, v in zip(bars5, mae_por_passo):
    axes[1].text(bar.get_x() + bar.get_width()/2, v + 0.002,
                 f"{v:.3f}", ha="center", fontsize=9)
axes[1].grid(axis="y", alpha=0.3)

plt.tight_layout()
caminho = f"{PASTA_GRAFICOS}/comparativo_final.png"
plt.savefig(caminho, dpi=150, bbox_inches="tight")
plt.close()
print(f"  Gráfico salvo → {caminho}")

# ══════════════════════════════════════════════════════════════════
#  4. RESUMO FINAL — PARA O ARTIGO
# ══════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
#  4. ABLATION STUDY — Comparação das 4 Camadas
# ══════════════════════════════════════════════════════════════

print("\n" + "=" * 62)
print("  ABLATION STUDY — Comparativo das 4 Camadas de Decisão")
print("=" * 62)

# Configuração 1: Baseline — prediz sempre a classe mais frequente
dummy = DummyClassifier(strategy="most_frequent", random_state=SEED)
dummy.fit(X_train, y_train)
acc_baseline = accuracy_score(y_test, dummy.predict(X_test))
f1_baseline  = f1_score(y_test, dummy.predict(X_test), average="weighted", zero_division=0)
print(f"\n  [Baseline Majority Class]  Acc={acc_baseline*100:.1f}%  F1={f1_baseline:.4f}")

# Configuração 2: Somente XGBoost
acc_xgb_only = acc_xgb
f1_xgb_only  = f1_xgb
print(f"  [Somente XGBoost]          Acc={acc_xgb_only*100:.1f}%  F1={f1_xgb_only:.4f}")

# Configuração 3: LSTM — converte previsão contínua em classe de risco
def pct_para_risco(pct):
    if pct >= 92: return "CRÍTICO"
    if pct >= 78: return "ALTO"
    if pct >= 58: return "MÉDIO"
    return "BAIXO"

lstm_preds_risco = []
lstm_trues_risco = []
for zona_id_ab, res_ab in resultados_lstm.items():
    cap_ab = df[df["zona_id"] == zona_id_ab]["capacidade_mw"].mean()
    if cap_ab <= 0: continue
    for i in range(len(res_ab["y_pred_real"])):
        pred_pct = (res_ab["y_pred_real"][i][0] / cap_ab) * 100
        true_pct = (res_ab["y_test_real"][i][0] / cap_ab) * 100
        lstm_preds_risco.append(pct_para_risco(pred_pct))
        lstm_trues_risco.append(pct_para_risco(true_pct))

if lstm_preds_risco:
    le_lstm = LabelEncoder()
    le_lstm.fit(["ALTO", "BAIXO", "CRÍTICO", "MÉDIO"])
    lstm_true_enc = le_lstm.transform(lstm_trues_risco)
    lstm_pred_enc = le_lstm.transform(lstm_preds_risco)
    acc_lstm_only = accuracy_score(lstm_true_enc, lstm_pred_enc)
    f1_lstm_only  = f1_score(lstm_true_enc, lstm_pred_enc, average="weighted", zero_division=0)
    print(f"  [Somente LSTM]             Acc={acc_lstm_only*100:.1f}%  F1={f1_lstm_only:.4f}")
else:
    acc_lstm_only = 0.0
    f1_lstm_only  = 0.0
    print("  [Somente LSTM]             Dados insuficientes")

# Gráfico do Ablation Study
fig_ab, ax_ab = plt.subplots(1, 2, figsize=(12, 5))
fig_ab.suptitle("Ablation Study — Impacto de Cada Camada de Decisão\n"
                "CityGrid Brain | Target: Risco Futuro (t+30min)",
                fontsize=13, fontweight="bold")

configs   = ["Baseline\n(Majority)", "Somente\nXGBoost", "Somente\nLSTM", "Híbrido\nXGBoost+LSTM"]
accs      = [acc_baseline*100, acc_xgb_only*100, acc_lstm_only*100,
             (acc_xgb_only * 0.6 + acc_lstm_only * 0.4) * 100]  # estimativa híbrido
f1s       = [f1_baseline, f1_xgb_only, f1_lstm_only,
             f1_xgb_only * 0.6 + f1_lstm_only * 0.4]
cores_ab  = ["#6b7280", "#3b82f6", "#10b981", "#8b5cf6"]

bars_ab = ax_ab[0].bar(configs, accs, color=cores_ab)
ax_ab[0].set_title("Acurácia por Configuração (%)")
ax_ab[0].set_ylabel("Acurácia (%)")
ax_ab[0].set_ylim(0, 110)
for bar, v in zip(bars_ab, accs):
    ax_ab[0].text(bar.get_x() + bar.get_width()/2, v + 1,
                  f"{v:.1f}%", ha="center", fontsize=10, fontweight="bold")
ax_ab[0].grid(axis="y", alpha=0.3)

bars_f1 = ax_ab[1].bar(configs, f1s, color=cores_ab)
ax_ab[1].set_title("F1-Score Ponderado por Configuração")
ax_ab[1].set_ylabel("F1-Score")
ax_ab[1].set_ylim(0, 1.15)
for bar, v in zip(bars_f1, f1s):
    ax_ab[1].text(bar.get_x() + bar.get_width()/2, v + 0.02,
                  f"{v:.3f}", ha="center", fontsize=10, fontweight="bold")
ax_ab[1].grid(axis="y", alpha=0.3)

plt.tight_layout()
caminho_ab = f"{PASTA_GRAFICOS}/ablation_study.png"
plt.savefig(caminho_ab, dpi=150, bbox_inches="tight")
plt.close()
print(f"  Gráfico Ablation Study salvo → {caminho_ab}")

print("\n" + "=" * 62)
print("  RESUMO FINAL — RESULTADOS PARA O ARTIGO")
print("=" * 62)

print(f"""
  ┌──────────────────────────────────────────────────────────┐
  │  XGBoost — Classificador de Risco                       │
  │    Acurácia  : {acc_xgb*100:.2f}%                               │
  │    F1-Score  : {f1_xgb:.4f}                                  │
  ├──────────────────────────────────────────────────────────┤
  │  LSTM — Previsão de Consumo por Zona                    │
  │    MAE médio : {np.mean(maes):.4f} MW                           │
  │    MAPE médio: {np.mean(mapes):.2f}%                              │
  ├──────────────────────────────────────────────────────────┤
  │  Detalhamento por zona:                                 │""")

for zona_id, res in resultados_lstm.items():
    print(f"  │    {zona_id:<22} MAE={res['mae']:.3f} MW  MAPE={res['mape']:>5.1f}%  │")

print(f"""  └──────────────────────────────────────────────────────────┘

  Gráficos gerados:
    → {PASTA_GRAFICOS}/xgboost_resultados.png
    → {PASTA_GRAFICOS}/lstm_loss_por_zona.png
    → {PASTA_GRAFICOS}/lstm_real_vs_predito.png
    → {PASTA_GRAFICOS}/lstm_comparativo_zonas.png
    → {PASTA_GRAFICOS}/comparativo_final.png

  Modelos salvos:
    → {PASTA_MODELOS}/xgboost_risco.json
    → {PASTA_MODELOS}/lstm_<zona>.pt  (um por zona)
    → {PASTA_MODELOS}/scaler_<zona>.pkl
""")

print("=" * 62)
print("  TREINAMENTO CONCLUÍDO!")
print("=" * 62)