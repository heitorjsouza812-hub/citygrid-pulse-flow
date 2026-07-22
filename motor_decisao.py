"""
╔══════════════════════════════════════════════════════════════════╗
║         CITYGRID BRAIN — MOTOR DE DECISÃO HÍBRIDO               ║
║                        v1.0                                     ║
╚══════════════════════════════════════════════════════════════════╝

Camadas de recomendação experimental:
  1. Heurísticas    → identifica condições que merecem atenção imediata
  2. XGBoost        → estima o risco 30 minutos à frente
  3. LSTM           → prevê consumo para os próximos 30 minutos
  4. Alg. Genético  → calcula um cenário hipotético de redistribuição

Cada recomendação gera:

  - Nível de urgência
  - Explicação em linguagem natural (XAI)
  - Log completo para auditoria
"""

import os
import sys
import time
import json
import pickle
import random
import logging
import numpy as np
import pandas as pd
from datetime import datetime
from collections import deque
from dataclasses import dataclass, field, asdict
from typing import Optional
from colorama import Fore, Style, init

try:  # Kafka é opcional no modo de feira baseado em arquivo.
    from kafka import KafkaConsumer
    from kafka.errors import NoBrokersAvailable
except ImportError:  # pragma: no cover - exercido apenas em instalação mínima
    KafkaConsumer = None

    class NoBrokersAvailable(Exception):
        pass

import torch
import torch.nn as nn
import xgboost as xgb


init(autoreset=True)

# ══════════════════════════════════════════════════════════════════
#  CONFIGURAÇÃO
# ══════════════════════════════════════════════════════════════════

PASTA_MODELOS   = "modelos"
LOG_DECISOES    = "logs/decisoes.jsonl"
ARQUIVO_JSONL   = "dados_citygrid.jsonl"
KAFKA_BOOTSTRAP = os.getenv("CITYGRID_KAFKA_BOOTSTRAP", "localhost:9092")
TOPICO_LEITURAS = "citygrid-leituras"
GRUPO_CONSUMIDOR = "citygrid-motor-decisao-group"
POLL_TIMEOUT_MS = 1000
TEMPO_MAX_CICLO_S = 2.0
JANELA_LSTM     = 24
HORIZONTE_LSTM  = 6
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
CLASSES_RISCO  = ["ALTO", "BAIXO", "CRÍTICO", "MÉDIO"]
PRIORIDADE     = {"CRÍTICO": 4, "ALTO": 3, "MÉDIO": 2, "BAIXO": 1}

os.makedirs("logs", exist_ok=True)
logging.basicConfig(filename="logs/citygrid.log", level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")

# ══════════════════════════════════════════════════════════════════
#  DATACLASSES
# ══════════════════════════════════════════════════════════════════

@dataclass
class Acao:
    tipo:        str
    urgencia:    str
    zona_alvo:   str
    descricao:   str
    explicacao:  str
    confianca:   Optional[float]
    origem:      str   # "heuristica" | "xgboost" | "lstm" | "genetico"
    timestamp:   str   = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))


@dataclass
class EstadoZona:
    zona_id:         str
    consumo_mw:      float
    capacidade_mw:   float
    pct_carga:       float
    risco_atual:     str
    risco_xgb:       str
    risco_futuro:    str
    consumo_previsto: list
    acoes:           list = field(default_factory=list)

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
#  CARREGAMENTO DOS MODELOS
# ══════════════════════════════════════════════════════════════════

def carregar_modelos():
    print(f"\n  Carregando modelos de {PASTA_MODELOS}/...")

    # XGBoost
    modelo_xgb = xgb.XGBClassifier()
    modelo_xgb.load_model(f"{PASTA_MODELOS}/xgboost_risco.json")
    print(f"  ✅ XGBoost carregado")

    # LSTMs por zona
    device      = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    modelos_lstm = {}
    scalers_zona = {}

    for arquivo in os.listdir(PASTA_MODELOS):
        if arquivo.startswith("lstm_") and arquivo.endswith(".pt"):
            zona_id = arquivo.replace("lstm_", "").replace(".pt", "")
            modelo  = LSTMConsumo()
            modelo.load_state_dict(torch.load(
                f"{PASTA_MODELOS}/{arquivo}", map_location=device, weights_only=True
            ))
            modelo.eval()
            modelos_lstm[zona_id] = modelo

        if arquivo.startswith("scaler_") and arquivo.endswith(".pkl"):
            zona_id = arquivo.replace("scaler_", "").replace(".pkl", "")
            with open(f"{PASTA_MODELOS}/{arquivo}", "rb") as f:
                scalers_zona[zona_id] = pickle.load(f)

    print(f"  ✅ {len(modelos_lstm)} modelos LSTM carregados: {list(modelos_lstm.keys())}")
    print(f"  ✅ {len(scalers_zona)} scalers carregados")
    return modelo_xgb, modelos_lstm, scalers_zona, device

