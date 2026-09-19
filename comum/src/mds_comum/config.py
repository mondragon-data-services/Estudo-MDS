"""Localiza a raiz do repositório e carrega os arquivos .env.

Ordem de prioridade (o primeiro que definir a variável vence):

    1. variáveis de ambiente já definidas no terminal
    2. aulas/<aula>/.env   -> configurações só daquela aula
    3. <raiz>/.env         -> conexão com o SQL Server, comum a todas as aulas
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # sem python-dotenv, vale só o que estiver no ambiente
    load_dotenv = None


def _eh_raiz(pasta: Path) -> bool:
    return (pasta / "aulas").is_dir() and (pasta / "comum").is_dir()


def raiz_do_repositorio() -> Path:
    """Sobe as pastas (a partir deste arquivo e do diretório atual) até achar a raiz."""
    for inicio in (Path(__file__).resolve(), Path.cwd().resolve()):
        for pasta in (inicio, *inicio.parents):
            if _eh_raiz(pasta):
                return pasta
    raise FileNotFoundError(
        "Não encontrei a raiz do repositório (pasta com 'aulas/' e 'comum/')."
    )


def carregar_env(pasta_aula: str | Path | None = None) -> None:
    """Carrega o .env da aula (se informado) e depois o .env da raiz.

    O ``load_dotenv`` não sobrescreve variáveis já definidas, então carregar a
    aula primeiro é o que dá prioridade a ela.
    """
    if load_dotenv is None:
        return
    if pasta_aula is not None:
        load_dotenv(Path(pasta_aula) / ".env")
    load_dotenv(raiz_do_repositorio() / ".env")


def _sim(valor: str) -> bool:
    return valor.strip().lower() in {"1", "yes", "sim", "true", "s", "y"}


@dataclass(frozen=True)
class ConfigSqlServer:
    servidor: str
    autenticacao_windows: bool
    usuario: str
    senha: str
    driver: str


def sqlserver() -> ConfigSqlServer:
    """Configuração de conexão lida do ambiente (com os padrões do .env.example)."""
    carregar_env()
    return ConfigSqlServer(
        servidor=os.getenv("SQL_SERVER", "localhost"),
        autenticacao_windows=_sim(os.getenv("SQL_TRUSTED_CONNECTION", "yes")),
        usuario=os.getenv("SQL_USER", ""),
        senha=os.getenv("SQL_PASSWORD", ""),
        driver=os.getenv("ODBC_DRIVER", "ODBC Driver 18 for SQL Server"),
    )
