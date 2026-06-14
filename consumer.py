"""
╔══════════════════════════════════════════════════════════════════╗
║           CITYGRID BRAIN — KAFKA CONSUMER + INFLUXDB            ║
║   Consome leituras do Kafka e persiste no InfluxDB              ║
╚══════════════════════════════════════════════════════════════════╝

Como funciona:
  1. Conecta no Kafka e subscreve o tópico citygrid-leituras
  2. Para cada mensagem recebida:
     - Deserializa o JSON
     - Monta um Point para o InfluxDB
     - Grava no bucket 'citygrid'
  3. Exibe estatísticas em tempo real no terminal

Estrutura no InfluxDB:
  Measurement : leitura_zona
  Tags        : zona_id, zona_nome, perfil, risco (indexados para query rápida)
  Fields      : todos os valores numéricos (consumo, tensão, frequência, etc.)
  Timestamp   : extraído do campo timestamp da mensagem
"""

import json
import time
import sys
from datetime import datetime, timezone
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from colorama import Fore, Style, init
from collections import defaultdict

init(autoreset=True)

# ══════════════════════════════════════════════════════════════════
#  CONFIGURAÇÃO
# ══════════════════════════════════════════════════════════════════

KAFKA_BOOTSTRAP    = "localhost:9092"
TOPICO_LEITURAS    = "citygrid-leituras"
TOPICO_ALERTAS     = "citygrid-alertas"
GRUPO_CONSUMIDOR   = "citygrid-consumer-group"

INFLUX_URL         = "http://localhost:8086"
INFLUX_TOKEN       = "citygrid-token-2024"
INFLUX_ORG         = "citygrid"
INFLUX_BUCKET      = "citygrid"

# ══════════════════════════════════════════════════════════════════
#  CAMPOS DO INFLUXDB
# ══════════════════════════════════════════════════════════════════

# Tags: valores categóricos — indexados, usados em filtros/agrupamentos
TAGS = ["zona_id", "zona_nome", "perfil", "risco", "bat_modo",
        "evento", "anomalia_tipo", "anomalia_grav"]

# Fields: valores numéricos — armazenados como séries temporais
FIELDS_FLOAT = [
    "consumo_mw", "consumo_liquido_mw", "capacidade_mw", "pct_carga",
    "solar_mw", "eolica_mw", "geracao_total_mw", "autoprod_pct",
    "pot_ativa_kw", "pot_aparente_kva", "pot_reativa_kvar", "corrente_mt_a",
    "frequencia_hz",
    "tensao_fase_a_v", "tensao_fase_b_v", "tensao_fase_c_v", "tensao_media_v",
    "desequilibrio_tensao_pct", "thd_tensao_pct", "fator_potencia",
    "ve_ocupacao_pct", "ve_demanda_kw",
    "bat_soc_pct", "bat_disponivel_mwh",
    "clima_temp_c", "clima_umidade_pct", "clima_vento_ms",
    "clima_irrad_wm2", "clima_sensacao_c",
]

FIELDS_INT = [
    "ciclo", "num_unidades",
    "ve_postos_total", "ve_postos_em_uso",
]

# ══════════════════════════════════════════════════════════════════
#  CONEXÃO KAFKA
# ══════════════════════════════════════════════════════════════════

def conectar_kafka(tentativas: int = 10) -> KafkaConsumer:
    for i in range(tentativas):
        try:
            consumer = KafkaConsumer(
                TOPICO_LEITURAS,
                bootstrap_servers=KAFKA_BOOTSTRAP,
                group_id=GRUPO_CONSUMIDOR,
                auto_offset_reset="latest",       # começa do mais recente
                enable_auto_commit=True,
                auto_commit_interval_ms=5000,
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                key_deserializer=lambda k: k.decode("utf-8") if k else None,
                session_timeout_ms=30000,
                heartbeat_interval_ms=10000,
                max_poll_records=50,              # processa até 50 msgs por poll
                fetch_max_wait_ms=500,
            )
            print(Fore.GREEN + f"  ✅ Kafka conectado — tópico: {TOPICO_LEITURAS}" + Style.RESET_ALL)
            return consumer
        except NoBrokersAvailable:
            print(Fore.YELLOW + f"  ⏳ Aguardando Kafka... tentativa {i+1}/{tentativas}" + Style.RESET_ALL)
            time.sleep(5)

    print(Fore.RED + "  ❌ Kafka indisponível. Execute: docker-compose up -d" + Style.RESET_ALL)
    sys.exit(1)

# ══════════════════════════════════════════════════════════════════
#  CONEXÃO INFLUXDB
# ══════════════════════════════════════════════════════════════════

def conectar_influx():
    try:
        client    = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        write_api = client.write_api(write_options=SYNCHRONOUS)
        # Testa a conexão
        client.ping()
        print(Fore.GREEN + f"  ✅ InfluxDB conectado em {INFLUX_URL}" + Style.RESET_ALL)
        print(Fore.GREEN + f"     Org: {INFLUX_ORG} | Bucket: {INFLUX_BUCKET}" + Style.RESET_ALL)
        return client, write_api
    except Exception as e:
        print(Fore.RED + f"  ❌ InfluxDB indisponível: {e}" + Style.RESET_ALL)
        print(Fore.YELLOW + "  👉 Execute: docker-compose up -d" + Style.RESET_ALL)
        sys.exit(1)

# ══════════════════════════════════════════════════════════════════
#  CONVERSÃO PARA POINT DO INFLUXDB
# ══════════════════════════════════════════════════════════════════

