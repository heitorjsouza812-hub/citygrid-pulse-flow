"""
╔══════════════════════════════════════════════════════════════════╗
║           CITYGRID BRAIN — SIMULADOR IoT AVANÇADO               ║
║        Smart City Energy Monitoring System v2.0                 ║
║                  Baseado em dados reais ANEEL                   ║
╚══════════════════════════════════════════════════════════════════╝

Referências técnicas utilizadas:
  - ANEEL PRODIST Módulo 8 (Qualidade de Energia)
  - ONS — Operador Nacional do Sistema Elétrico
  - ABNT NBR 5410 (Instalações elétricas de baixa tensão)
  - INMET — Dados climáticos reais do Brasil
  - Frequência nominal BR: 60 Hz
  - Tensão nominal BR: 127V / 220V (BT), 13,8 kV (MT)

Simula cidade brasileira de médio porte (~400k habitantes):
  - 8 zonas com perfis reais de consumo (MW)
  - Qualidade de energia (THD, frequência, desequilíbrio de fase)
  - Fontes renováveis (solar + eólica) por zona
  - Baterias de armazenamento por zona
  - Estações de recarga de VEs
  - Sistema de eventos urbanos (ondas de calor, feriados, shows)
  - Anomalias reais (furto de energia, sobrecarga, falha)
  - Exportação em JSONL e CSV
  - Dashboard completo em tempo real no terminal
"""

import random
import time
import json
import csv
import os
import math
from datetime import datetime
from collections import deque
from typing import Optional
from colorama import Fore, Style, init

init(autoreset=True)

# ══════════════════════════════════════════════════════════════════
#  CONFIGURAÇÃO GLOBAL
# ══════════════════════════════════════════════════════════════════

INTERVALO_SEGUNDOS = 5
SALVAR_JSONL       = True
SALVAR_CSV         = True
ARQUIVO_JSONL      = "dados_citygrid.jsonl"
ARQUIVO_CSV        = "dados_citygrid.csv"

# ══════════════════════════════════════════════════════════════════
#  ZONAS DA CIDADE — VALORES REAIS (cidade BR ~400k hab.)
# ══════════════════════════════════════════════════════════════════
#
# Referência: feeders de distribuição 13,8 kV típicos do Brasil
# Capacidade por zona: transformadores de 10–60 MVA por subestação
# Consumo médio residencial BR: ~180 kWh/mês por unidade (ANEEL 2023)

ZONAS = {
    "zona_norte": {
        "nome_display":     "Zona Norte",
        "perfil":           "residencial",
        "capacidade_mw":    18.0,
        "consumo_base_mw":  7.5,
        "num_unidades":     12000,
        "solar_mwp":        1.2,
        "eolica_mw":        0.0,
        "bateria_mwh":      0.5,
        "num_eletropostos": 8,
    },
    "zona_sul": {
        "nome_display":     "Zona Sul",
        "perfil":           "comercial",
        "capacidade_mw":    30.0,
        "consumo_base_mw":  18.0,
        "num_unidades":     3500,
        "solar_mwp":        0.8,
        "eolica_mw":        0.0,
        "bateria_mwh":      2.0,
        "num_eletropostos": 25,
    },
    "zona_leste": {
        "nome_display":     "Zona Leste",
        "perfil":           "residencial_popular",
        "capacidade_mw":    15.0,
        "consumo_base_mw":  8.0,
        "num_unidades":     18000,
        "solar_mwp":        0.2,
        "eolica_mw":        0.0,
        "bateria_mwh":      0.2,
        "num_eletropostos": 3,
    },
    "zona_oeste": {
        "nome_display":     "Zona Oeste",
        "perfil":           "industrial",
        "capacidade_mw":    60.0,
        "consumo_base_mw":  38.0,
        "num_unidades":     450,
        "solar_mwp":        5.0,
        "eolica_mw":        2.0,
        "bateria_mwh":      8.0,
        "num_eletropostos": 15,
    },
    "zona_centro": {
        "nome_display":     "Centro",
        "perfil":           "misto",
        "capacidade_mw":    25.0,
        "consumo_base_mw":  14.0,
        "num_unidades":     8000,
        "solar_mwp":        0.4,
        "eolica_mw":        0.0,
        "bateria_mwh":      1.5,
        "num_eletropostos": 40,
    },
    "zona_hospitalar": {
        "nome_display":     "Zona Hospitalar",
        "perfil":           "critico",
        "capacidade_mw":    12.0,
        "consumo_base_mw":  8.5,
        "num_unidades":     120,
        "solar_mwp":        0.6,
        "eolica_mw":        0.0,
        "bateria_mwh":      3.0,
        "num_eletropostos": 5,
    },
    "zona_universitaria": {
        "nome_display":     "Zona Universitária",
        "perfil":           "educacional",
        "capacidade_mw":    10.0,
        "consumo_base_mw":  4.5,
        "num_unidades":     600,
        "solar_mwp":        1.5,
        "eolica_mw":        0.5,
        "bateria_mwh":      1.0,
        "num_eletropostos": 20,
    },
    "zona_aeroporto": {
        "nome_display":     "Zona Aeroporto",
        "perfil":           "logistico",
        "capacidade_mw":    22.0,
        "consumo_base_mw":  12.0,
        "num_unidades":     200,
        "solar_mwp":        3.0,
        "eolica_mw":        0.8,
        "bateria_mwh":      4.0,
        "num_eletropostos": 50,
    },
}

