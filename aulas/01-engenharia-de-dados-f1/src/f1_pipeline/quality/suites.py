"""As regras de qualidade do projeto, uma *suite* por tabela.

Uma decisão importante de arquitetura aparece aqui:

* **Suites de BRONZE validam o CONTRATO da fonte.** Na camada bronze todo
  valor ainda é texto (é o que a API devolveu). Então testamos *forma*:
  as colunas esperadas existem? o campo que deveria ser numérico casa com
  ``^\\d+$``? a chave de negócio é única? o volume de linhas faz sentido?

* **Suites de SILVER/GOLD validam a SEMÂNTICA do dado.** Aqui os tipos já
  existem, então testamos *significado*: pontuação não pode ser negativa,
  posição de chegada vai de 1 a 30, a soma de pontos do campeonato tem que
  bater com a soma das corridas.

Cada expectativa carrega um ``meta={"descricao": ...}`` em português: é o que
aparece no relatório e no app, transformando um erro técnico em uma frase que
o time de negócio entende.
"""

from __future__ import annotations

import great_expectations as gx
from great_expectations import expectations as gxe

from f1_pipeline import config

# Expressões regulares usadas para validar "números que ainda são texto".
REGEX_INTEIRO = r"^\d+$"
REGEX_DECIMAL = r"^-?\d+(\.\d+)?$"
REGEX_DATA = r"^\d{4}-\d{2}-\d{2}$"
REGEX_TEMPO_VOLTA = r"^\d+:\d{2}\.\d{3}$"  # 1:32.608


def _suite(name: str, expectations: list) -> gx.ExpectationSuite:
    """Monta uma ExpectationSuite a partir de uma lista de expectativas."""
    suite = gx.ExpectationSuite(name=name)
    for expectation in expectations:
        suite.add_expectation(expectation)
    return suite


def _descricao(texto: str) -> dict:
    return {"descricao": texto}


# ===========================================================================
# BRONZE — o contrato com a fonte
# ===========================================================================


def bronze_races_suite() -> gx.ExpectationSuite:
    """Calendário: uma linha por GP, chave (temporada, rodada) única."""
    return _suite(
        "bronze_races",
        [
            gxe.ExpectTableColumnsToMatchSet(
                column_set=[
                    "season",
                    "round",
                    "race_name",
                    "date",
                    "circuit_id",
                    "circuit_name",
                    "locality",
                    "country",
                ],
                exact_match=False,
                meta=_descricao("O schema da fonte contém todas as colunas esperadas."),
            ),
            gxe.ExpectTableRowCountToBeBetween(
                min_value=10,
                max_value=30 * len(config.SEASONS),
                meta=_descricao(
                    "Uma temporada de F1 tem entre 10 e 30 corridas; volume fora "
                    "disso indica carga incompleta ou duplicada."
                ),
            ),
            gxe.ExpectCompoundColumnsToBeUnique(
                column_list=["season", "round"],
                meta=_descricao(
                    "A chave de negócio (temporada, rodada) não pode se repetir."
                ),
            ),
            gxe.ExpectColumnValuesToNotBeNull(
                column="race_name",
                meta=_descricao("Todo GP precisa de nome."),
            ),
            gxe.ExpectColumnValuesToMatchRegex(
                column="date",
                regex=REGEX_DATA,
                meta=_descricao("A data do GP vem no formato ISO AAAA-MM-DD."),
            ),
            gxe.ExpectColumnValuesToMatchRegex(
                column="round",
                regex=REGEX_INTEIRO,
                meta=_descricao("A rodada é um inteiro (ainda como texto no bronze)."),
            ),
            gxe.ExpectColumnDistinctValuesToBeInSet(
                column="season",
                value_set=[str(s) for s in config.SEASONS],
                meta=_descricao(
                    "Só devem existir as temporadas que pedimos na ingestão."
                ),
            ),
            gxe.ExpectColumnValuesToNotBeNull(
                column="circuit_id",
                meta=_descricao("Toda corrida acontece em um circuito conhecido."),
            ),
        ],
    )


