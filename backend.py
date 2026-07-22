"""
╔══════════════════════════════════════════════════════════════════╗
║         CITYGRID BRAIN — BACKEND API v1.0                       ║
║   FastAPI + WebSocket para o Dashboard em Tempo Real            ║
╚══════════════════════════════════════════════════════════════════╝

Endpoints:
  GET  /api/zonas          — estado atual de todas as zonas + previsão ML
  GET  /api/alertas        — últimas N decisões/alertas do motor
  GET  /api/stats          — estatísticas globais da cidade
  GET  /api/historico/{z}  — histórico de consumo de uma zona (últimas 2h)
  WS   /ws                 — push de atualizações a cada 5s para o dashboard

Fontes de dados:
  - dados_citygrid.jsonl   — leituras do simulador IoT
  - logs/decisoes.jsonl    — ações/alertas do motor de decisão
  - modelos/               — modelos XGBoost e LSTM treinados
"""

import os
import sys
import json
import time
import pickle
import asyncio
import logging
import numpy as np
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from collections import defaultdict, deque
from contextlib import asynccontextmanager

# FastAPI
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ML
import torch
import torch.nn as nn
import xgboost as xgb

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("citygrid-backend")

# ══════════════════════════════════════════════════════════════════
#  CONFIGURAÇÃO
# ══════════════════════════════════════════════════════════════════

BASE_DIR        = Path(__file__).parent
ARQUIVO_JSONL   = BASE_DIR / "dados_citygrid.jsonl"
LOG_DECISOES    = BASE_DIR / "logs" / "decisoes.jsonl"
PASTA_MODELOS   = BASE_DIR / "modelos"

JANELA_LSTM     = 24
HORIZONTE_LSTM  = 6
INTERVALO_SIMULADO_MINUTOS = 5
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
FEATURES_LSTM = [
    "consumo_mw", "pct_carga",
    "clima_temp_c", "clima_irrad_wm2",
    "hora_sin", "hora_cos",
    "evento_flag", "anomalia_flag",
    "geracao_total_mw",
]
CLASSES_RISCO = ["ALTO", "BAIXO", "CRÍTICO", "MÉDIO"]

# Cache de dados em memória
_cache: Dict[str, Any] = {
    "zonas":          {},        # ultima leitura por zona_id
    "historicos":     defaultdict(lambda: deque(maxlen=JANELA_LSTM * 4)),
    "alertas":        deque(maxlen=50),
    "stats":          {},
    "ciclo_atual":    0,
    "ultima_leitura": None,
    "ultima_chave_por_zona": {},
}

# ══════════════════════════════════════════════════════════════════
#  ARQUITETURA LSTM (igual ao treinamento)
# ══════════════════════════════════════════════════════════════════

class LSTMConsumo(nn.Module):
    def __init__(self, n_features=9, hidden=64, n_layers=2, horizonte=6, dropout=0.2):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=n_features, hidden_size=hidden,
            num_layers=n_layers, batch_first=True,
            dropout=dropout if n_layers > 1 else 0,
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden, 32), nn.ReLU(),
            nn.Dropout(dropout), nn.Linear(32, horizonte),
        )
    def forward(self, x):
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])

# ══════════════════════════════════════════════════════════════════
#  CARREGAMENTO DE MODELOS
# ══════════════════════════════════════════════════════════════════

modelos = {"xgb": None, "lstm": {}, "scalers": {}, "device": None}

def carregar_modelos():
    global modelos
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    modelos["device"] = device

    # XGBoost
    caminho_xgb = PASTA_MODELOS / "xgboost_risco.json"
    if caminho_xgb.exists():
        m = xgb.XGBClassifier()
        m.load_model(str(caminho_xgb))
        modelos["xgb"] = m
        logger.info("XGBoost carregado")
    else:
        logger.warning("XGBoost não encontrado — rode treinamento_ml.py primeiro")

    # LSTMs por zona
    for arquivo in PASTA_MODELOS.iterdir():
        if arquivo.name.startswith("lstm_") and arquivo.suffix == ".pt":
            zona_id = arquivo.stem.replace("lstm_", "")
            modelo  = LSTMConsumo()
            modelo.load_state_dict(torch.load(str(arquivo), map_location=device, weights_only=True))
            modelo.eval()
            modelos["lstm"][zona_id] = modelo

        if arquivo.name.startswith("scaler_") and arquivo.suffix == ".pkl":
            zona_id = arquivo.stem.replace("scaler_", "")
            with open(arquivo, "rb") as f:
                modelos["scalers"][zona_id] = pickle.load(f)

    logger.info(f"LSTM: {len(modelos['lstm'])} modelos | Scalers: {len(modelos['scalers'])}")

