"""
╔══════════════════════════════════════════════════════════════════╗
║         CITYGRID BRAIN — GERADOR TURBO DE DADOS                 ║
║   Gera 100.000+ linhas em ~2 minutos                            ║
║   Simula múltiplos dias, horas, estações e eventos              ║
╚══════════════════════════════════════════════════════════════════╝

Diferente do simulador normal que usa o horário real do PC,
o modo turbo avança o tempo artificialmente cobrindo:
  - Todos os horários do dia (0h–23h)
  - Todos os dias da semana
  - Todas as estações do ano (verão, inverno, outono, primavera)
  - Todos os tipos de evento urbano
  - Todos os tipos de anomalia
  - Modos de bateria: CARREGANDO, STANDBY, DESCARGANDO
"""

import random
import math
import json
import csv
import os
import time
from datetime import datetime, timedelta
from collections import deque
from typing import Optional
from colorama import Fore, Style, init

init(autoreset=True)

# ══════════════════════════════════════════════════════════════════
#  CONFIGURAÇÃO
# ══════════════════════════════════════════════════════════════════

LINHAS_ALVO      = 100_000     # quantas linhas gerar
ARQUIVO_TURBO    = "dados_turbo.csv"
ARQUIVO_TURBO_JSONL = "dados_turbo.jsonl"
SALVAR_JSONL     = False       # True se quiser o JSONL também (mais pesado)
REPORT_CADA      = 5_000       # mostra progresso a cada N linhas

# ══════════════════════════════════════════════════════════════════
#  ZONAS (igual ao simulador original)
# ══════════════════════════════════════════════════════════════════

ZONAS = {
    "zona_norte":        {"nome_display":"Zona Norte",       "perfil":"residencial",         "capacidade_mw":18.0,  "consumo_base_mw":7.5,  "num_unidades":12000,"solar_mwp":1.2, "eolica_mw":0.0,"bateria_mwh":0.5, "num_eletropostos":8},
    "zona_sul":          {"nome_display":"Zona Sul",         "perfil":"comercial",            "capacidade_mw":30.0,  "consumo_base_mw":18.0, "num_unidades":3500, "solar_mwp":0.8, "eolica_mw":0.0,"bateria_mwh":2.0, "num_eletropostos":25},
    "zona_leste":        {"nome_display":"Zona Leste",       "perfil":"residencial_popular",  "capacidade_mw":15.0,  "consumo_base_mw":8.0,  "num_unidades":18000,"solar_mwp":0.2, "eolica_mw":0.0,"bateria_mwh":0.2, "num_eletropostos":3},
    "zona_oeste":        {"nome_display":"Zona Oeste",       "perfil":"industrial",           "capacidade_mw":60.0,  "consumo_base_mw":38.0, "num_unidades":450,  "solar_mwp":5.0, "eolica_mw":2.0,"bateria_mwh":8.0, "num_eletropostos":15},
    "zona_centro":       {"nome_display":"Centro",           "perfil":"misto",                "capacidade_mw":25.0,  "consumo_base_mw":14.0, "num_unidades":8000, "solar_mwp":0.4, "eolica_mw":0.0,"bateria_mwh":1.5, "num_eletropostos":40},
    "zona_hospitalar":   {"nome_display":"Zona Hospitalar",  "perfil":"critico",              "capacidade_mw":12.0,  "consumo_base_mw":8.5,  "num_unidades":120,  "solar_mwp":0.6, "eolica_mw":0.0,"bateria_mwh":3.0, "num_eletropostos":5},
    "zona_universitaria":{"nome_display":"Zona Universitária","perfil":"educacional",         "capacidade_mw":10.0,  "consumo_base_mw":4.5,  "num_unidades":600,  "solar_mwp":1.5, "eolica_mw":0.5,"bateria_mwh":1.0, "num_eletropostos":20},
    "zona_aeroporto":    {"nome_display":"Zona Aeroporto",   "perfil":"logistico",            "capacidade_mw":22.0,  "consumo_base_mw":12.0, "num_unidades":200,  "solar_mwp":3.0, "eolica_mw":0.8,"bateria_mwh":4.0, "num_eletropostos":50},
}