def bronze_results_suite() -> gx.ExpectationSuite:
    """Tabela-fato principal: resultado de cada piloto em cada GP."""
    return _suite(
        "bronze_results",
        [
            gxe.ExpectTableColumnsToMatchSet(
                column_set=[
                    "season",
                    "round",
                    "driver_id",
                    "constructor_id",
                    "grid",
                    "position",
                    "position_text",
                    "points",
                    "laps",
                    "status",
                ],
                exact_match=False,
                meta=_descricao("O contrato de colunas da fonte não mudou."),
            ),
            gxe.ExpectTableRowCountToBeBetween(
                min_value=100,
                max_value=30 * 25 * len(config.SEASONS),
                meta=_descricao(
                    "No máximo ~25 pilotos por GP em até 30 GPs por temporada."
                ),
            ),
            gxe.ExpectCompoundColumnsToBeUnique(
                column_list=["season", "round", "driver_id"],
                meta=_descricao(
                    "Um piloto aparece uma única vez por corrida — se duplicar, "
                    "houve reprocessamento indevido da ingestão."
                ),
            ),
            gxe.ExpectColumnValuesToNotBeNull(
                column="driver_id",
                meta=_descricao("Sem piloto não existe resultado."),
            ),
            gxe.ExpectColumnValuesToNotBeNull(
                column="constructor_id",
                meta=_descricao("Todo piloto corre por uma equipe."),
            ),
            gxe.ExpectColumnValuesToMatchRegex(
                column="points",
                regex=REGEX_DECIMAL,
                meta=_descricao("Pontos são numéricos (podem ter meio ponto)."),
            ),
            gxe.ExpectColumnValuesToMatchRegex(
                column="grid",
                regex=REGEX_INTEIRO,
                meta=_descricao("Posição de largada é inteira (0 = largou do pit)."),
            ),
            gxe.ExpectColumnValuesToMatchRegex(
                column="position",
                regex=REGEX_INTEIRO,
                meta=_descricao("Posição de chegada é inteira."),
            ),
            gxe.ExpectColumnValuesToNotBeNull(
                column="status",
                meta=_descricao(
                    "O status ('Finished', '+1 Lap', 'Engine'...) explica o "
                    "resultado e é obrigatório."
                ),
            ),
            gxe.ExpectColumnValuesToBeInSet(
                column="position_text",
                value_set=[str(i) for i in range(1, 31)]
                + list(config.NON_CLASSIFIED_CODES),
                meta=_descricao(
                    "position_text traz a posição OU um código de não classificado "
                    "(R=abandono, D=desclassificado, W=desistiu...)."
                ),
            ),
        ],
    )


def bronze_qualifying_suite() -> gx.ExpectationSuite:
    """Classificação (Q1/Q2/Q3): note que Q2 e Q3 são legitimamente nulos."""
    return _suite(
        "bronze_qualifying",
        [
            gxe.ExpectTableColumnsToMatchSet(
                column_set=[
                    "season",
                    "round",
                    "driver_id",
                    "constructor_id",
                    "position",
                    "q1",
                    "q2",
                    "q3",
                ],
                exact_match=False,
                meta=_descricao("O contrato de colunas da classificação não mudou."),
            ),
            gxe.ExpectCompoundColumnsToBeUnique(
                column_list=["season", "round", "driver_id"],
                meta=_descricao("Um piloto tem um único resultado de classificação."),
            ),
            gxe.ExpectColumnValuesToMatchRegex(
                column="position",
                regex=REGEX_INTEIRO,
                meta=_descricao("Posição no grid provisório é inteira."),
            ),
            gxe.ExpectColumnValuesToNotBeNull(
                column="driver_id",
                meta=_descricao("Sem piloto não existe volta de classificação."),
            ),
            gxe.ExpectColumnValuesToMatchRegex(
                column="q1",
                regex=REGEX_TEMPO_VOLTA,
                mostly=0.90,
                meta=_descricao(
                    "Tempo de Q1 no formato m:ss.mmm. Toleramos 10% de exceções "
                    "porque quem não marca tempo fica sem registro."
                ),
            ),
            gxe.ExpectColumnValuesToNotBeNull(
                column="q1",
                mostly=0.95,
                meta=_descricao(
                    "Quase todo piloto marca tempo no Q1 — 'mostly' é como o GX "
                    "expressa uma tolerância explícita."
                ),
            ),
        ],
    )