# ══════════════════════════════════════════════════════════════════
#  EVENTOS URBANOS
# ══════════════════════════════════════════════════════════════════

EVENTOS = [
    {"nome": "Onda de Calor (>38°C)",  "prob": 0.04, "fator": 1.35, "zonas": "todas",                          "ciclos": 8},
    {"nome": "Frente Fria (<10°C)",    "prob": 0.03, "fator": 1.20, "zonas": "todas",                          "ciclos": 6},
    {"nome": "Show no Centro",         "prob": 0.05, "fator": 1.18, "zonas": ["zona_centro"],                   "ciclos": 4},
    {"nome": "Feriado Nacional",       "prob": 0.03, "fator": 0.75, "zonas": "todas",                          "ciclos": 24},
    {"nome": "Fim de Semana",          "prob": 0.28, "fator": 0.85, "zonas": "todas",                          "ciclos": 48},
    {"nome": "Jogo de Futebol",        "prob": 0.06, "fator": 1.12, "zonas": "todas",                          "ciclos": 3},
    {"nome": "Chuva Forte",            "prob": 0.08, "fator": 0.88, "zonas": "todas",                          "ciclos": 2},
    {"nome": "Black Friday",           "prob": 0.02, "fator": 1.40, "zonas": ["zona_sul", "zona_centro"],       "ciclos": 10},
    {"nome": "Manutenção Programada",  "prob": 0.02, "fator": 0.60, "zonas": None,                             "ciclos": 5},
]

# ══════════════════════════════════════════════════════════════════
#  ANOMALIAS — BASEADAS EM OCORRÊNCIAS REAIS BRASIL
# ══════════════════════════════════════════════════════════════════

ANOMALIAS = [
    {"tipo": "furto_energia",           "descricao": "Desvio de energia (gato) detectado",          "prob": 0.06, "gravidade": "ALTA"},
    {"tipo": "sobrecarga_transformador","descricao": "Transformador operando acima de 95%",          "prob": 0.04, "gravidade": "CRITICA"},
    {"tipo": "falha_medicao",           "descricao": "Medidor com leitura inconsistente",            "prob": 0.03, "gravidade": "MEDIA"},
    {"tipo": "desequilibrio_fases",     "descricao": "Desequilíbrio de tensão entre fases > 3%",    "prob": 0.05, "gravidade": "ALTA"},
    {"tipo": "distorcao_harmonica",     "descricao": "THD de tensão acima do limite ANEEL (8%)",    "prob": 0.04, "gravidade": "ALTA"},
    {"tipo": "microfalta",              "descricao": "Interrupção momentânea < 3 min (ANEEL)",       "prob": 0.02, "gravidade": "MEDIA"},
]

# ══════════════════════════════════════════════════════════════════
#  CURVAS DE CARGA HORÁRIA — DADOS ONS/ANEEL (% do pico diário)
# ══════════════════════════════════════════════════════════════════

CURVA_RESIDENCIAL = {
    0:0.38,1:0.34,2:0.31,3:0.30,4:0.31,5:0.36,
    6:0.52,7:0.68,8:0.72,9:0.70,10:0.68,11:0.67,
    12:0.70,13:0.68,14:0.65,15:0.64,16:0.68,17:0.76,
    18:0.90,19:1.00,20:0.98,21:0.92,22:0.75,23:0.55,
}
CURVA_COMERCIAL = {
    0:0.20,1:0.18,2:0.17,3:0.17,4:0.18,5:0.22,
    6:0.38,7:0.60,8:0.85,9:0.95,10:0.98,11:1.00,
    12:0.92,13:0.90,14:0.97,15:0.99,16:0.98,17:0.95,
    18:0.80,19:0.65,20:0.50,21:0.38,22:0.28,23:0.22,
}
CURVA_INDUSTRIAL = {
    0:0.65,1:0.62,2:0.60,3:0.60,4:0.62,5:0.68,
    6:0.75,7:0.88,8:0.98,9:1.00,10:0.99,11:0.98,
    12:0.88,13:0.90,14:0.98,15:0.99,16:0.97,17:0.92,
    18:0.80,19:0.72,20:0.70,21:0.68,22:0.66,23:0.65,
}
CURVA_CRITICO   = {h: 0.87 + random.uniform(-0.04, 0.04) for h in range(24)}
CURVA_EDUCACIONAL = {
    0:0.12,1:0.10,2:0.10,3:0.10,4:0.10,5:0.12,
    6:0.25,7:0.55,8:0.85,9:0.95,10:0.98,11:1.00,
    12:0.88,13:0.90,14:0.95,15:0.92,16:0.80,17:0.65,
    18:0.55,19:0.45,20:0.35,21:0.25,22:0.18,23:0.14,
}
CURVA_LOGISTICO = {
    0:0.70,1:0.68,2:0.65,3:0.65,4:0.68,5:0.80,
    6:0.90,7:1.00,8:0.98,9:0.95,10:0.92,11:0.90,
    12:0.85,13:0.88,14:0.92,15:0.95,16:0.98,17:0.95,
    18:0.88,19:0.82,20:0.78,21:0.75,22:0.72,23:0.70,
}
CURVA_MISTO = {h: (CURVA_RESIDENCIAL[h]+CURVA_COMERCIAL[h])/2 for h in range(24)}