# ══════════════════════════════════════════════════════════════════
#  CAMADA 1 — HEURÍSTICAS
# ══════════════════════════════════════════════════════════════════

def avaliar_heuristicas(zona_id: str, dados: dict) -> Optional[Acao]:
    """
    Regras fixas de emergência — têm prioridade absoluta sobre ML. Execução em <1ms.

    ORDEM DE PRIORIDADE (do maior para menor):
      R0 — Zona crítica (hospital/UPA) em sobrecarga → NUNCA cortar carga (vida humana)
      R1 — Sobrecarga geral >= 95% (somente zonas NÃO-críticas)
      R2 — Frequência fora do limite ANEEL PRODIST M8
      R3 — THD acima do limite ANEEL (8%)
      R4 — Fator de potência menor que 0,92
      R5 — Microfalta (consumo zero inesperado)
    """
    pct     = dados.get("pct_carga", 0)
    freq    = dados.get("frequencia_hz", 60.0)
    thd     = dados.get("thd_tensao_pct", 0)
    fp      = dados.get("fator_potencia", 1.0)
    consumo = dados.get("consumo_mw", 0)
    perfil  = dados.get("perfil", "")

    # ── Regra R0 (MÁXIMA PRIORIDADE) — Zona crítica em sobrecarga ───────────
    # AVALIADA ANTES de qualquer corte de carga.
    # Hospitais e UPAs NUNCA podem ser desligados — proteção à vida humana.
    if perfil == "critico":
        if pct >= 95:
            return Acao(
                tipo="EMERGENCIA_ZONA_CRITICA",
                urgencia="CRÍTICA",
                zona_alvo=zona_id,
                descricao=f"Zona crítica (hospital/UPA) em {pct:.1f}% — mobilizar geração de reserva",
                explicacao=(
                    f"Regra R0: zona crítica com pct_carga={pct:.1f}% >= 95%. "
                    f"NUNCA cortar carga em zona crítica. Acionar gerador de emergência "
                    f"e redistribuir de outras zonas para manter fornecimento."
                ),
                confianca=None,
                origem="heuristica",
            )
        if pct >= 85:
            return Acao(
                tipo="PRIORIDADE_CARGA_CRITICA",
                urgencia="ALTA",
                zona_alvo=zona_id,
                descricao=f"Zona hospitalar/crítica em {pct:.1f}% — ativar reserva de emergência",
                explicacao=(
                    f"Regra R0: zona crítica (hospitais/UPAs) com pct_carga={pct:.1f}% >= 85%. "
                    f"Prioridade máxima de fornecimento. Preparar geração de backup."
                ),
                confianca=None,
                origem="heuristica",
            )

    # ── Regra R1 — Sobrecarga crítica (somente zonas NÃO-críticas) ──────────
    if pct >= 95 and perfil != "critico":
        return Acao(
            tipo="RECOMENDAR_REDUCAO_CARGA",
            urgencia="CRÍTICA",
            zona_alvo=zona_id,
            descricao=f"Zona em {pct:.1f}% da capacidade — recomendar redução de carga não essencial",
            explicacao=(
                f"Regra R1: pct_carga={pct:.1f}% >= 95%. "
                f"Risco de dano ao transformador; recomenda-se revisão humana imediata, sem execução automática."
            ),
            confianca=None,
            origem="heuristica",
        )

    # ── Regra R2 — Frequência fora do limite ANEEL PRODIST M8 ───────────────
    if freq < 59.5 or freq > 60.5:
        return Acao(
            tipo="ALERTA_FREQUENCIA",
            urgencia="ALTA",
            zona_alvo=zona_id,
            descricao=f"Frequência em {freq:.3f} Hz — fora do limite ANEEL (59,5–60,5 Hz)",
            explicacao=(
                f"Regra R2: frequencia_hz={freq:.3f} Hz fora do limite precário ANEEL PRODIST M8. "
                f"Indica desequilíbrio entre geração e carga na rede."
            ),
            confianca=None,
            origem="heuristica",
        )

    # ── Regra R3 — THD acima do limite crítico ANEEL ────────────────────────
    if thd > 8.0:
        return Acao(
            tipo="ALERTA_QUALIDADE_ENERGIA",
            urgencia="ALTA",
            zona_alvo=zona_id,
            descricao=f"THD de tensão em {thd:.1f}% — acima do limite ANEEL (8%)",
            explicacao=(
                f"Regra R3: thd_tensao_pct={thd:.1f}% > 8% (ANEEL PRODIST M8, Seção 3.6). "
                f"Distorção harmônica pode danificar equipamentos e causar falhas."
            ),
            confianca=None,
            origem="heuristica",
        )

    # ── Regra R4 — Fator de potência abaixo do mínimo ANEEL ─────────────────
    if fp < 0.92 and pct > 30:
        return Acao(
            tipo="ALERTA_FATOR_POTENCIA",
            urgencia="MÉDIA",
            zona_alvo=zona_id,
            descricao=f"Fator de potência em {fp:.3f} — abaixo do mínimo ANEEL (0,92)",
            explicacao=(
                f"Regra R4: fator_potencia={fp:.3f} menor que 0,92 (Res. ANEEL 456/2000). "
                f"Gera penalidade tarifária e perdas na transmissão."
            ),
            confianca=None,
            origem="heuristica",
        )

    # ── Regra R5 — Microfalta detectada (consumo zero inesperado) ───────────
    if consumo == 0.0 and perfil != "critico":
        return Acao(
            tipo="MICROFALTA_DETECTADA",
            urgencia="ALTA",
            zona_alvo=zona_id,
            descricao=f"Consumo zerado detectado — possível microfalta ou falha de medição",
            explicacao=(
                f"Regra R5: consumo_mw=0.0 em zona não-crítica. "
                f"Verificar medidor e continuidade do fornecimento (ANEEL — DEC/FEC)."
            ),
            confianca=None,
            origem="heuristica",
        )

    return None  # nenhuma emergência detectada