# ══════════════════════════════════════════════════════════════════
#  LEITURA EFICIENTE DO JSONL (últimas N linhas)
# ══════════════════════════════════════════════════════════════════

def ler_ultimas_linhas(caminho: Path, n: int = 200) -> List[dict]:
    """Lê as últimas N linhas de um JSONL de forma eficiente."""
    if not caminho.exists():
        return []
    try:
        with open(caminho, "rb") as f:
            f.seek(0, 2)
            tamanho = f.tell()
            if tamanho == 0:
                return []
            # Lê bloco do final
            bloco = min(tamanho, n * 300)
            f.seek(max(0, tamanho - bloco))
            raw = f.read()
        linhas = raw.decode("utf-8", errors="replace").splitlines()
        resultados = []
        for linha in reversed(linhas):
            linha = linha.strip()
            if not linha:
                continue
            try:
                resultados.append(json.loads(linha))
            except json.JSONDecodeError:
                continue
            if len(resultados) >= n:
                break
        return list(reversed(resultados))
    except Exception as e:
        logger.error(f"Erro ao ler {caminho}: {e}")
        return []


def extrair_instante_amostra(dados: dict) -> datetime:
    """Usa o relógio simulado da amostra, não o relógio da máquina."""
    valor = dados.get("timestamp")
    if valor:
        try:
            return datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
        except ValueError:
            logger.warning("Timestamp inválido na amostra: %s", valor)
    return datetime.now(timezone.utc)


def incorporar_leituras_cache(leituras: List[dict]) -> Dict[str, dict]:
    """Incorpora apenas observações novas e devolve a mais recente por zona."""
    por_zona: Dict[str, dict] = {}
    for leitura in leituras:
        zona_id = leitura.get("zona_id")
        if not zona_id:
            continue
        por_zona[zona_id] = leitura
        chave = (leitura.get("ciclo"), leitura.get("timestamp"))
        historico = _cache["historicos"][zona_id]
        chaves_existentes = {
            (item.get("ciclo"), item.get("timestamp")) for item in historico
        }
        if chave not in chaves_existentes:
            historico.append(leitura)
        _cache["ultima_chave_por_zona"][zona_id] = chave
    return por_zona


def calcular_stats(
    zonas: List[dict],
    total_recomendacoes: int,
    intervalo_minutos: int = INTERVALO_SIMULADO_MINUTOS,
) -> dict:
    """Calcula telemetria observada sem atribuir economia causal à IA."""
    if not zonas:
        return {}
    tot_mw = sum(z.get("consumo_mw", 0) for z in zonas)
    tot_renov = sum(z.get("geracao_total_mw", 0) for z in zonas)
    pct_renov = round(tot_renov / tot_mw * 100, 1) if tot_mw > 0 else 0
    return {
        "consumo_total_mw": round(tot_mw, 2),
        "renovavel_total_mw": round(tot_renov, 3),
        "pct_renovavel": pct_renov,
        "zonas_criticas": sum(1 for z in zonas if z.get("risco") == "CRÍTICO"),
        "zonas_alto": sum(1 for z in zonas if z.get("risco") == "ALTO"),
        "anomalias_ativas": sum(1 for z in zonas if z.get("anomalia_tipo")),
        "total_recomendacoes": total_recomendacoes,
        "energia_renovavel_intervalo_mwh": round(
            tot_renov * intervalo_minutos / 60, 4
        ),
        "intervalo_simulado_minutos": intervalo_minutos,
        "evento_ativo": zonas[0].get("evento"),
        "dados_sinteticos": True,
    }

# ══════════════════════════════════════════════════════════════════
#  INFERÊNCIA ML