# ══════════════════════════════════════════════════════════════════
#  EVENTOS E ANOMALIAS
# ══════════════════════════════════════════════════════════════════

EVENTOS = [
    {"nome":"Onda de Calor (>38°C)", "prob":0.04,"fator":1.35,"zonas":"todas",                        "ciclos":8},
    {"nome":"Frente Fria (<10°C)",   "prob":0.03,"fator":1.20,"zonas":"todas",                        "ciclos":6},
    {"nome":"Show no Centro",        "prob":0.05,"fator":1.18,"zonas":["zona_centro"],                "ciclos":4},
    {"nome":"Feriado Nacional",      "prob":0.03,"fator":0.75,"zonas":"todas",                        "ciclos":24},
    {"nome":"Fim de Semana",         "prob":0.10,"fator":0.85,"zonas":"todas",                        "ciclos":48},
    {"nome":"Jogo de Futebol",       "prob":0.06,"fator":1.12,"zonas":"todas",                        "ciclos":3},
    {"nome":"Chuva Forte",           "prob":0.08,"fator":0.88,"zonas":"todas",                        "ciclos":2},
    {"nome":"Black Friday",          "prob":0.02,"fator":1.40,"zonas":["zona_sul","zona_centro"],     "ciclos":10},
    {"nome":"Manutenção Programada", "prob":0.02,"fator":0.60,"zonas":None,                           "ciclos":5},
]

ANOMALIAS = [
    {"tipo":"furto_energia",           "descricao":"Desvio de energia (gato) detectado",       "prob":0.06,"gravidade":"ALTA"},
    {"tipo":"sobrecarga_transformador","descricao":"Transformador operando acima de 95%",       "prob":0.04,"gravidade":"CRITICA"},
    {"tipo":"falha_medicao",           "descricao":"Medidor com leitura inconsistente",         "prob":0.03,"gravidade":"MEDIA"},
    {"tipo":"desequilibrio_fases",     "descricao":"Desequilíbrio de tensão entre fases > 3%", "prob":0.05,"gravidade":"ALTA"},
    {"tipo":"distorcao_harmonica",     "descricao":"THD de tensão acima do limite ANEEL (8%)", "prob":0.04,"gravidade":"ALTA"},
    {"tipo":"microfalta",              "descricao":"Interrupção momentânea < 3 min (ANEEL)",    "prob":0.02,"gravidade":"MEDIA"},
]

# ══════════════════════════════════════════════════════════════════
#  CURVAS DE CARGA HORÁRIA
# ══════════════════════════════════════════════════════════════════

CURVA_RESIDENCIAL  = {0:0.38,1:0.34,2:0.31,3:0.30,4:0.31,5:0.36,6:0.52,7:0.68,8:0.72,9:0.70,10:0.68,11:0.67,12:0.70,13:0.68,14:0.65,15:0.64,16:0.68,17:0.76,18:0.90,19:1.00,20:0.98,21:0.92,22:0.75,23:0.55}
CURVA_COMERCIAL    = {0:0.20,1:0.18,2:0.17,3:0.17,4:0.18,5:0.22,6:0.38,7:0.60,8:0.85,9:0.95,10:0.98,11:1.00,12:0.92,13:0.90,14:0.97,15:0.99,16:0.98,17:0.95,18:0.80,19:0.65,20:0.50,21:0.38,22:0.28,23:0.22}
CURVA_INDUSTRIAL   = {0:0.65,1:0.62,2:0.60,3:0.60,4:0.62,5:0.68,6:0.75,7:0.88,8:0.98,9:1.00,10:0.99,11:0.98,12:0.88,13:0.90,14:0.98,15:0.99,16:0.97,17:0.92,18:0.80,19:0.72,20:0.70,21:0.68,22:0.66,23:0.65}
CURVA_CRITICO      = {h:0.87 for h in range(24)}
CURVA_EDUCACIONAL  = {0:0.12,1:0.10,2:0.10,3:0.10,4:0.10,5:0.12,6:0.25,7:0.55,8:0.85,9:0.95,10:0.98,11:1.00,12:0.88,13:0.90,14:0.95,15:0.92,16:0.80,17:0.65,18:0.55,19:0.45,20:0.35,21:0.25,22:0.18,23:0.14}
CURVA_LOGISTICO    = {0:0.70,1:0.68,2:0.65,3:0.65,4:0.68,5:0.80,6:0.90,7:1.00,8:0.98,9:0.95,10:0.92,11:0.90,12:0.85,13:0.88,14:0.92,15:0.95,16:0.98,17:0.95,18:0.88,19:0.82,20:0.78,21:0.75,22:0.72,23:0.70}
CURVA_MISTO        = {h:(CURVA_RESIDENCIAL[h]+CURVA_COMERCIAL[h])/2 for h in range(24)}

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
#  ESTADO DO GERADOR TURBO
# ══════════════════════════════════════════════════════════════════

