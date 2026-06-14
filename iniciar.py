"""
╔══════════════════════════════════════════════════════════════════╗
║         CITYGRID BRAIN — LANÇADOR ÚNICO (Modo Demo)             ║
║   Inicia todos os componentes com um único comando              ║
║                                                                 ║
║   Uso: python iniciar.py                                        ║
║                                                                 ║
║   O que este script faz:                                        ║
║     1. Inicia o Simulador IoT (gera dados a cada 5s)           ║
║     2. Inicia o Motor de Decisão offline (sem Kafka)           ║
║     3. Inicia o Backend FastAPI (http://localhost:8000)         ║
║     4. Abre o Dashboard no navegador automaticamente            ║
║                                                                 ║
║   Pressione Ctrl+C para encerrar tudo.                          ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import time
import signal
import subprocess
import webbrowser
from pathlib import Path

BASE = Path(__file__).parent

VERDE   = "\033[92m"
AMARELO = "\033[93m"
CIANO   = "\033[96m"
VERMELHO= "\033[91m"
RESET   = "\033[0m"
BOLD    = "\033[1m"

processos = []


def banner():
    print(CIANO + BOLD + """
╔══════════════════════════════════════════════════════════════════╗
║         CITYGRID BRAIN — SMART CITY ENERGY MONITOR              ║
║              Feira de Ciência — Modo Demo                       ║
╚══════════════════════════════════════════════════════════════════╝
""" + RESET)


def iniciar_processo(nome: str, cmd: list, esperar: float = 0) -> subprocess.Popen:
    print(f"  {CIANO}[INICIANDO]{RESET} {nome}...")
    if esperar > 0:
        time.sleep(esperar)
    p = subprocess.Popen(
        cmd,
        cwd=str(BASE),
        creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0,
    )
    processos.append((nome, p))
    print(f"  {VERDE}[OK]{RESET}       {nome} — PID {p.pid}")
    return p


def encerrar_tudo(sig=None, frame=None):
    print(f"\n  {AMARELO}Encerrando todos os componentes...{RESET}")
    for nome, p in reversed(processos):
        try:
            p.terminate()
            p.wait(timeout=5)
            print(f"  {AMARELO}[ENCERRADO]{RESET} {nome}")
        except Exception:
            p.kill()
    print(f"\n  {VERDE}CityGrid Brain encerrado com sucesso.{RESET}")
    sys.exit(0)


def aguardar_backend(timeout: int = 30) -> bool:
    """Aguarda o backend responder antes de abrir o browser."""
    import urllib.request
    for _ in range(timeout):
        try:
            urllib.request.urlopen("http://localhost:8000/", timeout=1)
            return True
        except Exception:
            time.sleep(1)
    return False


def main():
    banner()

    # Registra handler para Ctrl+C encerrar tudo limpo
    signal.signal(signal.SIGINT,  encerrar_tudo)
    signal.signal(signal.SIGTERM, encerrar_tudo)

    python = sys.executable

    print(f"{CIANO}━━ Iniciando componentes ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")

    # 1. Simulador IoT — gera leituras a cada 5s
    iniciar_processo(
        "Simulador IoT",
        [python, str(BASE / "simulador_iot.py")],
    )

    # 2. Motor de Decisão (modo offline, sem Kafka)
    iniciar_processo(
        "Motor de Decisão (offline)",
        [python, str(BASE / "motor_decisao.py"), "--modo=arquivo"],
        esperar=2,  # aguarda o simulador gerar as primeiras leituras
    )

    # 3. Backend FastAPI
    iniciar_processo(
        "Backend FastAPI  → http://localhost:8000",
        [python, str(BASE / "backend.py")],
        esperar=1,
    )

    print(f"\n  {CIANO}Aguardando backend inicializar{RESET}", end="", flush=True)
    ok = aguardar_backend(timeout=20)
    print()

    if ok:
        print(f"  {VERDE}[OK]{RESET}       Backend respondendo em http://localhost:8000")
    else:
        print(f"  {AMARELO}[AVISO]{RESET}    Backend demorou para responder — abrindo dashboard mesmo assim")

    # 4. Abre o dashboard no navegador
    dashboard = BASE / "front-end" / "dashboard.html"
    print(f"\n  {CIANO}[ABRINDO]{RESET}   Dashboard → {dashboard}")
    webbrowser.open(f"file:///{dashboard.as_posix()}")

    print(f"""
{CIANO}━━ CityGrid Brain rodando ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}

  Dashboard Web  →  aberto no navegador (front-end/dashboard.html)
  Backend API    →  http://localhost:8000
  Docs da API    →  http://localhost:8000/docs

  Dados gerados em tempo real a cada 5 segundos.
  O motor de decisão analisa cada ciclo e gera alertas.

  {AMARELO}Pressione Ctrl+C para encerrar tudo.{RESET}
""")

    # Monitora se algum processo morreu inesperadamente
    try:
        while True:
            for nome, p in processos:
                if p.poll() is not None:
                    print(f"  {VERMELHO}[ERRO]{RESET} {nome} encerrou inesperadamente (código {p.returncode})")
            time.sleep(5)
    except KeyboardInterrupt:
        encerrar_tudo()


if __name__ == "__main__":
    main()