CURVAS = {
    "residencial":         CURVA_RESIDENCIAL,
    "residencial_popular": CURVA_RESIDENCIAL,
    "comercial":           CURVA_COMERCIAL,
    "industrial":          CURVA_INDUSTRIAL,
    "critico":             CURVA_CRITICO,
    "educacional":         CURVA_EDUCACIONAL,
    "logistico":           CURVA_LOGISTICO,
    "misto":               CURVA_MISTO,
}

# ══════════════════════════════════════════════════════════════════
#  ESTADO GLOBAL
# ══════════════════════════════════════════════════════════════════

estado = {
    "ciclo":               0,
    "evento_ativo":        None,
    "evento_ciclos_rest":  0,
    "anomalias_ativas":    {},
    "alertas":             deque(maxlen=20),
    "gen_renovavel_mwh":   0.0,
}

# Estado persistente das baterias — SoC com inércia física real
# Inicializado com valores aleatórios realistas (50-75%) uma única vez
_estado_baterias: dict = {}

# ══════════════════════════════════════════════════════════════════
#  CLIMA — NORMAIS CLIMATOLÓGICAS INMET (Região SE/Brasil)
# ══════════════════════════════════════════════════════════════════

def gerar_clima() -> dict:
    hora = datetime.now().hour
    mes  = datetime.now().month

    if mes in [12,1,2,3]:   base_temp = 28.5
    elif mes in [6,7,8]:     base_temp = 16.0
    elif mes in [4,5]:       base_temp = 22.0
    else:                     base_temp = 24.0

    if 6 <= hora <= 14:     var_hora = (hora - 6) * 0.9
    elif 14 < hora <= 20:   var_hora = (20 - hora) * 0.7
    else:                    var_hora = -3.0

    temperatura = round(base_temp + var_hora + random.gauss(0, 1.2), 1)
    umidade     = round(random.uniform(55, 88), 1)
    vento_ms    = round(random.uniform(0.5, 6.5), 1)

    if 6 <= hora <= 18:
        irrad_max   = 950 if mes in [11,12,1,2] else 820
        irrad_base  = irrad_max * math.sin(math.pi * (hora - 6) / 12)
        irradiancia = round(max(0, irrad_base * random.uniform(0.65, 1.0)), 1)
    else:
        irradiancia = 0.0

    nebulosidade = round(random.uniform(10, 70), 1)
    irradiancia  = round(irradiancia * (1 - nebulosidade / 150), 1)

    if temperatura >= 27:
        e = 6.105 * math.exp(17.27 * temperatura / (237.7 + temperatura))
        sensacao = round(temperatura + 0.33 * (umidade / 100 * e) - 4.0, 1)
    else:
        sensacao = round(temperatura - 0.4 * (temperatura - 10) * (1 - umidade / 100), 1)

    return {
        "temperatura_c":      temperatura,
        "umidade_pct":        umidade,
        "vento_ms":           vento_ms,
        "irradiancia_wm2":    irradiancia,
        "nebulosidade_pct":   nebulosidade,
        "sensacao_termica_c": sensacao,
    }

# ══════════════════════════════════════════════════════════════════
#  GERAÇÃO RENOVÁVEL
# ══════════════════════════════════════════════════════════════════

def gerar_solar(solar_mwp: float, irradiancia: float) -> float:
    """
    P = Pico × (Irrad / 1000) × PR
    PR (Performance Ratio) típico BR: 0,76–0,84
    Ref: ABSOLAR — Atlas Brasileiro de Energia Solar
    """
    if irradiancia <= 0 or solar_mwp <= 0:
        return 0.0
    pr = random.uniform(0.76, 0.84)
    return round(solar_mwp * (irradiancia / 1000) * pr, 4)