# ══════════════════════════════════════════════════════════════════
#  CAMADA 2 — XGBOOST
# ══════════════════════════════════════════════════════════════════


def extrair_instante_amostra(dados: dict) -> datetime:
    """Lê o relógio da simulação; usa o relógio local apenas como fallback explícito."""
    valor = dados.get("timestamp")
    if valor:
        try:
            return datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
        except ValueError:
            logging.warning("Timestamp inválido na amostra: %s", valor)
    return datetime.now()


def avaliar_xgboost(zona_id: str, dados: dict, modelo_xgb) -> tuple:
    """Estima, de forma experimental, o risco 30 minutos à frente."""
    instante = extrair_instante_amostra(dados)
    hora = instante.hour
    dados = dict(dados)
    dados["hora"]      = hora
    dados["hora_sin"]  = np.sin(2 * np.pi * hora / 24)
    dados["hora_cos"]  = np.cos(2 * np.pi * hora / 24)
    dados["dia_semana"]= instante.weekday()
    dados["anomalia_flag"] = 1 if dados.get("anomalia_tipo") else 0
    dados["evento_flag"]   = 1 if dados.get("evento") else 0

    X = np.array([[dados.get(f, 0.0) for f in FEATURES_XGB]])
    proba = modelo_xgb.predict_proba(X)[0]
    idx   = np.argmax(proba)

    risco      = CLASSES_RISCO[idx]
    confianca  = float(proba[idx])
    distribuicao = {CLASSES_RISCO[i]: round(float(p), 3) for i, p in enumerate(proba)}

    explicacao = (
        f"XGBoost estimou risco {risco} para 30 minutos à frente, com score bruto de {confianca*100:.1f}%. "
        f"Features de entrada: pct_carga={dados.get('pct_carga',0):.1f}%, "
        f"anomalia={'sim' if dados.get('anomalia_flag') else 'não'}, "
        f"temperatura={dados.get('clima_temp_c',0):.1f}°C. "
        f"Distribuição: {distribuicao}"
    )

    return risco, confianca, explicacao

# ══════════════════════════════════════════════════════════════════
#  CAMADA 3 — LSTM
# ══════════════════════════════════════════════════════════════════