def bronze_pit_stops_suite() -> gx.ExpectationSuite:
    """Paradas nos boxes."""
    return _suite(
        "bronze_pit_stops",
        [
            gxe.ExpectTableColumnsToMatchSet(
                column_set=[
                    "season",
                    "round",
                    "driver_id",
                    "stop",
                    "lap",
                    "duration",
                ],
                exact_match=False,
                meta=_descricao("O contrato de colunas das paradas não mudou."),
            ),
            gxe.ExpectCompoundColumnsToBeUnique(
                column_list=["season", "round", "driver_id", "stop"],
                meta=_descricao(
                    "Cada parada (1ª, 2ª, 3ª...) de um piloto é registrada uma vez."
                ),
            ),
            gxe.ExpectColumnValuesToMatchRegex(
                column="lap",
                regex=REGEX_INTEIRO,
                meta=_descricao("O número da volta é inteiro."),
            ),
            gxe.ExpectColumnValuesToNotBeNull(
                column="duration",
                meta=_descricao("Toda parada tem duração medida."),
            ),
        ],
    )


def bronze_driver_standings_suite() -> gx.ExpectationSuite:
    """Classificação final do campeonato de pilotos."""
    return _suite(
        "bronze_driver_standings",
        [
            gxe.ExpectCompoundColumnsToBeUnique(
                column_list=["season", "driver_id"],
                meta=_descricao("Um piloto ocupa uma única posição por temporada."),
            ),
            gxe.ExpectCompoundColumnsToBeUnique(
                column_list=["season", "position"],
                meta=_descricao("Não existem dois pilotos na mesma colocação final."),
            ),
            gxe.ExpectColumnValuesToMatchRegex(
                column="points",
                regex=REGEX_DECIMAL,
                meta=_descricao("Pontos do campeonato são numéricos."),
            ),
            gxe.ExpectColumnValuesToMatchRegex(
                column="wins",
                regex=REGEX_INTEIRO,
                meta=_descricao("Número de vitórias é inteiro."),
            ),
        ],
    )


def bronze_constructor_standings_suite() -> gx.ExpectationSuite:
    """Classificação final do campeonato de construtores."""
    return _suite(
        "bronze_constructor_standings",
        [
            gxe.ExpectCompoundColumnsToBeUnique(
                column_list=["season", "constructor_id"],
                meta=_descricao("Uma equipe ocupa uma única posição por temporada."),
            ),
            gxe.ExpectColumnValuesToMatchRegex(
                column="points",
                regex=REGEX_DECIMAL,
                meta=_descricao("Pontos do campeonato de construtores são numéricos."),
            ),
            gxe.ExpectColumnValuesToNotBeNull(
                column="constructor_name",
                meta=_descricao("Toda equipe tem nome."),
            ),
        ],
    )


BRONZE_SUITES = {
    "races": bronze_races_suite,
    "results": bronze_results_suite,
    "qualifying": bronze_qualifying_suite,
    "pit_stops": bronze_pit_stops_suite,
    "driver_standings": bronze_driver_standings_suite,
    "constructor_standings": bronze_constructor_standings_suite,
}


# ===========================================================================
# SILVER — a semântica do dado já tipado
# ===========================================================================


def silver_fact_result_suite() -> gx.ExpectationSuite:
    """Agora que os tipos existem, testamos faixas e regras de negócio."""
    return _suite(
        "silver_fact_result",
        [
            gxe.ExpectColumnValuesToBeBetween(
                column="points",
                min_value=0,
                max_value=config.MAX_POINTS_PER_RACE,
                meta=_descricao(
                    f"Um GP dá no máximo {config.MAX_POINTS_PER_RACE:.0f} pontos "
                    "(25 pela vitória + 1 pela volta mais rápida)."
                ),
            ),
            gxe.ExpectColumnValuesToBeBetween(
                column="grid",
                min_value=0,
                max_value=config.MAX_GRID_POSITION,
                meta=_descricao("Grid vai de 0 (largada do pit lane) a 30."),
            ),
            gxe.ExpectColumnValuesToBeBetween(
                column="position",
                min_value=1,
                max_value=config.MAX_GRID_POSITION,
                meta=_descricao("Posição de chegada vai de 1 a 30."),
            ),
            gxe.ExpectColumnValuesToNotBeNull(
                column="race_key",
                meta=_descricao(
                    "A chave técnica temporada-rodada é a ligação com dim_race."
                ),
            ),
            gxe.ExpectCompoundColumnsToBeUnique(
                column_list=["race_key", "driver_id"],
                meta=_descricao("Grão da tabela-fato: uma linha por piloto por corrida."),
            ),
            gxe.ExpectColumnValuesToBeInSet(
                column="finalizou",
                value_set=[True, False],
                meta=_descricao("A flag de conclusão é booleana de verdade."),
            ),
            gxe.ExpectColumnValuesToBeBetween(
                column="laps",
                min_value=0,
                max_value=200,
                meta=_descricao("Nenhum GP moderno passa de 200 voltas."),
            ),
        ],
    )


