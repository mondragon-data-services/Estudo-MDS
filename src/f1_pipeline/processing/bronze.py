"""RAW -> BRONZE: transformar JSON aninhado em tabelas.

A camada bronze tem **uma única responsabilidade**: achatar o JSON em linhas e
colunas. Nada mais.

* Nenhuma conversão de tipo — tudo continua texto, como veio da API.
* Nenhum filtro — se veio na fonte, está no bronze.
* Nenhuma regra de negócio.

Por que essa disciplina? Porque assim a bronze é **auditável**: qualquer valor
dela pode ser comparado com o JSON original. É exatamente sobre ela que rodamos
as validações de "a fonte continua cumprindo o contrato?".
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from f1_pipeline import config
from f1_pipeline.ingestion.jobs import iter_raw_records
from f1_pipeline.utils.io import write_table
from f1_pipeline.utils.logging import get_logger

logger = get_logger(__name__)


def _texto(valor: Any) -> str | None:
    """Normaliza para texto mantendo ``None`` — bronze não inventa valor."""
    if valor is None:
        return None
    return str(valor)


def _campos_da_corrida(race: dict[str, Any]) -> dict[str, Any]:
    """Colunas de contexto repetidas em toda tabela derivada de uma corrida."""
    return {
        "season": _texto(race.get("season")),
        "round": _texto(race.get("round")),
        "race_name": _texto(race.get("raceName")),
        "date": _texto(race.get("date")),
    }


# ---------------------------------------------------------------------------
# Um construtor por endpoint
# ---------------------------------------------------------------------------


def build_races(seasons: Iterable[int] | None = None, raw_dir: Path | None = None):
    linhas = []
    for _, race in iter_raw_records("races", seasons, raw_dir):
        circuito = race.get("Circuit", {}) or {}
        local = circuito.get("Location", {}) or {}
        linhas.append(
            {
                **_campos_da_corrida(race),
                "time": _texto(race.get("time")),
                "circuit_id": _texto(circuito.get("circuitId")),
                "circuit_name": _texto(circuito.get("circuitName")),
                "locality": _texto(local.get("locality")),
                "country": _texto(local.get("country")),
                "lat": _texto(local.get("lat")),
                "lon": _texto(local.get("long")),
                "url": _texto(race.get("url")),
            }
        )
    return pd.DataFrame(linhas)


def build_results(seasons: Iterable[int] | None = None, raw_dir: Path | None = None):
    """Achata ``Races[].Results[]`` — o JSON tem 3 níveis de aninhamento."""
    linhas = []
    for _, race in iter_raw_records("results", seasons, raw_dir):
        contexto = _campos_da_corrida(race)
        for resultado in race.get("Results", []) or []:
            piloto = resultado.get("Driver", {}) or {}
            equipe = resultado.get("Constructor", {}) or {}
            tempo = resultado.get("Time", {}) or {}
            volta_rapida = resultado.get("FastestLap", {}) or {}
            tempo_volta_rapida = volta_rapida.get("Time", {}) or {}
            velocidade = volta_rapida.get("AverageSpeed", {}) or {}
            linhas.append(
                {
                    **contexto,
                    "driver_id": _texto(piloto.get("driverId")),
                    "driver_code": _texto(piloto.get("code")),
                    "driver_number": _texto(resultado.get("number")),
                    "given_name": _texto(piloto.get("givenName")),
                    "family_name": _texto(piloto.get("familyName")),
                    "driver_nationality": _texto(piloto.get("nationality")),
                    "date_of_birth": _texto(piloto.get("dateOfBirth")),
                    "constructor_id": _texto(equipe.get("constructorId")),
                    "constructor_name": _texto(equipe.get("name")),
                    "constructor_nationality": _texto(equipe.get("nationality")),
                    "grid": _texto(resultado.get("grid")),
                    "position": _texto(resultado.get("position")),
                    "position_text": _texto(resultado.get("positionText")),
                    "points": _texto(resultado.get("points")),
                    "laps": _texto(resultado.get("laps")),
                    "status": _texto(resultado.get("status")),
                    "time_millis": _texto(tempo.get("millis")),
                    "time_text": _texto(tempo.get("time")),
                    "fastest_lap_rank": _texto(volta_rapida.get("rank")),
                    "fastest_lap_number": _texto(volta_rapida.get("lap")),
                    "fastest_lap_time": _texto(tempo_volta_rapida.get("time")),
                    "fastest_lap_speed_kph": _texto(velocidade.get("speed")),
                }
            )
    return pd.DataFrame(linhas)


def build_qualifying(seasons: Iterable[int] | None = None, raw_dir: Path | None = None):
    linhas = []
    for _, race in iter_raw_records("qualifying", seasons, raw_dir):
        contexto = _campos_da_corrida(race)
        for quali in race.get("QualifyingResults", []) or []:
            piloto = quali.get("Driver", {}) or {}
            equipe = quali.get("Constructor", {}) or {}
            linhas.append(
                {
                    **contexto,
                    "driver_id": _texto(piloto.get("driverId")),
                    "driver_code": _texto(piloto.get("code")),
                    "constructor_id": _texto(equipe.get("constructorId")),
                    "position": _texto(quali.get("position")),
                    "q1": _texto(quali.get("Q1")),
                    "q2": _texto(quali.get("Q2")),
                    "q3": _texto(quali.get("Q3")),
                }
            )
    return pd.DataFrame(linhas)


def build_pit_stops(seasons: Iterable[int] | None = None, raw_dir: Path | None = None):
    linhas = []
    for _, race in iter_raw_records("pit_stops", seasons, raw_dir):
        contexto = _campos_da_corrida(race)
        for parada in race.get("PitStops", []) or []:
            linhas.append(
                {
                    **contexto,
                    "driver_id": _texto(parada.get("driverId")),
                    "stop": _texto(parada.get("stop")),
                    "lap": _texto(parada.get("lap")),
                    "time": _texto(parada.get("time")),
                    "duration": _texto(parada.get("duration")),
                }
            )
    return pd.DataFrame(linhas)


def build_driver_standings(
    seasons: Iterable[int] | None = None, raw_dir: Path | None = None
):
    """A classificação vem em ``StandingsLists[].DriverStandings[]``."""
    linhas = []
    for season, lista in iter_raw_records("driver_standings", seasons, raw_dir):
        for posicao in lista.get("DriverStandings", []) or []:
            piloto = posicao.get("Driver", {}) or {}
            equipes = posicao.get("Constructors", []) or []
            linhas.append(
                {
                    "season": _texto(lista.get("season", season)),
                    "round": _texto(lista.get("round")),
                    "position": _texto(posicao.get("position")),
                    "position_text": _texto(posicao.get("positionText")),
                    "points": _texto(posicao.get("points")),
                    "wins": _texto(posicao.get("wins")),
                    "driver_id": _texto(piloto.get("driverId")),
                    "driver_code": _texto(piloto.get("code")),
                    "given_name": _texto(piloto.get("givenName")),
                    "family_name": _texto(piloto.get("familyName")),
                    "driver_nationality": _texto(piloto.get("nationality")),
                    "constructor_ids": ",".join(
                        str(c.get("constructorId")) for c in equipes
                    ),
                    "constructor_names": ",".join(str(c.get("name")) for c in equipes),
                }
            )
    return pd.DataFrame(linhas)


def build_constructor_standings(
    seasons: Iterable[int] | None = None, raw_dir: Path | None = None
):
    linhas = []
    for season, lista in iter_raw_records("constructor_standings", seasons, raw_dir):
        for posicao in lista.get("ConstructorStandings", []) or []:
            equipe = posicao.get("Constructor", {}) or {}
            linhas.append(
                {
                    "season": _texto(lista.get("season", season)),
                    "round": _texto(lista.get("round")),
                    "position": _texto(posicao.get("position")),
                    "position_text": _texto(posicao.get("positionText")),
                    "points": _texto(posicao.get("points")),
                    "wins": _texto(posicao.get("wins")),
                    "constructor_id": _texto(equipe.get("constructorId")),
                    "constructor_name": _texto(equipe.get("name")),
                    "constructor_nationality": _texto(equipe.get("nationality")),
                }
            )
    return pd.DataFrame(linhas)


BUILDERS = {
    "races": build_races,
    "results": build_results,
    "qualifying": build_qualifying,
    "pit_stops": build_pit_stops,
    "driver_standings": build_driver_standings,
    "constructor_standings": build_constructor_standings,
}


# ---------------------------------------------------------------------------
# Orquestração da camada
# ---------------------------------------------------------------------------


def build_bronze(
    seasons: Iterable[int] | None = None,
    *,
    raw_dir: Path | None = None,
    bronze_dir: Path | None = None,
    salvar: bool = True,
) -> dict[str, pd.DataFrame]:
    """Constrói (e opcionalmente grava) todas as tabelas bronze."""
    bronze_dir = Path(bronze_dir or config.BRONZE_DIR)
    tabelas: dict[str, pd.DataFrame] = {}
    for nome, builder in BUILDERS.items():
        df = builder(seasons, raw_dir)
        tabelas[nome] = df
        if salvar:
            destino = write_table(df, bronze_dir / nome)
            logger.info(
                "BRONZE %-22s | %6d linhas | %2d colunas -> %s",
                nome,
                len(df),
                df.shape[1],
                destino.name,
            )
        else:
            logger.info("BRONZE %-22s | %6d linhas (não gravado)", nome, len(df))
    return tabelas