def avaliar_lstm(zona_id: str, historico: list,
                 modelos_lstm: dict, scalers_zona: dict, device) -> tuple:
    """Prevê o consumo futuro e estima o risco nas próximas leituras."""
    if zona_id not in modelos_lstm or zona_id not in scalers_zona:
        return "DESCONHECIDO", [], "Modelo LSTM não disponível para esta zona."

    if len(historico) < JANELA_LSTM:
        faltam = JANELA_LSTM - len(historico)
        return "AGUARDANDO", [], f"Aguardando mais {faltam} leituras para ativar previsão LSTM."

    scalers = scalers_zona[zona_id]
    sx      = scalers["sx"]
    sy      = scalers["sy"]

    janela       = historico[-JANELA_LSTM:]
    janela_array = np.array([[l.get(f, 0.0) for f in FEATURES_LSTM] for l in janela])
    janela_norm  = sx.transform(janela_array)

    X_tensor = torch.FloatTensor(janela_norm).unsqueeze(0).to(device)

    with torch.no_grad():
        pred_norm = modelos_lstm[zona_id](X_tensor).cpu().numpy()

    pred_real = sy.inverse_transform(pred_norm)[0]
    pred_real = [max(0.0, float(v)) for v in pred_real]

    # Calcula risco futuro baseado no maior consumo previsto
    capacidade    = historico[-1].get("capacidade_mw", 1)
    max_previsto  = max(pred_real)
    pct_prevista  = (max_previsto / capacidade) * 100

    if pct_prevista >= 92:   risco_futuro = "CRÍTICO"
    elif pct_prevista >= 78: risco_futuro = "ALTO"
    elif pct_prevista >= 58: risco_futuro = "MÉDIO"
    else:                     risco_futuro = "BAIXO"

    explicacao = (
        f"LSTM prevê consumo de {pred_real[0]:.2f}→{pred_real[-1]:.2f} MW "
        f"nas próximas {HORIZONTE_LSTM} leituras (~{HORIZONTE_LSTM*5} min). "
        f"Pico previsto: {max_previsto:.2f} MW ({pct_prevista:.1f}% da capacidade). "
        f"Risco futuro estimado: {risco_futuro}."
    )

    return risco_futuro, pred_real, explicacao

# ══════════════════════════════════════════════════════════════════
#  CAMADA 4 — ALGORITMO GENÉTICO
# ══════════════════════════════════════════════════════════════════

