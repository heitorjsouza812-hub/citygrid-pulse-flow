from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _curva_critica(seed: int) -> list[float]:
    env = {**os.environ, "CITYGRID_SEED": str(seed)}
    codigo = (
        "import json, simulador_iot as s; "
        "print(json.dumps([s.CURVA_CRITICO[h] for h in range(24)]))"
    )
    saida = subprocess.check_output(
        [sys.executable, "-c", codigo], cwd=ROOT, env=env, text=True
    )
    return json.loads(saida.strip().splitlines()[-1])


def test_seed_do_simulador_e_configuravel_e_reproduzivel() -> None:
    primeira = _curva_critica(123)
    segunda = _curva_critica(123)
    diferente = _curva_critica(321)

    assert primeira == segunda
    assert primeira != diferente


def test_relogio_simulado_avanca_cinco_minutos_por_ciclo() -> None:
    import simulador_iot as simulador

    inicio = datetime(2026, 1, 1, 12, 0)
    simulador.estado["tempo_simulado"] = inicio

    simulador.avancar_tempo_simulado()

    assert simulador.estado["tempo_simulado"] == inicio + timedelta(minutes=5)
    assert simulador.INTERVALO_SEGUNDOS == 5
    assert simulador.INTERVALO_SIMULADO_MINUTOS == 5