estado = {
    "ciclo":              0,
    "evento_ativo":       None,
    "evento_ciclos_rest": 0,
    "anomalias_ativas":   {},
}

# ══════════════════════════════════════════════════════════════════
#  FUNÇÕES — CLIMA COM TIMESTAMP FICTÍCIO
# ══════════════════════════════════════════════════════════════════

def gerar_clima(ts: datetime) -> dict:
    hora = ts.hour
    mes  = ts.month

    if mes in [12,1,2,3]:   base_temp = 28.5
    elif mes in [6,7,8]:     base_temp = 16.0
    elif mes in [4,5]:       base_temp = 22.0
    else:                     base_temp = 24.0

    if 6 <= hora <= 14:     var_hora = (hora - 6) * 0.9
    elif 14 < hora <= 20:   var_hora = (20 - hora) * 0.7
    else:                    var_hora = -3.0

    temperatura  = round(base_temp + var_hora + random.gauss(0, 1.2), 1)
    umidade      = round(random.uniform(55, 88), 1)
    vento_ms     = round(random.uniform(0.5, 6.5), 1)

    if 6 <= hora <= 18:
        irrad_max   = 950 if mes in [11,12,1,2] else 820
        irrad_base  = irrad_max * math.sin(math.pi * (hora - 6) / 12)
        irradiancia = round(max(0, irrad_base * random.uniform(0.65, 1.0)), 1)
    else:
        irradiancia = 0.0

    nebulosidade = round(random.uniform(10, 70), 1)
    irradiancia  = round(irradiancia * (1 - nebulosidade / 150), 1)

    if temperatura >= 27:
        e        = 6.105 * math.exp(17.27 * temperatura / (237.7 + temperatura))
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
#  FUNÇÕES — RENOVÁVEIS, QUALIDADE, VE, BATERIA
# ══════════════════════════════════════════════════════════════════

def gerar_solar(solar_mwp, irradiancia):
    if irradiancia <= 0 or solar_mwp <= 0: return 0.0
    return round(solar_mwp * (irradiancia / 1000) * random.uniform(0.76, 0.84), 4)

def gerar_eolica(eolica_mw, vento_ms):
    if eolica_mw <= 0 or vento_ms < 3.0 or vento_ms >= 25.0: return 0.0
    fator = 1.0 if vento_ms >= 12.0 else ((vento_ms - 3) / 9) ** 3
    return round(eolica_mw * fator * random.uniform(0.88, 0.97), 4)

