"""BRONZE -> SILVER: limpar, tipar e modelar.

É aqui que o dado deixa de ser "o que a API mandou" e passa a ser "o que o
negócio entende". Três trabalhos acontecem nesta camada:

1. **Tipagem** — texto vira inteiro, decimal, data e booleano. Sem isso não dá
   para somar, ordenar nem comparar.
2. **Enriquecimento** — criamos colunas que a fonte não tem, mas que todo
   analista de F1 quer: ``posicoes_ganhas``, ``abandonou``, ``podio``,
   tempos de volta convertidos para segundos.
3. **Modelagem dimensional** — separamos DIMENSÕES (quem/onde: piloto, equipe,
   circuito, corrida) de FATOS (o que aconteceu: resultado, classificação,
   parada). É o modelo estrela clássico, o que torna a camada gold trivial.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from f1_pipeline import config
from f1_pipeline.utils.io import read_table, write_table
from f1_pipeline.utils.logging import get_logger

logger = get_logger(__name__)

# Status que significam "completou a prova" (inclui quem terminou voltas atrás).
#
# ATENÇÃO, e este é um ótimo exemplo de por que validamos o contrato da fonte:
# a Ergast original escrevia "+1 Lap" para quem tomou volta; a Jolpica passou a
# escrever "Lapped". Quem tivesse codificado apenas o texto antigo estaria hoje
# contabilizando 10 abandonos por corrida — número errado, sem nenhum erro de
# execução. Por isso mantemos as duas formas.
STATUS_COMPLETOU = ("Finished", "Lapped")
STATUS_COMPLETOU_PREFIXOS = ("Finished", "Lapped", "+")

# Duração acima disso não é uma parada normal: é carro parado sob bandeira
# vermelha ou reparo longo no box. Marcamos para não contaminar as médias.
LIMITE_PARADA_ATIPICA_S = 60.0

_PADRAO_TEMPO = re.compile(r"^(?:(\d+):)?(\d+)(?:\.(\d+))?$")


# ---------------------------------------------------------------------------
# Conversões auxiliares
# ---------------------------------------------------------------------------


def tempo_para_segundos(valor: object) -> float:
    """Converte ``"1:32.608"`` (ou ``"22.343"``) em segundos decimais.

    Tempos de volta e durações de pit stop chegam como texto no formato
    ``m:ss.mmm``. Enquanto forem texto, ``"1:02.000"`` é *menor* que
    ``"59.000"`` na ordenação alfabética — um erro clássico de análise.
    """
    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return float("nan")
    texto = str(valor).strip()
    if not texto or texto.lower() in {"nan", "none"}:
        return float("nan")
    match = _PADRAO_TEMPO.match(texto)
    if not match:
        return float("nan")
    minutos, segundos, milesimos = match.groups()
    total = int(minutos or 0) * 60 + int(segundos)
    if milesimos:
        total += int(milesimos) / (10 ** len(milesimos))
    return float(total)


def _para_int(serie: pd.Series) -> pd.Series:
    """Texto -> inteiro anulável (``Int64``), que aceita ausência de valor."""
    return pd.to_numeric(serie, errors="coerce").astype("Int64")


def _para_float(serie: pd.Series) -> pd.Series:
    return pd.to_numeric(serie, errors="coerce").astype("float64")


def chave_corrida(season: pd.Series, rodada: pd.Series) -> pd.Series:
    """Chave técnica da corrida: ``2024-05``. Ordena e junta sem ambiguidade."""
    return (
        season.astype(str)
        + "-"
        + pd.to_numeric(rodada, errors="coerce").astype("Int64").astype(str).str.zfill(2)
    )


# ---------------------------------------------------------------------------
# Dimensões
# ---------------------------------------------------------------------------


def build_dim_driver(results: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por piloto — a "ficha cadastral" que o fato não repete."""
    dim = (
        results[
            [
                "driver_id",
                "driver_code",
                "given_name",
                "family_name",
                "driver_nationality",
                "date_of_birth",
            ]
        ]
        .drop_duplicates(subset=["driver_id"])
        .rename(
            columns={
                "driver_code": "sigla",
                "given_name": "nome",
                "family_name": "sobrenome",
                "driver_nationality": "nacionalidade",
            }
        )
        .reset_index(drop=True)
    )
    dim["piloto"] = dim["nome"].fillna("") + " " + dim["sobrenome"].fillna("")
    dim["piloto"] = dim["piloto"].str.strip()
    dim["data_nascimento"] = pd.to_datetime(dim["date_of_birth"], errors="coerce")
    dim = dim.drop(columns=["date_of_birth"])
    return dim[["driver_id", "piloto", "sigla", "nome", "sobrenome", "nacionalidade", "data_nascimento"]]