def montar_point(dados: dict) -> Point:
    """
    Converte um dict de leitura em um Point do InfluxDB.

    Measurement: leitura_zona
    Tags:        campos categóricos (indexados para filtros rápidos)
    Fields:      todos os valores numéricos (séries temporais)
    Timestamp:   extraído da mensagem (precisão em segundos)
    """
    point = Point("leitura_zona")

    # Tags — indexadas, usadas em GROUP BY e filtros
    for tag in TAGS:
        valor = dados.get(tag)
        if valor is not None:
            point = point.tag(tag, str(valor))
        else:
            point = point.tag(tag, "N/A")

    # Fields float
    for field in FIELDS_FLOAT:
        valor = dados.get(field)
        if valor is not None:
            try:
                point = point.field(field, float(valor))
            except (TypeError, ValueError):
                pass

    # Fields int
    for field in FIELDS_INT:
        valor = dados.get(field)
        if valor is not None:
            try:
                point = point.field(field, int(valor))
            except (TypeError, ValueError):
                pass

    # Timestamp da leitura original
    try:
        ts = datetime.strptime(dados["timestamp"], "%Y-%m-%dT%H:%M:%S")
        ts = ts.replace(tzinfo=timezone.utc)
        point = point.time(ts, WritePrecision.SECONDS)
    except Exception:
        point = point.time(datetime.now(timezone.utc), WritePrecision.SECONDS)

    return point

# ══════════════════════════════════════════════════════════════════
#  ESTATÍSTICAS EM MEMÓRIA
# ══════════════════════════════════════════════════════════════════

stats = {
    "total_msgs":      0,
    "total_escritas":  0,
    "erros":           0,
    "por_zona":        defaultdict(int),
    "por_risco":       defaultdict(int),
    "ultimo_ciclo":    0,
    "inicio":          datetime.now(),
}

def exibir_stats():
    elapsed = (datetime.now() - stats["inicio"]).seconds
    rate    = round(stats["total_msgs"] / elapsed, 2) if elapsed > 0 else 0
    print(
        f"\r  {Fore.CYAN}msgs: {stats['total_msgs']:>6}{Style.RESET_ALL}  "
        f"escritas: {Fore.GREEN}{stats['total_escritas']:>6}{Style.RESET_ALL}  "
        f"erros: {Fore.RED}{stats['erros']:>3}{Style.RESET_ALL}  "
        f"ciclo: {stats['ultimo_ciclo']:>4}  "
        f"taxa: {rate:.2f} msg/s  "
        f"CRÍTICO: {Fore.RED}{stats['por_risco']['CRÍTICO']:>3}{Style.RESET_ALL}  "
        f"ALTO: {Fore.YELLOW}{stats['por_risco']['ALTO']:>3}{Style.RESET_ALL}",
        end="", flush=True
    )

# ══════════════════════════════════════════════════════════════════
#  PROCESSAMENTO DE MENSAGEM
# ══════════════════════════════════════════════════════════════════

def processar_mensagem(dados: dict, write_api) -> bool:
    """Processa uma mensagem: converte e grava no InfluxDB."""
    try:
        point = montar_point(dados)
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)

        # Atualiza stats
        stats["total_escritas"] += 1
        stats["por_zona"][dados.get("zona_id", "?")] += 1
        stats["por_risco"][dados.get("risco", "?")] += 1
        stats["ultimo_ciclo"] = dados.get("ciclo", 0)

        return True
    except Exception as e:
        stats["erros"] += 1
        print(Fore.RED + f"\n  ❌ Erro ao gravar no InfluxDB: {e}" + Style.RESET_ALL)
        return False

# ══════════════════════════════════════════════════════════════════
#  LOOP PRINCIPAL
# ══════════════════════════════════════════════════════════════════

def iniciar_consumer():
    print(Fore.CYAN + Style.BRIGHT + """
╔══════════════════════════════════════════════════════════════════╗
║         CITYGRID BRAIN — KAFKA CONSUMER + INFLUXDB              ║
╚══════════════════════════════════════════════════════════════════╝
""")
    print("  Conectando aos serviços...")
    consumer            = conectar_kafka()
    influx_client, write_api = conectar_influx()

    print(f"""
  Pipeline ativo:
    Kafka    → {KAFKA_BOOTSTRAP}  [{TOPICO_LEITURAS}]
    InfluxDB → {INFLUX_URL}  [{INFLUX_BUCKET}]

  Para visualizar os dados:
    → Acesse http://localhost:8086
    → Login: admin / citygrid123
    → Bucket: citygrid

  Aguardando mensagens... Ctrl+C para encerrar
  {"─"*68}
""")

    try:
        for msg in consumer:
            stats["total_msgs"] += 1
            dados = msg.value

            if dados:
                processar_mensagem(dados, write_api)

            # Atualiza display a cada 8 mensagens
            if stats["total_msgs"] % 8 == 0:
                exibir_stats()

    except KeyboardInterrupt:
        print(Fore.YELLOW + f"""

  Consumer encerrado.
  Resumo final:
    → Mensagens recebidas : {stats['total_msgs']}
    → Escritas no InfluxDB: {stats['total_escritas']}
    → Erros               : {stats['erros']}
    → Zonas monitoradas   : {len(stats['por_zona'])}
""" + Style.RESET_ALL)

    finally:
        consumer.close()
        influx_client.close()

# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    iniciar_consumer()