def gerar_qualidade(pct_carga, anomalia):
    desvio_freq = -0.008 * (pct_carga - 50) + random.gauss(0, 0.03)
    frequencia  = round(max(59.2, min(60.8, 60.0 + desvio_freq)), 3)

    vnom  = 220.0
    var_v = -0.05 * (pct_carga / 100)
    fa    = round(vnom * (1 + var_v) + random.gauss(0, 1.5), 1)
    fb    = round(vnom * (1 + var_v) + random.gauss(0, 1.5), 1)
    fc    = round(vnom * (1 + var_v) + random.gauss(0, 1.5), 1)

    if anomalia and anomalia["tipo"] == "desequilibrio_fases":
        fa = round(fa * random.uniform(1.04, 1.08), 1)
        fc = round(fc * random.uniform(0.92, 0.96), 1)

    vmedia = round((fa + fb + fc) / 3, 1)
    deseq  = round(max(abs(fa-vmedia), abs(fb-vmedia), abs(fc-vmedia)) / vmedia * 100, 2)

    if anomalia and anomalia["tipo"] == "distorcao_harmonica":
        thd = round(random.uniform(8.5, 15.0), 2)
    elif pct_carga > 85:
        thd = round(random.uniform(4.5, 7.5), 2)
    else:
        thd = round(random.uniform(1.8, 4.2), 2)

    fp = round(random.uniform(0.82, 0.91) if pct_carga > 90 else random.uniform(0.92, 0.99), 3)

    return {"frequencia_hz":frequencia,"tensao_fase_a_v":fa,"tensao_fase_b_v":fb,
            "tensao_fase_c_v":fc,"tensao_media_v":vmedia,
            "desequilibrio_tensao_pct":deseq,"thd_tensao_pct":thd,"fator_potencia":fp}

def gerar_ve(num_postos, hora):
    if 18 <= hora <= 22:     taxa = random.uniform(0.40, 0.65)
    elif 8 <= hora <= 12:    taxa = random.uniform(0.25, 0.45)
    elif 0 <= hora <= 5:     taxa = random.uniform(0.05, 0.15)
    else:                     taxa = random.uniform(0.15, 0.35)
    em_uso     = round(num_postos * taxa)
    demanda_kw = round(em_uso * random.uniform(5.5, 7.8), 2)
    return {"ve_postos_total":num_postos,"ve_postos_em_uso":em_uso,
            "ve_ocupacao_pct":round(taxa*100,1),"ve_demanda_kw":demanda_kw}

def gerar_bateria(cap_mwh, pct_carga, hora):
    if 18 <= hora <= 21:      modo = "DESCARGANDO"
    elif 1 <= hora <= 6:      modo = "CARREGANDO"
    elif pct_carga > 85:      modo = "DESCARGANDO"
    elif pct_carga < 40:      modo = "CARREGANDO"
    else:                      modo = "STANDBY"
    soc  = round(max(10, min(95, random.uniform(35, 85))), 1)
    disp = round(cap_mwh * soc / 100, 3)
    return {"bat_capacidade_mwh":cap_mwh,"bat_soc_pct":soc,
            "bat_disponivel_mwh":disp,"bat_modo":modo}

# ══════════════════════════════════════════════════════════════════
#  EVENTOS E ANOMALIAS
# ══════════════════════════════════════════════════════════════════

def verificar_evento():
    if estado["evento_ativo"] is None:
        for ev in EVENTOS:
            if random.random() < ev["prob"]:
                estado["evento_ativo"]       = ev
                estado["evento_ciclos_rest"] = ev["ciclos"]
                break
    else:
        estado["evento_ciclos_rest"] -= 1
        if estado["evento_ciclos_rest"] <= 0:
            estado["evento_ativo"] = None

def verificar_anomalia(zona_id) -> Optional[dict]:
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
            return novo
    return None

# ══════════════════════════════════════════════════════════════════
#  CONSUMO E RISCO
# ══════════════════════════════════════════════════════════════════

def calcular_consumo(zona_id, zona, clima, anomalia, ts):
    hora   = ts.hour
    fator  = CURVAS[zona["perfil"]][hora]
    temp   = clima["temperatura_c"]

    if temp > 26:     fator_temp = 1 + 0.020 * (temp - 26)
    elif temp < 14:   fator_temp = 1 + 0.015 * (14 - temp)
    else:              fator_temp = 1.0

    fator_ev = 1.0
    ev = estado["evento_ativo"]
    if ev:
        zonas_af = ev["zonas"]
        if zonas_af == "todas" or (isinstance(zonas_af, list) and zona_id in zonas_af):
            fator_ev = ev["fator"]

    consumo = zona["consumo_base_mw"] * fator * fator_temp * fator_ev * random.gauss(1.0, 0.10)

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

def classificar_risco(pct, anomalia):
    if anomalia and anomalia["gravidade"] == "CRITICA": return "CRÍTICO"
    if pct >= 92: return "CRÍTICO"
    if pct >= 78: return "ALTO"
    if pct >= 58: return "MÉDIO"
    return "BAIXO"