def algoritmo_genetico(estados_zonas: dict,
                       capacidade_total: float,
                       geracoes: int = 50,
                       populacao: int = 30) -> dict:
    """
    Calcula um cenário experimental de distribuição entre zonas.
    Não representa fluxo de potência nem garante uma solução operacionalmente válida.
    Retorna: fração hipotética por zona.
    """
    zonas     = list(estados_zonas.keys())
    n         = len(zonas)

    if n == 0:
        return {}
    if n == 1:
        return {zonas[0]: 1.0}

    demandas  = np.array([estados_zonas[z].consumo_mw for z in zonas])
    riscos    = np.array([PRIORIDADE[estados_zonas[z].risco_atual] for z in zonas])

    def fitness(individuo):
        alocado   = individuo * capacidade_total
        penalidade = 0.0
        for i in range(n):
            cap_zona = estados_zonas[zonas[i]].capacidade_mw
            uso      = alocado[i] / cap_zona if cap_zona > 0 else 0
            # Penaliza zona acima de 90%
            if uso > 0.90:
                penalidade += (uso - 0.90) * 100 * riscos[i]
            # Penaliza subatendimento de zona crítica
            if riscos[i] >= 3 and alocado[i] < demandas[i]:
                penalidade += (demandas[i] - alocado[i]) * 50
            # Penaliza desperdício
            penalidade += max(0, alocado[i] - demandas[i]) * 0.5
        return penalidade

    # Inicializa população
    pop = [np.random.dirichlet(np.ones(n)) for _ in range(populacao)]

    for _ in range(geracoes):
        pop_fitness = [(ind, fitness(ind)) for ind in pop]
        pop_fitness.sort(key=lambda x: x[1])
        pop = [ind for ind, _ in pop_fitness[:populacao // 2]]

        filhos = []
        for _ in range(populacao // 2):
            p1, p2 = random.sample(pop, 2)
            ponto  = random.randint(1, n - 1)
            filho  = np.concatenate([p1[:ponto], p2[ponto:]])
            filho  = np.abs(filho + np.random.normal(0, 0.02, n))
            filho /= filho.sum()
            filhos.append(filho)
        pop.extend(filhos)

    melhor   = min(pop, key=fitness)
    alocacao = {zonas[i]: round(float(melhor[i]), 4) for i in range(n)}
    return alocacao

# ══════════════════════════════════════════════════════════════════
#  MOTOR DE DECISÃO PRINCIPAL
# ══════════════════════════════════════════════════════════════════

class MotorDecisao:
    def __init__(self):
        print(Fore.CYAN + Style.BRIGHT + """
╔══════════════════════════════════════════════════════════════════╗
║         CITYGRID BRAIN — MOTOR DE DECISÃO HÍBRIDO               ║
╚══════════════════════════════════════════════════════════════════╝""")

        self.modelo_xgb, self.modelos_lstm, self.scalers_zona, self.device = carregar_modelos()
        self.historicos   = {}
        self.log_acoes    = deque(maxlen=50)
        self.ciclo        = 0
        self.zonas_esperadas = max(len(self.modelos_lstm), 1)
        self.stats        = {"total_acoes": 0, "por_origem": {}, "por_urgencia": {}}
        print(Fore.GREEN + "\n  ✅ Motor de Decisão inicializado e pronto!\n")

    def processar_ciclo(self, leituras: list, ciclo_id: Optional[int] = None) -> list:
        """Processa um ciclo completo e retorna recomendações com métricas de latência."""
        t_inicio     = time.monotonic()
        self.ciclo   = ciclo_id if ciclo_id is not None else self.ciclo + 1
        acoes_ciclo  = []
        estados      = {}
        timestamps_zona = {}

        for dados in leituras:
            zona_id = dados["zona_id"]
            if dados.get("timestamp"):
                timestamps_zona[zona_id] = str(dados["timestamp"])

            # Atualiza histórico
            if zona_id not in self.historicos:
                self.historicos[zona_id] = deque(maxlen=JANELA_LSTM * 2)
            self.historicos[zona_id].append(dados)

            # ── Camada 1: Heurísticas ──────────────────────────────
            acao_heur = avaliar_heuristicas(zona_id, dados)

            # ── Camada 2: XGBoost ──────────────────────────────────
            risco_xgb, conf_xgb, expl_xgb = avaliar_xgboost(
                zona_id, dados, self.modelo_xgb
            )

            # ── Camada 3: LSTM ─────────────────────────────────────
            risco_futuro, consumo_previsto, expl_lstm = avaliar_lstm(
                zona_id,
                list(self.historicos[zona_id]),
                self.modelos_lstm,
                self.scalers_zona,
                self.device,
            )

            # ── Estado consolidado da zona ─────────────────────────
            estados[zona_id] = EstadoZona(
                zona_id         = zona_id,
                consumo_mw      = dados.get("consumo_mw", 0),
                capacidade_mw   = dados.get("capacidade_mw", 1),
                pct_carga       = dados.get("pct_carga", 0),
                risco_atual     = dados.get("risco", "BAIXO"),
                risco_xgb       = risco_xgb,
                risco_futuro    = risco_futuro,
                consumo_previsto= consumo_previsto,
            )

            # ── Decide ação baseada nas camadas ────────────────────
            if acao_heur:
                # Heurística tem prioridade absoluta
                acoes_ciclo.append(acao_heur)
                estados[zona_id].acoes.append(acao_heur)

            elif risco_xgb in ["CRÍTICO", "ALTO"]:
                acao = Acao(
                    tipo       = "REVISAR_RISCO_PREVISTO_XGB",
                    urgencia   = risco_xgb,
                    zona_alvo  = zona_id,
                    descricao  = f"XGBoost prevê risco {risco_xgb} em 30 min — recomendar revisão humana",
                    explicacao = expl_xgb,
                    confianca  = conf_xgb,
                    origem     = "xgboost",
                )
                acoes_ciclo.append(acao)
                estados[zona_id].acoes.append(acao)

            elif risco_futuro in ["CRÍTICO", "ALTO"] and estados[zona_id].risco_atual == "MÉDIO":
                acao = Acao(
                    tipo       = "ACAO_PREVENTIVA",
                    urgencia   = "MÉDIA",
                    zona_alvo  = zona_id,
                    descricao  = f"Previsão de risco {risco_futuro} em ~{HORIZONTE_LSTM*5} min — agir preventivamente",
                    explicacao = expl_lstm,
                    confianca  = None,
                    origem     = "lstm",
                )
                acoes_ciclo.append(acao)
                estados[zona_id].acoes.append(acao)

        # ── Camada 4: Algoritmo Genético ───────────────────────────
        # Só roda se houver zonas em risco que precisam redistribuição
        zonas_risco = {z: e for z, e in estados.items()
                       if e.risco_atual in ["ALTO", "CRÍTICO"]}

        if zonas_risco and len(estados) > 1:
            cap_total  = sum(e.capacidade_mw for e in estados.values())
            alocacao   = algoritmo_genetico(estados, cap_total)
            acao_ag    = Acao(
                tipo       = "EXPERIMENTO_DISTRIBUICAO_GENETICA",
                urgencia   = "MÉDIA",
                zona_alvo  = "TODAS",
                descricao  = f"Cenário hipotético calculado para {len(zonas_risco)} zonas em risco atual",
                explicacao = (f"Algoritmo genético gerou uma distribuição experimental de {cap_total:.1f} MW. "
                              f"O cálculo não modela fluxo de potência nem executa comandos. Frações: "
                              + ", ".join([f"{z.replace('zona_','')}: {v*100:.1f}%"
                                           for z, v in alocacao.items()])),
                confianca  = None,
                origem     = "genetico",
            )
            acoes_ciclo.append(acao_ag)

        # Calcula latência e atualiza estatísticas de desempenho
        latencia_ms = round((time.monotonic() - t_inicio) * 1000, 2)
        self.stats.setdefault("latencias_ms", [])
        self.stats["latencias_ms"].append(latencia_ms)
        if len(self.stats["latencias_ms"]) > 100:
            self.stats["latencias_ms"] = self.stats["latencias_ms"][-100:]
        lats = self.stats["latencias_ms"]
        self.stats["latencia_media_ms"] = round(sum(lats) / len(lats), 2)
        self.stats["latencia_max_ms"]   = round(max(lats), 2)
        self.stats["latencia_atual_ms"] = latencia_ms

        timestamp_ciclo = max(timestamps_zona.values()) if timestamps_zona else None
        for acao in acoes_ciclo:
            timestamp_acao = timestamps_zona.get(acao.zona_alvo, timestamp_ciclo)
            if timestamp_acao:
                acao.timestamp = timestamp_acao
            self.stats["total_acoes"] += 1
            self.stats["por_origem"][acao.origem] = self.stats["por_origem"].get(acao.origem, 0) + 1
            self.stats["por_urgencia"][acao.urgencia] = self.stats["por_urgencia"].get(acao.urgencia, 0) + 1
            self.log_acoes.appendleft(acao)
            self._salvar_log(acao, latencia_ms)

        return acoes_ciclo, estados

    def _salvar_log(self, acao: Acao, latencia_ms: float = 0.0):
        registro = asdict(acao)
        registro["latencia_ms"] = latencia_ms
        with open(LOG_DECISOES, "a", encoding="utf-8") as f:
            f.write(json.dumps(registro, ensure_ascii=False) + "\n")

    def exibir_dashboard(self, acoes: list, estados: dict):
        """Exibe dashboard completo no terminal."""
        os.system("cls" if os.name == "nt" else "clear")
        ts = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        print(Fore.CYAN + Style.BRIGHT + "╔" + "═"*72 + "╗")
        print(Fore.CYAN + "║" + f" CITYGRID BRAIN — MOTOR DE DECISÃO  |  Ciclo #{self.ciclo:>4}  |  {ts}".center(72) + "║")
        print(Fore.CYAN + "╚" + "═"*72 + "╝" + Style.RESET_ALL)

        # Estados das zonas
        COR = {"BAIXO":Fore.GREEN,"MÉDIO":Fore.YELLOW,"ALTO":Fore.RED,"CRÍTICO":Fore.RED+Style.BRIGHT,"AGUARDANDO":Fore.WHITE,"DESCONHECIDO":Fore.WHITE}

        print(f"\n{Fore.BLUE}━━ ESTADO DAS ZONAS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}")
        print(f"  {'ZONA':<22} {'MW':>7}  {'%':>5}  {'RISCO ATUAL':<12}  {'RISCO FUTURO':<12}  {'PREV. 1ª':>8}")
        print("  " + "─"*76)

        for zona_id, estado in sorted(estados.items()):
            cr = COR.get(estado.risco_atual, Fore.WHITE)
            cf = COR.get(estado.risco_futuro, Fore.WHITE)
            prev = f"{estado.consumo_previsto[0]:.2f} MW" if estado.consumo_previsto else "---"
            print(
                f"  {zona_id:<22} "
                f"{estado.consumo_mw:>5.2f}MW  "
                f"{estado.pct_carga:>5.1f}%  "
                f"{cr}{estado.risco_atual:<12}{Style.RESET_ALL}  "
                f"{cf}{estado.risco_futuro:<12}{Style.RESET_ALL}  "
                f"{prev:>8}"
            )

        # Ações do ciclo
        if acoes:
            print(f"\n{Fore.BLUE}━━ AÇÕES DESTE CICLO ({len(acoes)}) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}")
            URG_COR = {"CRÍTICA":Fore.RED+Style.BRIGHT,"ALTA":Fore.RED,"MÉDIA":Fore.YELLOW,"BAIXA":Fore.GREEN}
            for acao in acoes:
                cor = URG_COR.get(acao.urgencia, Fore.WHITE)
                print(f"  {cor}[{acao.urgencia:<8}]{Style.RESET_ALL}  "
                      f"{Fore.CYAN}[{acao.origem.upper():<10}]{Style.RESET_ALL}  "
                      f"{acao.zona_alvo:<20}  {acao.descricao}")
                print(f"  {Fore.WHITE}           └─ {acao.explicacao[:100]}...{Style.RESET_ALL}")

        # Stats
        print(f"\n{Fore.BLUE}━━ ESTATÍSTICAS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}")
        print(f"  Total de ações tomadas : {self.stats['total_acoes']}")
        print(f"  Por origem  : {self.stats['por_origem']}")
        print(f"  Por urgência: {self.stats['por_urgencia']}")
        lat = self.stats.get
        print(f"  Latência — atual: {lat('latencia_atual_ms', 0):.1f}ms | "
              f"média: {lat('latencia_media_ms', 0):.1f}ms | "
              f"máx: {lat('latencia_max_ms', 0):.1f}ms")
        print(f"  Log salvo em: {LOG_DECISOES}")
        print(Fore.CYAN + "─"*76 + Style.RESET_ALL)

# ══════════════════════════════════════════════════════════════════
#  INTEGRACAO COM KAFKA
# ══════════════════════════════════════════════════════════════════

def conectar_kafka(tentativas: int = 10) -> KafkaConsumer:
    if KafkaConsumer is None:
        print(Fore.RED + "  [ERRO] Dependências Kafka não instaladas." + Style.RESET_ALL)
        print("  Execute: pip install -r requirements-streaming.txt")
        raise SystemExit(1)
    for i in range(tentativas):
        try:
            consumer = KafkaConsumer(
                TOPICO_LEITURAS,
                bootstrap_servers=KAFKA_BOOTSTRAP,
                group_id=GRUPO_CONSUMIDOR,
                auto_offset_reset="latest",
                enable_auto_commit=True,
                auto_commit_interval_ms=5000,
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                key_deserializer=lambda k: k.decode("utf-8") if k else None,
                session_timeout_ms=30000,
                heartbeat_interval_ms=10000,
                max_poll_records=50,
                fetch_max_wait_ms=500,
            )
            print(Fore.GREEN + f"  [OK] Kafka conectado - topico: {TOPICO_LEITURAS}" + Style.RESET_ALL)
            return consumer
        except NoBrokersAvailable:
            print(Fore.YELLOW + f"  [AGUARDANDO] Kafka... tentativa {i+1}/{tentativas}" + Style.RESET_ALL)
            time.sleep(5)

    print(Fore.RED + "  [ERRO] Kafka indisponivel. Execute: docker-compose up -d" + Style.RESET_ALL)
    sys.exit(1)


def _adicionar_leitura(ciclos_pendentes: dict, dados: dict):
    ciclo_id = dados.get("ciclo")
    zona_id  = dados.get("zona_id")

    if ciclo_id is None or zona_id is None:
        logging.warning("Leitura ignorada por falta de ciclo ou zona_id: %s", dados)
        return

    try:
        ciclo_id = int(ciclo_id)
    except (TypeError, ValueError):
        logging.warning("Leitura ignorada por ciclo invalido: %s", dados)
        return

    agora = time.monotonic()
    bucket = ciclos_pendentes.setdefault(
        ciclo_id,
        {"leituras": {}, "atualizado_em": agora},
    )
    bucket["leituras"][zona_id] = dados
    bucket["atualizado_em"] = agora


def _ciclos_prontos(ciclos_pendentes: dict, zonas_esperadas: int) -> list:
    if not ciclos_pendentes:
        return []

    agora = time.monotonic()
    maior_ciclo = max(ciclos_pendentes)
    prontos = []

    for ciclo_id in sorted(ciclos_pendentes):
        bucket = ciclos_pendentes[ciclo_id]
        total_zonas = len(bucket["leituras"])
        idade = agora - bucket["atualizado_em"]
        ciclo_completo = total_zonas >= zonas_esperadas
        ciclo_antigo = ciclo_id < maior_ciclo
        ciclo_expirado = idade >= TEMPO_MAX_CICLO_S

        if ciclo_completo or (ciclo_antigo and total_zonas > 0) or ciclo_expirado:
            prontos.append(ciclo_id)

    return prontos


def _processar_ciclo_pendente(motor: MotorDecisao, ciclos_pendentes: dict, ciclo_id: int):
    bucket = ciclos_pendentes.pop(ciclo_id, None)
    if not bucket:
        return

    leituras = [bucket["leituras"][zona_id] for zona_id in sorted(bucket["leituras"])]
    acoes, estados = motor.processar_ciclo(leituras, ciclo_id=ciclo_id)
    motor.exibir_dashboard(acoes, estados)


def rodar_kafka():
    """Roda o motor integrado ao fluxo Kafka."""
    motor = MotorDecisao()
    consumer = conectar_kafka()
    ciclos_pendentes = {}
    print("  Motor operando em modo Kafka")
    print(f"  Kafka  -> {KAFKA_BOOTSTRAP} [{TOPICO_LEITURAS}]")
    print(f"  Zonas esperadas por ciclo: {motor.zonas_esperadas}")
    print("  Aguardando leituras... Ctrl+C para encerrar\n")

    try:
        while True:
            lotes = consumer.poll(timeout_ms=POLL_TIMEOUT_MS, max_records=50)

            for mensagens in lotes.values():
                for msg in mensagens:
                    _adicionar_leitura(ciclos_pendentes, msg.value)

            for ciclo_id in _ciclos_prontos(ciclos_pendentes, motor.zonas_esperadas):
                _processar_ciclo_pendente(motor, ciclos_pendentes, ciclo_id)

    except KeyboardInterrupt:
        for ciclo_id in sorted(ciclos_pendentes):
            _processar_ciclo_pendente(motor, ciclos_pendentes, ciclo_id)
        print(Fore.YELLOW + "\n  Motor encerrado." + Style.RESET_ALL)
    finally:
        consumer.close()

# ══════════════════════════════════════════════════════════════════
#  MODO OFFLINE — lê o JSONL diretamente (sem precisar do Kafka)
# ══════════════════════════════════════════════════════════════════

def rodar_arquivo():
    """Motor de decisão em modo offline — lê dados_citygrid.jsonl sem Kafka."""
    motor = MotorDecisao()
    ciclos_pendentes: dict = {}
    pos = 0

    # Começa do final do arquivo para não reprocessar dados antigos
    if os.path.exists(ARQUIVO_JSONL):
        with open(ARQUIVO_JSONL, "rb") as f:
            f.seek(0, 2)
            pos = f.tell()

    print(Fore.CYAN + Style.BRIGHT + "\n╔" + "═"*60 + "╗")
    print(Fore.CYAN + "║" + " CITYGRID BRAIN — MOTOR OFFLINE (sem Kafka) ".center(60) + "║")
    print(Fore.CYAN + "╚" + "═"*60 + "╝" + Style.RESET_ALL)
    print(f"  Fonte : {ARQUIVO_JSONL}")
    print(f"  Log   : {LOG_DECISOES}")
    print(f"  Zonas : {motor.zonas_esperadas} esperadas por ciclo")
    print("  Aguardando novos dados... Ctrl+C para encerrar\n")

    try:
        while True:
            if os.path.exists(ARQUIVO_JSONL):
                with open(ARQUIVO_JSONL, "r", encoding="utf-8") as f:
                    f.seek(pos)
                    novas = f.readlines()
                    pos   = f.tell()

                for linha in novas:
                    linha = linha.strip()
                    if linha:
                        try:
                            dados = json.loads(linha)
                            _adicionar_leitura(ciclos_pendentes, dados)
                        except json.JSONDecodeError:
                            pass

            for ciclo_id in _ciclos_prontos(ciclos_pendentes, motor.zonas_esperadas):
                _processar_ciclo_pendente(motor, ciclos_pendentes, ciclo_id)

            time.sleep(1)

    except KeyboardInterrupt:
        for ciclo_id in sorted(ciclos_pendentes):
            _processar_ciclo_pendente(motor, ciclos_pendentes, ciclo_id)
        print(Fore.YELLOW + "\n  Motor offline encerrado." + Style.RESET_ALL)


# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    if "--modo=arquivo" in sys.argv or "--offline" in sys.argv:
        rodar_arquivo()
    else:
        rodar_kafka()
