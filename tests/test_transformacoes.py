"""Testes das regras de transformação.

Por que testar um projeto de dados? Porque a maior parte dos erros de pipeline
não quebra a execução — ela produz um número errado silenciosamente. O
Great Expectations cuida do *dado*; o pytest cuida da *lógica*.

Rode com:  pytest -q
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from f1_pipeline.processing.gold import build_agg_driver_season
from f1_pipeline.processing.silver import (
    build_fact_result,
    chave_corrida,
    tempo_para_segundos,
)


class TestTempoParaSegundos:
    @pytest.mark.parametrize(
        "entrada,esperado",
        [
            ("1:32.608", 92.608),
            ("22.343", 22.343),
            ("0:59.999", 59.999),
            ("2:04.500", 124.5),
        ],
    )
    def test_converte_formatos_validos(self, entrada, esperado):
        assert tempo_para_segundos(entrada) == pytest.approx(esperado)

    @pytest.mark.parametrize("entrada", [None, "", "sem tempo", float("nan")])
    def test_valores_invalidos_viram_nan(self, entrada):
        assert math.isnan(tempo_para_segundos(entrada))

    def test_ordenacao_so_faz_sentido_depois_de_converter(self):
        """O bug clássico: '1:02.000' é menor que '59.000' como TEXTO."""
        assert "1:02.000" < "59.000"  # ordenação alfabética — errada
        assert tempo_para_segundos("1:02.000") > tempo_para_segundos("59.000")


def test_chave_corrida_ordena_corretamente():
    chaves = chave_corrida(pd.Series(["2024", "2024"]), pd.Series(["2", "10"]))
    assert chaves.tolist() == ["2024-02", "2024-10"]
    assert chaves[0] < chaves[1]  # o zero à esquerda é o que garante isso


@pytest.fixture
def bronze_results_minimo() -> pd.DataFrame:
    """Uma corrida com 3 pilotos: um vence, um toma volta, um abandona."""
    base = {
        "season": "2024",
        "round": "1",
        "race_name": "GP de Teste",
        "date": "2024-03-02",
        "driver_code": None,
        "driver_number": "1",
        "given_name": "Piloto",
        "family_name": "Teste",
        "driver_nationality": "Brazilian",
        "date_of_birth": "1990-01-01",
        "constructor_name": "Equipe Teste",
        "constructor_nationality": "Brazilian",
        "time_millis": None,
        "time_text": None,
        "fastest_lap_rank": None,
        "fastest_lap_number": None,
        "fastest_lap_time": None,
        "fastest_lap_speed_kph": None,
    }
    return pd.DataFrame(
        [
            {**base, "driver_id": "a", "constructor_id": "x", "grid": "1", "position": "1",
             "position_text": "1", "points": "25", "laps": "57", "status": "Finished"},
            {**base, "driver_id": "b", "constructor_id": "y", "grid": "5", "position": "2",
             "position_text": "2", "points": "18", "laps": "56", "status": "Lapped"},
            {**base, "driver_id": "c", "constructor_id": "y", "grid": "0", "position": "3",
             "position_text": "R", "points": "0", "laps": "10", "status": "Retired"},
        ]
    )


class TestFactResult:
    def test_quem_toma_volta_nao_e_abandono(self, bronze_results_minimo):
        """A regra que mais deu trabalho: 'Lapped' completou a prova."""
        fato = build_fact_result(bronze_results_minimo)
        abandonos = fato.set_index("driver_id")["abandonou"]
        assert abandonos["a"] is False or not abandonos["a"]
        assert not abandonos["b"], "quem tomou volta terminou a corrida"
        assert abandonos["c"], "quem abandonou tem de contar como abandono"

    def test_grid_zero_vira_ultimo_lugar(self, bronze_results_minimo):
        """Grid 0 = largada do pit lane; tratamos como último para o cálculo."""
        fato = build_fact_result(bronze_results_minimo).set_index("driver_id")
        assert fato.loc["c", "grid_efetivo"] == 3
        assert fato.loc["c", "posicoes_ganhas"] == 0

    def test_posicoes_ganhas(self, bronze_results_minimo):
        fato = build_fact_result(bronze_results_minimo).set_index("driver_id")
        assert fato.loc["b", "posicoes_ganhas"] == 3  # largou 5º, chegou 2º

    def test_tipos_ficam_numericos(self, bronze_results_minimo):
        fato = build_fact_result(bronze_results_minimo)
        assert pd.api.types.is_numeric_dtype(fato["points"])
        assert pd.api.types.is_numeric_dtype(fato["position"])


def test_gold_nunca_tem_mais_vitorias_que_podios(bronze_results_minimo):
    """A mesma regra que o Great Expectations valida, agora como teste."""
    silver = {
        "fact_result": build_fact_result(bronze_results_minimo),
        "fact_qualifying": pd.DataFrame(
            columns=["season", "driver_id", "pole", "posicao_grid"]
        ),
        "dim_driver": pd.DataFrame(
            {
                "driver_id": ["a", "b", "c"],
                "piloto": ["A", "B", "C"],
                "sigla": ["AAA", "BBB", "CCC"],
                "nacionalidade": ["BR", "BR", "BR"],
            }
        ),
        "dim_constructor": pd.DataFrame(
            {"constructor_id": ["x", "y"], "equipe": ["X", "Y"]}
        ),
        "dim_race": pd.DataFrame(
            {
                "race_key": ["2024-01"],
                "gp": ["GP de Teste"],
                "data": pd.to_datetime(["2024-03-02"]),
                "circuit_id": ["teste"],
            }
        ),
        "dim_circuit": pd.DataFrame(
            {"circuit_id": ["teste"], "circuito": ["Autódromo"], "pais": ["Brazil"]}
        ),
    }
    agregado = build_agg_driver_season(silver)
    assert (agregado["podios"] >= agregado["vitorias"]).all()
    assert (agregado["corridas"] >= agregado["podios"]).all()
    assert agregado["pontos"].sum() == 43.0