# ══════════════════════════════════════════════════════════════════
#  GERAÇÃO DE LEITURA
# ══════════════════════════════════════════════════════════════════

def gerar_leitura(zona_id, zona, clima, anomalia, ts) -> dict:
    consumo  = calcular_consumo(zona_id, zona, clima, anomalia, ts)
    pct      = round((consumo / zona["capacidade_mw"]) * 100, 2)
    risco    = classificar_risco(pct, anomalia)

    solar    = gerar_solar(zona["solar_mwp"], clima["irradiancia_wm2"])
    eolica   = gerar_eolica(zona["eolica_mw"], clima["vento_ms"])
    gen_tot  = round(solar + eolica, 4)
    liq      = round(max(0, consumo - gen_tot), 4)
    autoprod = round(gen_tot / consumo * 100 if consumo > 0 else 0, 1)

    qual     = gerar_qualidade(pct, anomalia)
    ve       = gerar_ve(zona["num_eletropostos"], ts.hour)
    bat      = gerar_bateria(zona["bateria_mwh"], pct, ts.hour)

    fp   = qual["fator_potencia"]
    kw   = round(consumo * 1000, 2)
    kva  = round(kw / fp if fp > 0 else 0, 2)
    kvar = round(math.sqrt(max(0, kva**2 - kw**2)), 2)
    amp  = round(kw * 1000 / (math.sqrt(3) * 13800 * fp), 2)

    return {
        "zona_id":zona_id,"zona_nome":zona["nome_display"],"perfil":zona["perfil"],
        "timestamp":ts.strftime("%Y-%m-%dT%H:%M:%S"),"ciclo":estado["ciclo"],
        "consumo_mw":consumo,"consumo_liquido_mw":liq,
        "capacidade_mw":zona["capacidade_mw"],"pct_carga":pct,"risco":risco,
        "solar_mw":solar,"eolica_mw":eolica,"geracao_total_mw":gen_tot,"autoprod_pct":autoprod,
        "pot_ativa_kw":kw,"pot_aparente_kva":kva,"pot_reativa_kvar":kvar,"corrente_mt_a":amp,
        **qual, **ve, **bat,
        "evento":estado["evento_ativo"]["nome"] if estado["evento_ativo"] else None,
        "anomalia_tipo":anomalia["tipo"] if anomalia else None,
        "anomalia_grav":anomalia["gravidade"] if anomalia else None,
        "num_unidades":zona["num_unidades"],
        "hora_dia":ts.hour,"dia_semana":ts.weekday(),"mes":ts.month,
        "clima_temp_c":clima["temperatura_c"],"clima_umidade_pct":clima["umidade_pct"],
        "clima_vento_ms":clima["vento_ms"],"clima_irrad_wm2":clima["irradiancia_wm2"],
        "clima_sensacao_c":clima["sensacao_termica_c"],
    }

# ══════════════════════════════════════════════════════════════════
#  LOOP PRINCIPAL TURBO
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
    "hora_dia","dia_semana","mes",
    "clima_temp_c","clima_umidade_pct","clima_vento_ms","clima_irrad_wm2","clima_sensacao_c",
]

