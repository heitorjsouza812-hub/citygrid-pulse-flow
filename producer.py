"""
╔══════════════════════════════════════════════════════════════════╗
║           CITYGRID BRAIN — KAFKA PRODUCER                       ║
║     Publica leituras do simulador IoT no Apache Kafka           ║
╚══════════════════════════════════════════════════════════════════╝

Como funciona:
  1. Importa o simulador IoT
  2. A cada ciclo gera leituras de todas as zonas
  3. Serializa cada leitura em JSON
  4. Publica no tópico 'citygrid-leituras' do Kafka
  5. Consumer.py consome e salva no InfluxDB
"""

import json
import time
import sys
import os
from datetime import datetime
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable
from colorama import Fore, Style, init

# Importa o simulador do mesmo diretório
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import simulador_iot as sim

init(autoreset=True)

# ══════════════════════════════════════════════════════════════════
#  CONFIGURAÇÃO
# ══════════════════════════════════════════════════════════════════

KAFKA_BOOTSTRAP    = os.getenv("CITYGRID_KAFKA_BOOTSTRAP", "localhost:9092")
TOPICO_LEITURAS    = "citygrid-leituras"
TOPICO_ALERTAS     = "citygrid-alertas"
INTERVALO_SEGUNDOS = sim.INTERVALO_SEGUNDOS

# ══════════════════════════════════════════════════════════════════
#  CONEXÃO COM KAFKA
# ══════════════════════════════════════════════════════════════════

def conectar_kafka(tentativas: int = 10) -> KafkaProducer:
    """Tenta conectar ao Kafka com retries."""
    for i in range(tentativas):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP,
                value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                # Configurações de performance e confiabilidade
                acks="all",                  # aguarda confirmação de todos os brokers
                retries=3,                   # tenta 3x em caso de falha
                batch_size=16384,            # agrupa mensagens (16KB)
                linger_ms=10,                # aguarda 10ms para agrupar
                compression_type="gzip",     # comprime os dados
                max_block_ms=10000,          # timeout de 10s para publicar
            )
            print(Fore.GREEN + f"  ✅ Kafka conectado em {KAFKA_BOOTSTRAP}" + Style.RESET_ALL)
            return producer
        except NoBrokersAvailable:
            print(Fore.YELLOW + f"  ⏳ Kafka não disponível ainda... tentativa {i+1}/{tentativas}" + Style.RESET_ALL)
            time.sleep(5)

    print(Fore.RED + "  ❌ Não foi possível conectar ao Kafka. Verifique se o Docker está rodando." + Style.RESET_ALL)
    print(Fore.YELLOW + "  👉 Execute: docker-compose up -d" + Style.RESET_ALL)
    sys.exit(1)

# ══════════════════════════════════════════════════════════════════
#  PUBLICAÇÃO
# ══════════════════════════════════════════════════════════════════

def publicar_leitura(producer: KafkaProducer, leitura: dict):
    """Publica uma leitura no tópico do Kafka."""
    # Usa zona_id como chave para garantir ordenação por zona
    producer.send(
        topic=TOPICO_LEITURAS,
        key=leitura["zona_id"],
        value=leitura,
    )

def publicar_alertas(producer: KafkaProducer):
    """Publica alertas recentes num tópico separado."""
    for alerta in list(sim.estado["alertas"])[:3]:
        producer.send(
            topic=TOPICO_ALERTAS,
            key="alerta",
            value={
                "timestamp": sim.agora_simulado().isoformat(timespec="seconds"),
                **alerta
            }
        )


def exibir_status(ciclo: int, leituras: list, msgs_enviadas: int):
    """Exibe status resumido no terminal."""
    criticos = sum(1 for l in leituras if l["risco"] == "CRÍTICO")
    altos    = sum(1 for l in leituras if l["risco"] == "ALTO")
    anomalia = sum(1 for l in leituras if l["anomalia_tipo"])
    tot_mw   = round(sum(l["consumo_mw"] for l in leituras), 2)

    cor_c = Fore.RED + Style.BRIGHT if criticos else Fore.GREEN
    cor_a = Fore.RED if altos else Fore.GREEN

    print(
        f"  {Fore.CYAN}[Ciclo {ciclo:>4}]{Style.RESET_ALL} "
        f"{datetime.now().strftime('%H:%M:%S')}  │  "
        f"Total: {Fore.YELLOW}{tot_mw:>6.2f} MW{Style.RESET_ALL}  │  "
        f"Crítico: {cor_c}{criticos}{Style.RESET_ALL}  "
        f"Alto: {cor_a}{altos}{Style.RESET_ALL}  "
        f"Anomalia: {Fore.RED if anomalia else Fore.GREEN}{anomalia}{Style.RESET_ALL}  │  "
        f"Msgs enviadas: {Fore.CYAN}{msgs_enviadas}{Style.RESET_ALL}"
    )

# ══════════════════════════════════════════════════════════════════
#  LOOP PRINCIPAL
# ══════════════════════════════════════════════════════════════════

def iniciar_producer():
    print(Fore.CYAN + Style.BRIGHT + """
╔══════════════════════════════════════════════════════════════════╗
║           CITYGRID BRAIN — KAFKA PRODUCER                       ║
╚══════════════════════════════════════════════════════════════════╝
""")
    print(f"  Conectando ao Kafka em {KAFKA_BOOTSTRAP}...")
    producer      = conectar_kafka()
    msgs_enviadas = 0

    print(f"\n  Tópicos:")
    print(f"    → {TOPICO_LEITURAS}  (leituras das zonas)")
    print(f"    → {TOPICO_ALERTAS}   (alertas e anomalias)")
    print(f"\n  Publicando a cada {INTERVALO_SEGUNDOS}s | Ctrl+C para encerrar\n")
    print("  " + "─"*72)

    try:
        while True:
            sim.estado["ciclo"] += 1
            sim.verificar_evento()
            clima    = sim.gerar_clima()
            leituras = []

            for zona_id, zona in sim.ZONAS.items():
                leitura = sim.gerar_leitura(zona_id, zona, clima)
                publicar_leitura(producer, leitura)
                leituras.append(leitura)
                msgs_enviadas += 1

            # Publica alertas se houver
            if sim.estado["alertas"]:
                publicar_alertas(producer)

            # Garante que todas as mensagens foram enviadas
            producer.flush()

            exibir_status(sim.estado["ciclo"], leituras, msgs_enviadas)
            sim.avancar_tempo_simulado()
            time.sleep(INTERVALO_SEGUNDOS)

    except KeyboardInterrupt:
        print(Fore.YELLOW + f"\n\n  Producer encerrado. Total de mensagens publicadas: {msgs_enviadas}" + Style.RESET_ALL)
        producer.close()

# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    iniciar_producer()