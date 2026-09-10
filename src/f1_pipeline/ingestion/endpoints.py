"""Catálogo dos endpoints que este projeto ingere.

Declarar os endpoints como *dados* (e não como código espalhado) é o que
permite escrever um único job de ingestão genérico. Cada `Endpoint` diz:

* como montar a URL a partir da temporada;
* onde, dentro do JSON, estão os registros (a Ergast API aninha tudo em
  ``MRData -> <alguma>Table -> <alguma lista>``);
* uma descrição em português para os relatórios e notebooks.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Endpoint:
    """Descrição declarativa de um recurso da API."""

    name: str
    """Nome curto usado como pasta em ``data/raw/`` e como nome da tabela bronze."""

    path_template: str
    """Trecho da URL depois da base. Ex.: ``"{season}/results"``."""

    table_key: str
    """Chave da *table* dentro de ``MRData``. Ex.: ``"RaceTable"``."""

    records_key: str
    """Chave da lista de registros dentro da *table*. Ex.: ``"Races"``."""

    description: str
    """Explicação didática do que este endpoint traz."""

    por_rodada: bool = False
    """Se ``True``, a API só aceita a consulta corrida a corrida.

    É o caso das paradas nos boxes: ``/2024/pitstops`` devolve HTTP 400, só
    ``/2024/1/pitstops`` funciona. Endpoints assim exigem uma ingestão em
    *fan-out* (uma requisição por rodada) — um padrão muito comum em APIs
    reais e uma das primeiras surpresas de quem começa a ingerir dados.
    """

    def url_path(self, season: int, rodada: int | None = None) -> str:
        return self.path_template.format(season=season, round=rodada)


ENDPOINTS: tuple[Endpoint, ...] = (
    Endpoint(
        name="races",
        path_template="{season}/races",
        table_key="RaceTable",
        records_key="Races",
        description="Calendário da temporada: cada GP, sua data e seu circuito.",
    ),
    Endpoint(
        name="results",
        path_template="{season}/results",
        table_key="RaceTable",
        records_key="Races",
        description="Resultado final de cada piloto em cada GP (a tabela-fato principal).",
    ),
    Endpoint(
        name="qualifying",
        path_template="{season}/qualifying",
        table_key="RaceTable",
        records_key="Races",
        description="Tempos de Q1, Q2 e Q3 — define o grid de largada.",
    ),
    Endpoint(
        name="pit_stops",
        path_template="{season}/{round}/pitstops",
        table_key="RaceTable",
        records_key="Races",
        description="Cada parada nos boxes: volta, horário e duração.",
        por_rodada=True,
    ),
    Endpoint(
        name="driver_standings",
        path_template="{season}/driverstandings",
        table_key="StandingsTable",
        records_key="StandingsLists",
        description="Classificação final do campeonato de pilotos.",
    ),
    Endpoint(
        name="constructor_standings",
        path_template="{season}/constructorstandings",
        table_key="StandingsTable",
        records_key="StandingsLists",
        description="Classificação final do campeonato de construtores.",
    ),
)

ENDPOINTS_BY_NAME = {endpoint.name: endpoint for endpoint in ENDPOINTS}


def get_endpoint(name: str) -> Endpoint:
    try:
        return ENDPOINTS_BY_NAME[name]
    except KeyError as exc:  # pragma: no cover - erro de digitação do usuário
        disponiveis = ", ".join(sorted(ENDPOINTS_BY_NAME))
        raise KeyError(
            f"Endpoint '{name}' não existe. Disponíveis: {disponiveis}"
        ) from exc