def inferir_xgboost(dados: dict) -> tuple:
    """Retorna (risco_previsto, confianca, distribuicao)."""
    if modelos["xgb"] is None:
        return "AGUARDANDO", None, {}

    instante = extrair_instante_amostra(dados)
    hora = instante.hour
    d    = dict(dados)
    d["hora"]          = hora
    d["hora_sin"]      = np.sin(2 * np.pi * hora / 24)
    d["hora_cos"]      = np.cos(2 * np.pi * hora / 24)
    d["dia_semana"]    = instante.weekday()
    d["anomalia_flag"] = 1 if d.get("anomalia_tipo") else 0
    d["evento_flag"]   = 1 if d.get("evento") else 0

    try:
        X       = np.array([[d.get(f, 0.0) for f in FEATURES_XGB]])
        proba   = modelos["xgb"].predict_proba(X)[0]
        idx     = int(np.argmax(proba))
        risco   = CLASSES_RISCO[idx]
        conf    = float(proba[idx])
        distrib = {CLASSES_RISCO[i]: round(float(p), 3) for i, p in enumerate(proba)}
        return risco, conf, distrib
    except Exception as e:
        logger.warning(f"Erro XGBoost: {e}")
        return "ERRO", None, {}


def inferir_lstm(zona_id: str, historico: list) -> tuple:
    """Retorna (risco_futuro, previsao_mw)."""
    if zona_id not in modelos["lstm"] or zona_id not in modelos["scalers"]:
        return "AGUARDANDO", []

    if len(historico) < JANELA_LSTM:
        return "AGUARDANDO", []

    try:
        scalers    = modelos["scalers"][zona_id]
        sx, sy     = scalers["sx"], scalers["sy"]
        janela     = historico[-JANELA_LSTM:]
        arr        = np.array([[l.get(f, 0.0) for f in FEATURES_LSTM] for l in janela])
        arr_norm   = sx.transform(arr)
        device     = modelos["device"]
        X_tensor   = torch.FloatTensor(arr_norm).unsqueeze(0).to(device)

        with torch.no_grad():
            pred_norm = modelos["lstm"][zona_id](X_tensor).cpu().numpy()

        pred_real  = sy.inverse_transform(pred_norm)[0]
        pred_real  = [max(0.0, float(v)) for v in pred_real]

        cap        = historico[-1].get("capacidade_mw", 1)
        max_prev   = max(pred_real)
        pct_prev   = (max_prev / cap) * 100

        if pct_prev >= 92:   risco_futuro = "CRÍTICO"
        elif pct_prev >= 78: risco_futuro = "ALTO"
        elif pct_prev >= 58: risco_futuro = "MÉDIO"
        else:                risco_futuro = "BAIXO"

        return risco_futuro, pred_real
    except Exception as e:
        logger.warning(f"Erro LSTM [{zona_id}]: {e}")
        return "ERRO", []

# ══════════════════════════════════════════════════════════════════
#  ATUALIZAÇÃO DO CACHE (roda em background)
# ══════════════════════════════════════════════════════════════════

async def atualizar_cache():
    """Lê o JSONL, roda inferência ML e atualiza o cache."""
    leituras = ler_ultimas_linhas(ARQUIVO_JSONL, n=50)
    if not leituras:
        return

    # Agrupa por zona e adiciona ao histórico somente observações novas.
    por_zona = incorporar_leituras_cache(leituras)

    # Atualiza cada zona com inferência ML
    for zona_id, dados in por_zona.items():
        risco_xgb, conf_xgb, distrib_xgb = inferir_xgboost(dados)
        risco_lstm, previsao_mw = inferir_lstm(
            zona_id, list(_cache["historicos"][zona_id])
        )

        _cache["zonas"][zona_id] = {
            **dados,
            "risco_xgb":    risco_xgb,
            "conf_xgb":     conf_xgb,
            "distrib_xgb":  distrib_xgb,
            "risco_lstm":   risco_lstm,
            "previsao_mw":  previsao_mw,
        }

        ciclo = dados.get("ciclo", 0)
        if ciclo > _cache["ciclo_atual"]:
            _cache["ciclo_atual"] = ciclo

    timestamps = [str(d.get("timestamp")) for d in por_zona.values() if d.get("timestamp")]
    _cache["ultima_leitura"] = max(timestamps) if timestamps else None

    # Lê recomendações recentes
    alertas_raw = ler_ultimas_linhas(LOG_DECISOES, n=20)
    _cache["alertas"] = deque(alertas_raw, maxlen=20)

    zonas = list(_cache["zonas"].values())
    _cache["stats"] = calcular_stats(
        zonas,
        total_recomendacoes=len(_cache["alertas"]),
    )

