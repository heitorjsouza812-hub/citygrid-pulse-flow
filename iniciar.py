"""Lançador verificável do modo de demonstração local do CityGrid Brain.

Fluxo canônico:
    simulador sintético -> JSONL -> motor de recomendações -> FastAPI -> React

O modo principal não depende de Kafka, InfluxDB, Grafana ou internet.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

BASE = Path(__file__).resolve().parent
API_URL = "http://127.0.0.1:8000"
DASHBOARD_URL = "http://127.0.0.1:5173"

VERDE = "\033[92m"
AMARELO = "\033[93m"
CIANO = "\033[96m"
VERMELHO = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"

processos: list[tuple[str, subprocess.Popen]] = []
encerrando = False


def banner() -> None:
    print(
        CIANO
        + BOLD
        + """
╔══════════════════════════════════════════════════════════════════╗
║             CITYGRID BRAIN — DEMONSTRAÇÃO CIENTÍFICA             ║
║       dados sintéticos · simulação acelerada · modo local        ║
╚══════════════════════════════════════════════════════════════════╝
"""
        + RESET
    )


def verificar_pre_requisitos() -> list[str]:
    erros: list[str] = []
    arquivos = [
        "simulador_iot.py",
        "motor_decisao.py",
        "backend.py",
        "package.json",
        "modelos/xgboost_risco.json",
    ]
    for relativo in arquivos:
        if not (BASE / relativo).exists():
            erros.append(f"arquivo ausente: {relativo}")

    lstms = list((BASE / "modelos").glob("lstm_*.pt"))
    scalers = list((BASE / "modelos").glob("scaler_*.pkl"))
    if len(lstms) != 8 or len(scalers) != 8:
        erros.append(
            f"artefatos LSTM incompletos: {len(lstms)} modelos e {len(scalers)} scalers; esperado 8 de cada"
        )

    for modulo in ("numpy", "pandas", "torch", "xgboost", "fastapi", "uvicorn"):
        if importlib.util.find_spec(modulo) is None:
            erros.append(f"dependência Python ausente: {modulo}")

    if shutil.which("npm") is None and shutil.which("npm.cmd") is None:
        erros.append("npm não encontrado no PATH")
    if not (BASE / "node_modules").is_dir():
        erros.append("node_modules ausente; execute: npm install")

    return erros


def iniciar_processo(nome: str, cmd: list[str], esperar: float = 0) -> subprocess.Popen:
    print(f"  {CIANO}[INICIANDO]{RESET} {nome}...")
    if esperar:
        time.sleep(esperar)
    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NEW_CONSOLE
    processo = subprocess.Popen(cmd, cwd=str(BASE), creationflags=flags)
    processos.append((nome, processo))
    print(f"  {VERDE}[OK]{RESET}       {nome} — PID {processo.pid}")
    return processo


def encerrar_tudo(_sig=None, _frame=None, codigo: int = 0) -> None:
    global encerrando
    if encerrando:
        return
    encerrando = True
    print(f"\n  {AMARELO}Encerrando todos os componentes...{RESET}")
    for nome, processo in reversed(processos):
        if processo.poll() is not None:
            continue
        try:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(processo.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            else:
                processo.terminate()
                processo.wait(timeout=5)
            print(f"  {AMARELO}[ENCERRADO]{RESET} {nome}")
        except Exception:
            processo.kill()
    print(f"\n  {VERDE}CityGrid Brain encerrado.{RESET}")
    raise SystemExit(codigo)


def aguardar_url(url: str, timeout: int = 30) -> bool:
    limite = time.monotonic() + timeout
    while time.monotonic() < limite:
        try:
            with urllib.request.urlopen(url, timeout=1) as resposta:
                if 200 <= resposta.status < 500:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Inicia a demonstração local do CityGrid Brain")
    parser.add_argument(
        "--check",
        action="store_true",
        help="verifica pré-requisitos e sai sem iniciar processos",
    )
    parser.add_argument(
        "--sem-navegador",
        action="store_true",
        help="não abre o dashboard automaticamente",
    )
    args = parser.parse_args()

    banner()
    erros = verificar_pre_requisitos()
    if erros:
        print(f"{VERMELHO}Pré-requisitos incompletos:{RESET}")
        for erro in erros:
            print(f"  - {erro}")
        return 1
    print(f"  {VERDE}[OK]{RESET} Pré-requisitos, modelos e frontend verificados.")
    if args.check:
        return 0

    signal.signal(signal.SIGINT, encerrar_tudo)
    signal.signal(signal.SIGTERM, encerrar_tudo)
    python = sys.executable
    npm = shutil.which("npm.cmd") or shutil.which("npm") or "npm"

    print(f"\n{CIANO}━━ Iniciando fluxo canônico ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    iniciar_processo("Simulador sintético", [python, str(BASE / "simulador_iot.py")])
    iniciar_processo(
        "Motor de recomendações",
        [python, str(BASE / "motor_decisao.py"), "--modo=arquivo"],
        esperar=1,
    )
    iniciar_processo(
        f"Backend FastAPI → {API_URL}",
        [python, "-m", "uvicorn", "backend:app", "--host", "127.0.0.1", "--port", "8000"],
        esperar=1,
    )
    iniciar_processo(
        f"Frontend React → {DASHBOARD_URL}",
        [npm, "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173"],
    )

    api_ok = aguardar_url(f"{API_URL}/api/stats", timeout=35)
    front_ok = aguardar_url(DASHBOARD_URL, timeout=35)
    if not api_ok or not front_ok:
        print(
            f"  {VERMELHO}[ERRO]{RESET} Inicialização incompleta: "
            f"API={'OK' if api_ok else 'FALHOU'}, frontend={'OK' if front_ok else 'FALHOU'}"
        )
        encerrar_tudo(codigo=1)

    print(f"  {VERDE}[OK]{RESET} API e frontend responderam.")
    if not args.sem_navegador and os.getenv("CITYGRID_NO_BROWSER") != "1":
        webbrowser.open(DASHBOARD_URL)

    print(
        f"""
{CIANO}━━ Demonstração em execução ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}

  Dashboard      → {DASHBOARD_URL}
  API             → {API_URL}
  Documentação   → {API_URL}/docs

  5 segundos reais representam 5 minutos simulados.
  Os dados são sintéticos e as saídas são recomendações não executadas.

  {AMARELO}Pressione Ctrl+C para encerrar todos os processos.{RESET}
"""
    )

    while True:
        for nome, processo in processos:
            retorno = processo.poll()
            if retorno is not None:
                print(
                    f"  {VERMELHO}[ERRO]{RESET} {nome} encerrou inesperadamente "
                    f"(código {retorno})"
                )
                encerrar_tudo(codigo=1)
        time.sleep(2)


if __name__ == "__main__":
    raise SystemExit(main())