def gerar_eolica(eolica_mw: float, vento_ms: float) -> float:
    """
    Cut-in: 3 m/s | Rated: 12 m/s | Cut-out: 25 m/s
    Curva de potência cúbica na faixa parcial
    """
    if eolica_mw <= 0 or vento_ms < 3.0 or vento_ms >= 25.0:
        return 0.0
    fator = 1.0 if vento_ms >= 12.0 else ((vento_ms - 3) / 9) ** 3
    return round(eolica_mw * fator * random.uniform(0.88, 0.97), 4)

# ══════════════════════════════════════════════════════════════════
#  QUALIDADE DE ENERGIA — ANEEL PRODIST MÓDULO 8
# ══════════════════════════════════════════════════════════════════

def gerar_qualidade(pct_carga: float, anomalia: Optional[dict]) -> dict:
    """
    Frequência: 59,9–60,1 Hz adequado (ANEEL)
    Tensão: 220 V ± 5% adequado / ±10% precário
    THD: <5% adequado / 5–8% precário / >8% crítico
    FP mínimo: 0,92 (Resolução ANEEL 456/2000)
    """
    # Frequência — queda proporcional à carga (fenômeno real)
    desvio_freq = -0.008 * (pct_carga - 50) + random.gauss(0, 0.03)
    frequencia  = round(max(59.2, min(60.8, 60.0 + desvio_freq)), 3)

    # Tensão trifásica (220V BT)
    vnom    = 220.0
    var_v   = -0.05 * (pct_carga / 100)
    fa = round(vnom * (1 + var_v) + random.gauss(0, 1.5), 1)
    fb = round(vnom * (1 + var_v) + random.gauss(0, 1.5), 1)
    fc = round(vnom * (1 + var_v) + random.gauss(0, 1.5), 1)

    if anomalia and anomalia["tipo"] == "desequilibrio_fases":
        fa = round(fa * random.uniform(1.04, 1.08), 1)
        fc = round(fc * random.uniform(0.92, 0.96), 1)

    vmedia = round((fa + fb + fc) / 3, 1)
    deseq  = round(max(abs(fa-vmedia), abs(fb-vmedia), abs(fc-vmedia)) / vmedia * 100, 2)

    # THD
    if anomalia and anomalia["tipo"] == "distorcao_harmonica":
        thd = round(random.uniform(8.5, 15.0), 2)
    elif pct_carga > 85:
        thd = round(random.uniform(4.5, 7.5), 2)
    else:
        thd = round(random.uniform(1.8, 4.2), 2)

    # Fator de potência
    fp = round(random.uniform(0.82, 0.91) if pct_carga > 90 else random.uniform(0.92, 0.99), 3)

    return {
        "frequencia_hz":              frequencia,
        "tensao_fase_a_v":            fa,
        "tensao_fase_b_v":            fb,
        "tensao_fase_c_v":            fc,
        "tensao_media_v":             vmedia,
        "desequilibrio_tensao_pct":   deseq,
        "thd_tensao_pct":             thd,
        "fator_potencia":             fp,
    }

# ══════════════════════════════════════════════════════════════════
#  VEÍCULOS ELÉTRICOS E BATERIAS
# ══════════════════════════════════════════════════════════════════

def gerar_ve(num_postos: int) -> dict:
    """
    Carregador L2 padrão BR: 7,2 kW
    Pico de carregamento: 18h–22h
    Taxa de ocupação típica: 20–65% dependendo da hora
    Ref: ABVE — Associação Brasileira do Veículo Elétrico
    """
    hora = datetime.now().hour
    if 18 <= hora <= 22:     taxa = random.uniform(0.40, 0.65)
    elif 8 <= hora <= 12:    taxa = random.uniform(0.25, 0.45)
    elif 0 <= hora <= 5:     taxa = random.uniform(0.05, 0.15)
    else:                     taxa = random.uniform(0.15, 0.35)

    em_uso      = round(num_postos * taxa)
    demanda_kw  = round(em_uso * random.uniform(5.5, 7.8), 2)

    return {
        "ve_postos_total":  num_postos,
        "ve_postos_em_uso": em_uso,
        "ve_ocupacao_pct":  round(taxa * 100, 1),
        "ve_demanda_kw":    demanda_kw,
    }