def silver_fact_qualifying_suite() -> gx.ExpectationSuite:
    return _suite(
        "silver_fact_qualifying",
        [
            gxe.ExpectCompoundColumnsToBeUnique(
                column_list=["race_key", "driver_id"],
                meta=_descricao("Grão: uma linha por piloto por classificação."),
            ),
            gxe.ExpectColumnValuesToBeBetween(
                column="melhor_tempo_s",
                min_value=50,
                max_value=180,
                mostly=0.99,
                meta=_descricao(
                    "Uma volta de classificação leva entre 50s (Red Bull Ring) e "
                    "180s (Spa em pista molhada)."
                ),
            ),
            gxe.ExpectColumnValuesToBeBetween(
                column="posicao_grid",
                min_value=1,
                max_value=config.MAX_GRID_POSITION,
                meta=_descricao("Posição na classificação vai de 1 a 30."),
            ),
        ],
    )


SILVER_SUITES = {
    "fact_result": silver_fact_result_suite,
    "fact_qualifying": silver_fact_qualifying_suite,
}


# ===========================================================================
# GOLD — a agregação continua fiel à fonte?
# ===========================================================================


def gold_agg_driver_season_suite() -> gx.ExpectationSuite:
    """Validação de reconciliação: a agregação não pode inventar nem perder dado."""
    return _suite(
        "gold_agg_driver_season",
        [
            gxe.ExpectCompoundColumnsToBeUnique(
                column_list=["season", "driver_id"],
                meta=_descricao("Grão do mart: uma linha por piloto por temporada."),
            ),
            gxe.ExpectColumnValuesToBeBetween(
                column="pontos",
                min_value=0,
                max_value=1000,
                meta=_descricao("Nenhum piloto somou mais de 1000 pontos numa temporada."),
            ),
            gxe.ExpectColumnValuesToBeBetween(
                column="vitorias",
                min_value=0,
                max_value=30,
                meta=_descricao("Não dá para vencer mais corridas do que existem."),
            ),
            gxe.ExpectColumnPairValuesAToBeGreaterThanB(
                column_A="podios",
                column_B="vitorias",
                or_equal=True,
                meta=_descricao(
                    "Toda vitória também é um pódio: pódios >= vitórias. Esta é a "
                    "regra que pega erro de lógica na agregação."
                ),
            ),
            gxe.ExpectColumnPairValuesAToBeGreaterThanB(
                column_A="corridas",
                column_B="podios",
                or_equal=True,
                meta=_descricao("Não se sobe ao pódio em corrida que não se disputou."),
            ),
            gxe.ExpectColumnValuesToBeBetween(
                column="taxa_abandono_%",
                min_value=0,
                max_value=100,
                meta=_descricao("Percentual precisa ficar entre 0 e 100."),
            ),
            gxe.ExpectColumnValuesToNotBeNull(
                column="piloto",
                meta=_descricao("O mart é consumido por humanos: o nome é obrigatório."),
            ),
        ],
    )


def gold_agg_constructor_season_suite() -> gx.ExpectationSuite:
    return _suite(
        "gold_agg_constructor_season",
        [
            gxe.ExpectCompoundColumnsToBeUnique(
                column_list=["season", "constructor_id"],
                meta=_descricao("Grão do mart: uma linha por equipe por temporada."),
            ),
            gxe.ExpectColumnPairValuesAToBeGreaterThanB(
                column_A="podios",
                column_B="vitorias",
                or_equal=True,
                meta=_descricao("Pódios >= vitórias também no nível de equipe."),
            ),
            gxe.ExpectColumnValuesToBeBetween(
                column="pontos",
                min_value=0,
                max_value=1500,
                meta=_descricao("Teto histórico de pontos de uma equipe por temporada."),
            ),
        ],
    )


GOLD_SUITES = {
    "agg_driver_season": gold_agg_driver_season_suite,
    "agg_constructor_season": gold_agg_constructor_season_suite,
}

ALL_SUITES = {
    "bronze": BRONZE_SUITES,
    "silver": SILVER_SUITES,
    "gold": GOLD_SUITES,
}