# ══════════════════════════════════════════════════════════════════
#  FASTAPI APP
# ══════════════════════════════════════════════════════════════════


@asynccontextmanager
async def lifespan(_: FastAPI):
    carregar_modelos()
    tarefa = asyncio.create_task(loop_atualizacao())
    logger.info("CityGrid Backend iniciado — http://localhost:8000")
    try:
        yield
    finally:
        tarefa.cancel()
        try:
            await tarefa
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="CityGrid Brain API",
    description="API de um protótipo experimental com dados sintéticos",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:4173",
        "http://localhost:4173",
    ],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ── WebSocket Manager ──────────────────────────────────────────────

class WSManager:
    def __init__(self):
        self._clientes: List[WebSocket] = []

    async def conectar(self, ws: WebSocket):
        await ws.accept()
        self._clientes.append(ws)
        logger.info(f"WS conectado — total: {len(self._clientes)}")

    def desconectar(self, ws: WebSocket):
        self._clientes = [c for c in self._clientes if c != ws]

    async def broadcast(self, payload: dict):
        desconectados = []
        for ws in self._clientes:
            try:
                await ws.send_json(payload)
            except Exception:
                desconectados.append(ws)
        for ws in desconectados:
            self.desconectar(ws)

ws_manager = WSManager()

# ── Background task — atualiza cache e faz broadcast a cada 5s ────

async def loop_atualizacao():
    while True:
        try:
            await atualizar_cache()
            payload = {
                "tipo":      "update",
                "ciclo":     _cache["ciclo_atual"],
                "timestamp_simulado": _cache["ultima_leitura"],
                "atualizado_em_utc": datetime.now(timezone.utc).isoformat(),
                "zonas":     list(_cache["zonas"].values()),
                "stats":     _cache["stats"],
                "recomendacoes": list(_cache["alertas"])[-20:],
            }
            await ws_manager.broadcast(payload)
        except Exception as e:
            logger.error(f"Erro no loop de atualização: {e}")
        await asyncio.sleep(5)

# ── Endpoints REST ─────────────────────────────────────────────────

@app.get("/api/zonas")
async def get_zonas():
    """Retorna o estado atual de todas as zonas com previsão ML."""
    return list(_cache["zonas"].values())


@app.get("/api/alertas")
async def get_alertas(n: int = 20):
    """Retorna recomendações simuladas recentes do motor de decisão."""
    return list(_cache["alertas"])[-n:]


@app.get("/api/stats")
async def get_stats():
    """Retorna estatísticas globais da cidade."""
    return _cache["stats"]


@app.get("/api/historico/{zona_id}")
async def get_historico(zona_id: str, ultimas: int = 48):
    """Retorna histórico de consumo de uma zona (últimas N leituras)."""
    hist = list(_cache["historicos"].get(zona_id, []))
    if not hist:
        # Tenta ler mais do JSONL
        todas = ler_ultimas_linhas(ARQUIVO_JSONL, n=500)
        hist  = [l for l in todas if l.get("zona_id") == zona_id]
    return hist[-ultimas:]


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws_manager.conectar(ws)
    try:
        # Envia estado atual imediatamente ao conectar
        await ws.send_json({
            "tipo":      "update",
            "ciclo":     _cache["ciclo_atual"],
            "timestamp_simulado": _cache["ultima_leitura"],
            "atualizado_em_utc": datetime.now(timezone.utc).isoformat(),
            "zonas":     list(_cache["zonas"].values()),
            "stats":     _cache["stats"],
            "recomendacoes": list(_cache["alertas"])[-20:],
        })
        while True:
            await asyncio.sleep(30)  # mantém a conexão viva
    except WebSocketDisconnect:
        ws_manager.desconectar(ws)
    except Exception as e:
        logger.error(f"WS error: {e}")
        ws_manager.desconectar(ws)


@app.get("/")
async def root():
    return {
        "projeto": "CityGrid Brain",
        "versao":  "1.0.0",
        "status":  "online",
        "endpoints": ["/api/zonas", "/api/alertas", "/api/stats", "/api/historico/{zona_id}", "/ws"],
    }

# ══════════════════════════════════════════════════════════════════
#  ENTRYPOINT
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend:app", host="0.0.0.0", port=8000, reload=False, log_level="info")