def gerar_bateria(cap_mwh: float, pct_carga: float, zona_id: str = "") -> dict:
    """
    SoC (State of Charge) com dinâmica física real — inércia de ciclo a ciclo.

    Estratégia de operação:
      - Carrega no vale de carga (1h–6h) e quando pct_carga < 40%
      - Descarrega no pico (18h–21h) e quando pct_carga > 85%
      - Standby com pequena deriva em outros momentos

    Parâmetros físicos:
      - Eficiência roundtrip Li-Ion: 93% (tipico para BESS)
      - Taxa de carga/descarga: 0,5C (50% da capacidade por hora)
      - Limites de SoC: 10% (mínimo) a 95% (máximo)

    Ref: ABNT NBR 16782, IEC 62619 (sistemas de armazenamento Li-Ion)
    """
    hora = datetime.now().hour
    if 18 <= hora <= 21:     modo = "DESCARGANDO"
    elif 1 <= hora <= 6:     modo = "CARREGANDO"
    elif pct_carga > 85:     modo = "DESCARGANDO"
    elif pct_carga < 40:     modo = "CARREGANDO"
    else:                    modo = "STANDBY"

    # Recupera SoC anterior ou inicializa com valor realista
    soc_atual = _estado_baterias.get(zona_id, random.uniform(50, 75))

    # Cálculo de variação de SoC com inércia física
    # Taxa de 0,5C sobre delta_t = INTERVALO_SEGUNDOS
    eficiencia = 0.93
    dt_h       = INTERVALO_SEGUNDOS / 3600.0  # fração de hora
    taxa_c     = 0.5 * cap_mwh  # MW (0,5C)

    if modo == "CARREGANDO":
        delta_soc = (taxa_c * dt_h * eficiencia / cap_mwh) * 100
        soc_novo  = min(95.0, soc_atual + delta_soc)
    elif modo == "DESCARGANDO":
        delta_soc = (taxa_c * dt_h / cap_mwh) * 100
        soc_novo  = max(10.0, soc_atual - delta_soc)
    else:  # STANDBY — pequena deriva térmica
        soc_novo = max(10.0, min(95.0, soc_atual + random.gauss(0, 0.05)))

    _estado_baterias[zona_id] = soc_novo
    disp = round(cap_mwh * soc_novo / 100, 3)

    return {
        "bat_capacidade_mwh": cap_mwh,
        "bat_soc_pct":        round(soc_novo, 1),
        "bat_disponivel_mwh": disp,
        "bat_modo":           modo,
    }

# ══════════════════════════════════════════════════════════════════
#  EVENTOS E ANOMALIAS
# ══════════════════════════════════════════════════════════════════

def verificar_evento():
    if estado["evento_ativo"] is None:
        for ev in EVENTOS:
            if random.random() < ev["prob"]:
                estado["evento_ativo"]      = ev
                estado["evento_ciclos_rest"] = ev["ciclos"]
                alertar("EVENTO", ev["nome"], "INFO")
                break
    else:
        estado["evento_ciclos_rest"] -= 1
        if estado["evento_ciclos_rest"] <= 0:
            estado["evento_ativo"] = None

def verificar_anomalia(zona_id: str) -> Optional[dict]:
    if zona_id in estado["anomalias_ativas"]:
        an = estado["anomalias_ativas"][zona_id]
        an["ciclos_rest"] -= 1
        if an["ciclos_rest"] <= 0:
            del estado["anomalias_ativas"][zona_id]
            return None
        return an
    for an in ANOMALIAS:
        if random.random() < an["prob"]:
            novo = dict(an)
            novo["ciclos_rest"] = random.randint(2, 6)
            estado["anomalias_ativas"][zona_id] = novo
            alertar(f"ANOMALIA [{zona_id}]", f"{an['descricao']}", an["gravidade"])
            return novo
    return None

def alertar(origem: str, msg: str, grav: str):
    estado["alertas"].appendleft({
        "ts":      datetime.now().strftime("%H:%M:%S"),
        "origem":  origem,
        "msg":     msg,
        "grav":    grav,
    })

# ══════════════════════════════════════════════════════════════════
#  CONSUMO
# ══════════════════════════════════════════════════════════════════

def calcular_consumo(zona_id: str, zona: dict, clima: dict, anomalia: Optional[dict]) -> float:
    hora   = datetime.now().hour
    fator  = CURVAS[zona["perfil"]][hora]
    temp   = clima["temperatura_c"]

    # Impacto térmico — cada 1°C acima de 26°C = +2% consumo (ar-condicionado)
    if temp > 26:     fator_temp = 1 + 0.020 * (temp - 26)
    elif temp < 14:   fator_temp = 1 + 0.015 * (14 - temp)
    else:              fator_temp = 1.0

    # Impacto de evento urbano
    fator_ev = 1.0
    ev = estado["evento_ativo"]
    if ev:
        zonas_af = ev["zonas"]
        if zonas_af == "todas" or (isinstance(zonas_af, list) and zona_id in zonas_af):
            fator_ev = ev["fator"]

    # Ruído gaussiano de 5% — redes elétricas reais têm inércia temporal
    # (reduzido de 10% para maior fidelidade física — ref: ONS)
    consumo = zona["consumo_base_mw"] * fator * fator_temp * fator_ev * random.gauss(1.0, 0.05)

    if anomalia:
        if anomalia["tipo"] == "furto_energia":
            consumo *= random.uniform(0.60, 0.85)
        elif anomalia["tipo"] == "sobrecarga_transformador":
            consumo *= random.uniform(1.10, 1.25)
        elif anomalia["tipo"] == "falha_medicao":
            consumo = random.choice([0.0, consumo * random.uniform(2.0, 4.0)])
        elif anomalia["tipo"] == "microfalta":
            consumo = 0.0

    return round(max(0.0, min(consumo, zona["capacidade_mw"])), 4)