def build_dim_constructor(results: pd.DataFrame) -> pd.DataFrame:
    return (
        results[["constructor_id", "constructor_name", "constructor_nationality"]]
        .drop_duplicates(subset=["constructor_id"])
        .rename(
            columns={
                "constructor_name": "equipe",
                "constructor_nationality": "nacionalidade",
            }
        )
        .sort_values("equipe")
        .reset_index(drop=True)
    )


def build_dim_circuit(races: pd.DataFrame) -> pd.DataFrame:
    dim = (
        races[["circuit_id", "circuit_name", "locality", "country", "lat", "lon"]]
        .drop_duplicates(subset=["circuit_id"])
        .rename(
            columns={
                "circuit_name": "circuito",
                "locality": "cidade",
                "country": "pais",
            }
        )
        .reset_index(drop=True)
    )
    dim["lat"] = _para_float(dim["lat"])
    dim["lon"] = _para_float(dim["lon"])
    return dim


def build_dim_race(races: pd.DataFrame) -> pd.DataFrame:
    dim = pd.DataFrame(
        {
            "race_key": chave_corrida(races["season"], races["round"]),
            "season": _para_int(races["season"]),
            "rodada": _para_int(races["round"]),
            "gp": races["race_name"],
            "data": pd.to_datetime(races["date"], errors="coerce"),
            "circuit_id": races["circuit_id"],
        }
    )
    return dim.sort_values(["season", "rodada"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Fatos
# ---------------------------------------------------------------------------


def build_fact_result(results: pd.DataFrame) -> pd.DataFrame:
    """A tabela-fato central: um piloto, uma corrida, um resultado."""
    fato = pd.DataFrame(
        {
            "race_key": chave_corrida(results["season"], results["round"]),
            "season": _para_int(results["season"]),
            "rodada": _para_int(results["round"]),
            "driver_id": results["driver_id"],
            "constructor_id": results["constructor_id"],
            "grid": _para_int(results["grid"]),
            "position": _para_int(results["position"]),
            "position_text": results["position_text"],
            "points": _para_float(results["points"]),
            "laps": _para_int(results["laps"]),
            "status": results["status"],
            "tempo_total_ms": _para_int(results["time_millis"]),
            "volta_rapida_kph": _para_float(results["fastest_lap_speed_kph"]),
            "volta_rapida_s": results["fastest_lap_time"].map(tempo_para_segundos),
        }
    )

    # --- regras de negócio ------------------------------------------------
    fato["finalizou"] = (
        fato["status"].fillna("").str.startswith(STATUS_COMPLETOU_PREFIXOS)
    )
    fato["abandonou"] = ~fato["finalizou"]
    # "Classificado" é diferente de "completou": quem roda faltando poucas
    # voltas ainda recebe posição oficial (position_text numérico).
    fato["classificado"] = results["position_text"].fillna("").str.fullmatch(r"\d+")
    fato["motivo_abandono"] = fato["status"].where(fato["abandonou"])
    fato["vitoria"] = fato["position"] == 1
    fato["podio"] = fato["position"] <= config.PODIUM_POSITIONS
    fato["pontuou"] = fato["points"] > 0

    # Grid 0 significa "largou do pit lane". Para calcular posições ganhas,
    # tratamos esse piloto como se tivesse largado em último.
    largados_por_corrida = fato.groupby("race_key")["driver_id"].transform("size")
    fato["grid_efetivo"] = fato["grid"].where(fato["grid"] > 0, largados_por_corrida)
    fato["posicoes_ganhas"] = fato["grid_efetivo"] - fato["position"]

    return fato.sort_values(["season", "rodada", "position"]).reset_index(drop=True)


def build_fact_qualifying(qualifying: pd.DataFrame) -> pd.DataFrame:
    fato = pd.DataFrame(
        {
            "race_key": chave_corrida(qualifying["season"], qualifying["round"]),
            "season": _para_int(qualifying["season"]),
            "rodada": _para_int(qualifying["round"]),
            "driver_id": qualifying["driver_id"],
            "constructor_id": qualifying["constructor_id"],
            "posicao_grid": _para_int(qualifying["position"]),
            "q1_s": qualifying["q1"].map(tempo_para_segundos),
            "q2_s": qualifying["q2"].map(tempo_para_segundos),
            "q3_s": qualifying["q3"].map(tempo_para_segundos),
        }
    )
    # O "melhor tempo" é o menor entre as três sessões disputadas.
    fato["melhor_tempo_s"] = fato[["q1_s", "q2_s", "q3_s"]].min(axis=1, skipna=True)
    fato["pole"] = fato["posicao_grid"] == 1
    fato["chegou_ao_q3"] = fato["q3_s"].notna()
    return fato.sort_values(["season", "rodada", "posicao_grid"]).reset_index(drop=True)


def build_fact_pit_stop(pit_stops: pd.DataFrame) -> pd.DataFrame:
    fato = pd.DataFrame(
        {
            "race_key": chave_corrida(pit_stops["season"], pit_stops["round"]),
            "season": _para_int(pit_stops["season"]),
            "rodada": _para_int(pit_stops["round"]),
            "driver_id": pit_stops["driver_id"],
            "parada": _para_int(pit_stops["stop"]),
            "volta": _para_int(pit_stops["lap"]),
            "duracao_s": pit_stops["duration"].map(tempo_para_segundos),
        }
    )
    fato["parada_atipica"] = fato["duracao_s"] > LIMITE_PARADA_ATIPICA_S
    return fato.sort_values(["season", "rodada", "volta"]).reset_index(drop=True)


def build_fact_driver_standing(standings: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "season": _para_int(standings["season"]),
            "driver_id": standings["driver_id"],
            "posicao_campeonato": _para_int(standings["position"]),
            "pontos": _para_float(standings["points"]),
            "vitorias": _para_int(standings["wins"]),
            "equipes": standings["constructor_names"],
        }
    ).sort_values(["season", "posicao_campeonato"]).reset_index(drop=True)


def build_fact_constructor_standing(standings: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "season": _para_int(standings["season"]),
            "constructor_id": standings["constructor_id"],
            "equipe": standings["constructor_name"],
            "posicao_campeonato": _para_int(standings["position"]),
            "pontos": _para_float(standings["points"]),
            "vitorias": _para_int(standings["wins"]),
        }
    ).sort_values(["season", "posicao_campeonato"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Orquestração da camada
# ---------------------------------------------------------------------------


def build_silver(
    bronze: dict[str, pd.DataFrame] | None = None,
    *,
    bronze_dir: Path | None = None,
    silver_dir: Path | None = None,
    salvar: bool = True,
) -> dict[str, pd.DataFrame]:
    """Constrói todas as dimensões e fatos a partir do bronze."""
    bronze_dir = Path(bronze_dir or config.BRONZE_DIR)
    silver_dir = Path(silver_dir or config.SILVER_DIR)

    if bronze is None:
        bronze = {
            nome: read_table(bronze_dir / nome)
            for nome in (
                "races",
                "results",
                "qualifying",
                "pit_stops",
                "driver_standings",
                "constructor_standings",
            )
        }

    tabelas = {
        "dim_driver": build_dim_driver(bronze["results"]),
        "dim_constructor": build_dim_constructor(bronze["results"]),
        "dim_circuit": build_dim_circuit(bronze["races"]),
        "dim_race": build_dim_race(bronze["races"]),
        "fact_result": build_fact_result(bronze["results"]),
        "fact_qualifying": build_fact_qualifying(bronze["qualifying"]),
        "fact_pit_stop": build_fact_pit_stop(bronze["pit_stops"]),
        "fact_driver_standing": build_fact_driver_standing(bronze["driver_standings"]),
        "fact_constructor_standing": build_fact_constructor_standing(
            bronze["constructor_standings"]
        ),
    }

    for nome, df in tabelas.items():
        if salvar:
            destino = write_table(df, silver_dir / nome)
            logger.info(
                "SILVER %-26s | %6d linhas | %2d colunas -> %s",
                nome,
                len(df),
                df.shape[1],
                destino.name,
            )
        else:
            logger.info("SILVER %-26s | %6d linhas (não gravado)", nome, len(df))
    return tabelas


def load_silver(silver_dir: Path | None = None) -> dict[str, pd.DataFrame]:
    """Lê a camada silver do disco."""
    silver_dir = Path(silver_dir or config.SILVER_DIR)
    nomes = (
        "dim_driver",
        "dim_constructor",
        "dim_circuit",
        "dim_race",
        "fact_result",
        "fact_qualifying",
        "fact_pit_stop",
        "fact_driver_standing",
        "fact_constructor_standing",
    )
    return {nome: read_table(silver_dir / nome) for nome in nomes}
