"""Carregamento centralizado da configuração local do CityGrid."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv


ARQUIVO_ENV_PADRAO = Path(__file__).resolve().with_name(".env")


def carregar_env_local(caminho: str | Path | None = None) -> bool:
    """Carrega ``.env`` sem sobrescrever variáveis já definidas pelo processo."""
    arquivo = Path(caminho) if caminho is not None else ARQUIVO_ENV_PADRAO
    return bool(load_dotenv(dotenv_path=arquivo, override=False))