def classificar_risco(pct: float, anomalia: Optional[dict]) -> str:
    if anomalia and anomalia["gravidade"] == "CRITICA":  return "CRÍTICO"
    if pct >= 92:  return "CRÍTICO"
    if pct >= 78:  return "ALTO"
    if pct >= 58:  return "MÉDIO"
    return "BAIXO"

# ══════════════════════════════════════════════════════════════════
#  LEITURA COMPLETA DE UMA ZONA
# ══════════════════════════════════════════════════════════════════

def gerar_leitura(zona_id: str, zona: dict, clima: dict) -> dict:
    anomalia  = verificar_anomalia(zona_id)
    consumo   = calcular_consumo(zona_id, zona, clima, anomalia)
    pct       = round((consumo / zona["capacidade_mw"]) * 100, 2)
    risco     = classificar_risco(pct, anomalia)

    solar     = gerar_solar(zona["solar_mwp"], clima["irradiancia_wm2"])
    eolica    = gerar_eolica(zona["eolica_mw"], clima["vento_ms"])
    gen_total = round(solar + eolica, 4)
    liq       = round(max(0, consumo - gen_total), 4)
    autoprod  = round(gen_total / consumo * 100 if consumo > 0 else 0, 1)

    qual      = gerar_qualidade(pct, anomalia)
    ve        = gerar_ve(zona["num_eletropostos"])
    bat       = gerar_bateria(zona["bateria_mwh"], pct, zona_id)

    fp  = qual["fator_potencia"]
    kw  = round(consumo * 1000, 2)
    kva = round(kw / fp if fp > 0 else 0, 2)
    kvar= round(math.sqrt(max(0, kva**2 - kw**2)), 2)
    amp = round(kw * 1000 / (math.sqrt(3) * 13800 * fp), 2)

    if risco in ["ALTO", "CRÍTICO"]:
        alertar(f"RISCO [{zona['nome_display']}]", f"Carga em {pct}% da capacidade", risco)

    estado["gen_renovavel_mwh"] += gen_total * (INTERVALO_SEGUNDOS / 3600)

    return {
        "zona_id":              zona_id,
        "zona_nome":            zona["nome_display"],
        "perfil":               zona["perfil"],
        "timestamp":            datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "ciclo":                estado["ciclo"],
        "consumo_mw":           consumo,
        "consumo_liquido_mw":   liq,
        "capacidade_mw":        zona["capacidade_mw"],
        "pct_carga":            pct,
        "risco":                risco,
        "solar_mw":             solar,
        "eolica_mw":            eolica,
        "geracao_total_mw":     gen_total,
        "autoprod_pct":         autoprod,
        "pot_ativa_kw":         kw,
        "pot_aparente_kva":     kva,
        "pot_reativa_kvar":     kvar,
        "corrente_mt_a":        amp,
        **qual,
        **ve,
        **bat,
        "evento":               estado["evento_ativo"]["nome"] if estado["evento_ativo"] else None,
        "anomalia_tipo":        anomalia["tipo"] if anomalia else None,
        "anomalia_grav":        anomalia["gravidade"] if anomalia else None,
        "num_unidades":         zona["num_unidades"],
        "clima_temp_c":         clima["temperatura_c"],
        "clima_umidade_pct":    clima["umidade_pct"],
        "clima_vento_ms":       clima["vento_ms"],
        "clima_irrad_wm2":      clima["irradiancia_wm2"],
        "clima_sensacao_c":     clima["sensacao_termica_c"],
    }

# ══════════════════════════════════════════════════════════════════
#  EXPORTAÇÃO
# ══════════════════════════════════════════════════════════════════

CAMPOS_CSV = [
    "timestamp","ciclo","zona_id","zona_nome","perfil",
    "consumo_mw","consumo_liquido_mw","capacidade_mw","pct_carga","risco",
    "solar_mw","eolica_mw","geracao_total_mw","autoprod_pct",
    "pot_ativa_kw","pot_aparente_kva","pot_reativa_kvar","corrente_mt_a",
    "frequencia_hz","tensao_fase_a_v","tensao_fase_b_v","tensao_fase_c_v",
    "tensao_media_v","desequilibrio_tensao_pct","thd_tensao_pct","fator_potencia",
    "ve_postos_total","ve_postos_em_uso","ve_ocupacao_pct","ve_demanda_kw",
    "bat_capacidade_mwh","bat_soc_pct","bat_disponivel_mwh","bat_modo",
    "evento","anomalia_tipo","anomalia_grav","num_unidades",
    "clima_temp_c","clima_umidade_pct","clima_vento_ms","clima_irrad_wm2","clima_sensacao_c",
]