def gerar_turbo():
    print(Fore.CYAN + Style.BRIGHT + """
╔══════════════════════════════════════════════════════════════════╗
║         CITYGRID BRAIN — GERADOR TURBO DE DADOS                 ║
╚══════════════════════════════════════════════════════════════════╝
""")
    print(f"  Meta: {LINHAS_ALVO:,} linhas")
    print(f"  Arquivo: {ARQUIVO_TURBO}")
    print(f"  Iniciando...\n")

    # Timestamp fictício — começa 30 dias atrás e avança 5min por ciclo
    ts_atual   = datetime.now() - timedelta(days=30)
    delta_ts   = timedelta(minutes=5)

    total_linhas   = 0
    ciclos_alvo    = LINHAS_ALVO // len(ZONAS)
    inicio         = time.time()

    # Contadores para o relatório final
    contagem_risco    = {}
    contagem_anomalia = {}
    contagem_evento   = {}
    contagem_bat      = {}

    with open(ARQUIVO_TURBO, "w", newline="", encoding="utf-8") as f_csv:
        writer = csv.DictWriter(f_csv, fieldnames=CAMPOS_CSV, extrasaction="ignore")
        writer.writeheader()

        jsonl_file = None
        if SALVAR_JSONL:
            jsonl_file = open(ARQUIVO_TURBO_JSONL, "w", encoding="utf-8")

        for _ in range(ciclos_alvo):
            estado["ciclo"] += 1
            verificar_evento()
            clima = gerar_clima(ts_atual)

            for zona_id, zona in ZONAS.items():
                anomalia = verificar_anomalia(zona_id)
                leitura  = gerar_leitura(zona_id, zona, clima, anomalia, ts_atual)
                writer.writerow(leitura)
                total_linhas += 1

                # Contadores
                r = leitura["risco"]
                contagem_risco[r] = contagem_risco.get(r, 0) + 1
                if leitura["anomalia_tipo"]:
                    a = leitura["anomalia_tipo"]
                    contagem_anomalia[a] = contagem_anomalia.get(a, 0) + 1
                if leitura["evento"]:
                    e = leitura["evento"]
                    contagem_evento[e] = contagem_evento.get(e, 0) + 1
                b = leitura["bat_modo"]
                contagem_bat[b] = contagem_bat.get(b, 0) + 1

                if jsonl_file:
                    jsonl_file.write(json.dumps(leitura, ensure_ascii=False) + "\n")

            # Avança o tempo fictício
            ts_atual += delta_ts

            # Progresso
            if estado["ciclo"] % (REPORT_CADA // len(ZONAS)) == 0:
                elapsed  = time.time() - inicio
                pct      = total_linhas / LINHAS_ALVO * 100
                eta      = (elapsed / total_linhas) * (LINHAS_ALVO - total_linhas) if total_linhas > 0 else 0
                print(
                    f"  {Fore.CYAN}{pct:>5.1f}%{Style.RESET_ALL}  "
                    f"{total_linhas:>7,} linhas  "
                    f"| Data simulada: {ts_atual.strftime('%d/%m %Hh')}  "
                    f"| ETA: {eta:.0f}s"
                )

        if jsonl_file:
            jsonl_file.close()

    elapsed = time.time() - inicio

    print(Fore.GREEN + f"""
  ✅ CONCLUÍDO!
  ─────────────────────────────────────────────
  Linhas geradas : {total_linhas:,}
  Tempo total    : {elapsed:.1f}s
  Velocidade     : {total_linhas/elapsed:.0f} linhas/segundo
  Arquivo        : {ARQUIVO_TURBO}
  Tamanho aprox  : {os.path.getsize(ARQUIVO_TURBO)/1024/1024:.1f} MB

  DISTRIBUIÇÃO DE RISCO:""" + Style.RESET_ALL)
    for k, v in sorted(contagem_risco.items()):
        pct = v / total_linhas * 100
        print(f"    {k:<10}: {v:>7,} ({pct:.1f}%)")

    print(Fore.GREEN + "\n  ANOMALIAS DETECTADAS:" + Style.RESET_ALL)
    for k, v in sorted(contagem_anomalia.items(), key=lambda x: -x[1]):
        print(f"    {k:<30}: {v:>5,}")

    print(Fore.GREEN + "\n  EVENTOS ATIVOS:" + Style.RESET_ALL)
    for k, v in sorted(contagem_evento.items(), key=lambda x: -x[1]):
        print(f"    {k:<30}: {v:>5,}")

    print(Fore.GREEN + "\n  MODOS DE BATERIA:" + Style.RESET_ALL)
    for k, v in sorted(contagem_bat.items()):
        print(f"    {k:<15}: {v:>7,}")

    print(Fore.CYAN + f"""
  Próximo passo:
  → Atualize o arquivo no treinamento_ml.py:
    ARQUIVO_CSV = "{ARQUIVO_TURBO}"
  → Rode: python treinamento_ml.py
""" + Style.RESET_ALL)

# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    gerar_turbo()