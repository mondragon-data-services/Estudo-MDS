"""Configuração central do pipeline.

Todo caminho de pasta e todo parâmetro "mágico" do projeto vive aqui.
Isso evita que os notebooks fiquem cheios de strings soltas e permite
mudar o comportamento do pipeline por variável de ambiente.

Camadas de dados (arquitetura *medallion*):

    data/raw     -> JSON exatamente como veio da API (nada é alterado)
    data/bronze  -> os mesmos dados, apenas tabularizados (tudo texto)
    data/silver  -> dados limpos, tipados e modelados (dimensões e fatos)
    data/gold    -> agregações prontas para consumo analítico
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Caminhos
# ---------------------------------------------------------------------------

# config.py fica em <raiz>/src/f1_pipeline/config.py -> parents[2] é a raiz.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = Path(os.getenv("F1_DATA_DIR", PROJECT_ROOT / "data"))
RAW_DIR = DATA_DIR / "raw"
BRONZE_DIR = DATA_DIR / "bronze"
SILVER_DIR = DATA_DIR / "silver"
GOLD_DIR = DATA_DIR / "gold"

REPORTS_DIR = PROJECT_ROOT / "reports"          # relatórios de qualidade (JSON)
DOCS_DIR = PROJECT_ROOT / "docs"
DATA_DOCS_DIR = DOCS_DIR / "data_docs"          # Data Docs do Great Expectations
GX_ROOT = PROJECT_ROOT / "gx"                   # projeto do Great Expectations

ALL_DATA_DIRS = (RAW_DIR, BRONZE_DIR, SILVER_DIR, GOLD_DIR)

# ---------------------------------------------------------------------------
# Fonte de dados
# ---------------------------------------------------------------------------

# A Ergast API (ergast.com) foi descontinuada no fim de 2024. A Jolpica-F1 é o
# sucessor mantido pela comunidade e expõe exatamente o mesmo contrato.
API_BASE_URL = os.getenv("F1_API_BASE_URL", "https://api.jolpi.ca/ergast/f1")

# A API devolve no máximo 100 registros por página.
API_PAGE_SIZE = int(os.getenv("F1_API_PAGE_SIZE", "100"))

# Limite público: ~4 requisições/segundo. Deixamos folga por educação.
API_MIN_INTERVAL_SECONDS = float(os.getenv("F1_API_MIN_INTERVAL", "0.35"))
API_TIMEOUT_SECONDS = float(os.getenv("F1_API_TIMEOUT", "30"))
API_MAX_RETRIES = int(os.getenv("F1_API_MAX_RETRIES", "5"))
API_USER_AGENT = os.getenv(
    "F1_API_USER_AGENT",
    "f1-data-engineering-course/1.0 (projeto didatico)",
)

# ---------------------------------------------------------------------------
# Escopo da carga
# ---------------------------------------------------------------------------


def _parse_seasons(value: str | None) -> tuple[int, ...]:
    """Lê temporadas de uma variável de ambiente: "2021,2022" ou "2021-2024"."""
    if not value:
        return (2021, 2022, 2023, 2024)
    value = value.strip()
    if "-" in value and "," not in value:
        start, end = (int(p) for p in value.split("-", 1))
        return tuple(range(start, end + 1))
    return tuple(int(p) for p in value.split(",") if p.strip())


SEASONS: tuple[int, ...] = _parse_seasons(os.getenv("F1_SEASONS"))

# ---------------------------------------------------------------------------
# Regras de negócio usadas nas validações e agregações
# ---------------------------------------------------------------------------

# Pontuação máxima possível em um GP moderno: 25 (vitória) + 1 (volta mais
# rápida) = 26. Em corridas sprint a soma vai para outra tabela de resultados.
MAX_POINTS_PER_RACE = 26.0
PODIUM_POSITIONS = 3
MAX_GRID_POSITION = 30  # grid 0 = largada do pit lane

# `positionText` traz códigos quando o piloto não foi classificado.
NON_CLASSIFIED_CODES = ("R", "D", "E", "W", "F", "N")

__all__ = [
    "PROJECT_ROOT",
    "DATA_DIR",
    "RAW_DIR",
    "BRONZE_DIR",
    "SILVER_DIR",
    "GOLD_DIR",
    "REPORTS_DIR",
    "DOCS_DIR",
    "DATA_DOCS_DIR",
    "GX_ROOT",
    "ALL_DATA_DIRS",
    "API_BASE_URL",
    "API_PAGE_SIZE",
    "API_MIN_INTERVAL_SECONDS",
    "API_TIMEOUT_SECONDS",
    "API_MAX_RETRIES",
    "API_USER_AGENT",
    "SEASONS",
    "MAX_POINTS_PER_RACE",
    "PODIUM_POSITIONS",
    "MAX_GRID_POSITION",
    "NON_CLASSIFIED_CODES",
]