def salvar(leitura: dict):
    if SALVAR_JSONL:
        with open(ARQUIVO_JSONL, "a", encoding="utf-8") as f:
            f.write(json.dumps(leitura, ensure_ascii=False) + "\n")
    if SALVAR_CSV:
        novo = not os.path.exists(ARQUIVO_CSV)
        with open(ARQUIVO_CSV, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=CAMPOS_CSV, extrasaction="ignore")
            if novo: w.writeheader()
            w.writerow(leitura)

# ══════════════════════════════════════════════════════════════════
#  DASHBOARD TERMINAL
# ══════════════════════════════════════════════════════════════════

COR = {
    "BAIXO":   Fore.GREEN,
    "MÉDIO":   Fore.YELLOW,
    "ALTO":    Fore.RED,
    "CRÍTICO": Fore.RED + Style.BRIGHT,
    "INFO":    Fore.CYAN,
    "MEDIA":   Fore.YELLOW,
    "ALTA":    Fore.RED,
    "CRITICA": Fore.RED + Style.BRIGHT,
}

def barra(pct: float, w: int = 18) -> str:
    n   = int(pct / 100 * w)
    cor = COR.get("CRÍTICO" if pct>=92 else "ALTO" if pct>=78 else "MÉDIO" if pct>=58 else "BAIXO", Fore.GREEN)
    return f"{cor}{'█'*n}{'░'*(w-n)}{Style.RESET_ALL}"

def dashboard(leituras: list, clima: dict):
    os.system("cls" if os.name == "nt" else "clear")
    ts = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    # Cabeçalho
    print(Fore.CYAN + Style.BRIGHT + "╔" + "═"*76 + "╗")
    print(Fore.CYAN + "║" + " CITYGRID BRAIN — MONITOR DE REDE ELÉTRICA URBANA".center(76) + "║")
    print(Fore.CYAN + "║" + f" Ciclo #{estado['ciclo']:>4}   {ts}   Cidade BR ~400k hab.".center(76) + "║")
    print(Fore.CYAN + "╚" + "═"*76 + "╝" + Style.RESET_ALL)

    # Clima
    print(f"\n{Fore.BLUE}━━ CLIMA (INMET) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}")
    print(
        f"  🌡  {clima['temperatura_c']:>5.1f}°C  "
        f"Sensação: {clima['sensacao_termica_c']:>5.1f}°C   "
        f"💧 {clima['umidade_pct']:>4.1f}%   "
        f"💨 {clima['vento_ms']:>4.1f} m/s   "
        f"☀️  {clima['irradiancia_wm2']:>5.1f} W/m²   "
        f"☁  {clima['nebulosidade_pct']:>4.1f}%"
    )

    ev = estado["evento_ativo"]
    if ev:
        print(f"  {Fore.MAGENTA}⚡ EVENTO: {ev['nome']}  ×{ev['fator']}  "
              f"({estado['evento_ciclos_rest']} ciclos restantes){Style.RESET_ALL}")

    # Zonas
    print(f"\n{Fore.BLUE}━━ ZONAS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}")
    print(f"  {'ZONA':<22} {'MW':>7}  {'BARRA':<20}  {'%':>5}  {'SOLAR':>7}  {'FP':>5}  {'THD':>5}  {'RISCO':<9}  VE")
    print("  " + "─"*92)
    for l in leituras:
        cor   = COR.get(l["risco"], Fore.WHITE)
        anom  = f" {Fore.RED}⚠{Style.RESET_ALL}" if l["anomalia_tipo"] else ""
        solar = f"{l['solar_mw']*1000:>5.0f}kW" if l["solar_mw"] > 0 else "   ---"
        print(
            f"  {l['zona_nome']:<22} "
            f"{l['consumo_mw']:>5.2f}MW  "
            f"{barra(l['pct_carga'])}  "
            f"{cor}{l['pct_carga']:>5.1f}%{Style.RESET_ALL}  "
            f"{solar}  "
            f"{l['fator_potencia']:>5.3f}  "
            f"{l['thd_tensao_pct']:>4.1f}%  "
            f"{cor}{l['risco']:<9}{Style.RESET_ALL}  "
            f"{l['ve_postos_em_uso']:>2}🔌{anom}"
        )

    # Resumo cidade
    tot_mw    = sum(l["consumo_mw"] for l in leituras)
    tot_renov = sum(l["geracao_total_mw"] for l in leituras)
    pct_renov = round(tot_renov / tot_mw * 100, 1) if tot_mw > 0 else 0
    tot_ve    = sum(l["ve_demanda_kw"] for l in leituras)
    n_anom    = sum(1 for l in leituras if l["anomalia_tipo"])

    print(f"\n{Fore.BLUE}━━ RESUMO CIDADE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}")
    print(
        f"  ⚡ Consumo total: {Fore.YELLOW}{tot_mw:.2f} MW{Style.RESET_ALL}   "
        f"🌞 Renovável: {Fore.GREEN}{tot_renov:.3f} MW ({pct_renov}%){Style.RESET_ALL}   "
        f"🔌 VE: {tot_ve:.1f} kW   "
        f"📦 Renov. acum: {estado['gen_renovavel_mwh']:.4f} MWh   "
        f"⚠️  Anomalias: {Fore.RED if n_anom else Fore.GREEN}{n_anom}{Style.RESET_ALL}"
    )

    # Qualidade ANEEL
    print(f"\n{Fore.BLUE}━━ QUALIDADE DE ENERGIA (ANEEL PRODIST M8) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}")
    print(f"  {'ZONA':<22} {'Hz':>8}  {'V médio':>8}  {'Deseq%':>7}  {'THD%':>6}  {'FP':>6}  STATUS")
    print("  " + "─"*72)
    for l in leituras:
        ok_f  = 59.9 <= l["frequencia_hz"] <= 60.1
        ok_t  = l["thd_tensao_pct"] < 5.0
        ok_fp = l["fator_potencia"] >= 0.92
        ok_d  = l["desequilibrio_tensao_pct"] < 2.0

        if ok_f and ok_t and ok_fp and ok_d:      st = f"{Fore.GREEN}ADEQUADO{Style.RESET_ALL}"
        elif not ok_t or not ok_fp or not ok_f:   st = f"{Fore.RED}PRECÁRIO{Style.RESET_ALL}"
        else:                                       st = f"{Fore.YELLOW}ATENÇÃO{Style.RESET_ALL}"

        cf = Fore.GREEN if ok_f else Fore.RED
        ct = Fore.GREEN if ok_t else (Fore.YELLOW if l["thd_tensao_pct"] < 8 else Fore.RED)
        cp = Fore.GREEN if ok_fp else Fore.RED

        print(
            f"  {l['zona_nome']:<22} "
            f"{cf}{l['frequencia_hz']:>8.3f}{Style.RESET_ALL}  "
            f"{l['tensao_media_v']:>8.1f}V  "
            f"{l['desequilibrio_tensao_pct']:>7.2f}%  "
            f"{ct}{l['thd_tensao_pct']:>6.1f}%{Style.RESET_ALL}  "
            f"{cp}{l['fator_potencia']:>6.3f}{Style.RESET_ALL}  "
            f"{st}"
        )

    # Alertas
    if estado["alertas"]:
        print(f"\n{Fore.BLUE}━━ ALERTAS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}")
        for al in list(estado["alertas"])[:6]:
            cor = COR.get(al["grav"], Fore.WHITE)
            print(f"  {Fore.WHITE}{al['ts']}{Style.RESET_ALL}  {cor}[{al['grav']:<8}]{Style.RESET_ALL}  {al['origem']:<30} {al['msg']}")

    print(f"\n{Fore.CYAN}  Dados: {ARQUIVO_JSONL} + {ARQUIVO_CSV}   |   Ctrl+C para encerrar{Style.RESET_ALL}")
    print(Fore.CYAN + "─"*78 + Style.RESET_ALL)

# ══════════════════════════════════════════════════════════════════
#  LOOP PRINCIPAL
# ══════════════════════════════════════════════════════════════════

def iniciar():
    print(Fore.CYAN + Style.BRIGHT + """
╔══════════════════════════════════════════════════════════════════╗
║         CITYGRID BRAIN — SIMULADOR IoT AVANÇADO v2.0            ║
║   8 zonas | Dados reais ANEEL | Renováveis | VE | Anomalias     ║
║   Iniciando sensores... aguarde                                  ║
╚══════════════════════════════════════════════════════════════════╝
""")
    time.sleep(1.5)

    try:
        while True:
            estado["ciclo"] += 1
            verificar_evento()
            clima    = gerar_clima()
            leituras = []

            for zona_id, zona in ZONAS.items():
                l = gerar_leitura(zona_id, zona, clima)
                leituras.append(l)
                salvar(l)

            dashboard(leituras, clima)
            time.sleep(INTERVALO_SEGUNDOS)

    except KeyboardInterrupt:
        print(Fore.YELLOW + f"""
  Simulador encerrado com sucesso.
  → {ARQUIVO_JSONL}
  → {ARQUIVO_CSV}
""")

if __name__ == "__main__":
    iniciar()