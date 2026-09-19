"""SILVER -> GOLD: as agregações que respondem perguntas de negócio.

A camada gold é a única que o consumidor final (o app Streamlit, um BI, um
relatório) enxerga. Cada tabela aqui existe para responder **uma pergunta**:

``agg_driver_season``           Como foi a temporada de cada piloto?
``agg_constructor_season``      Como foi a temporada de cada equipe?
``agg_race_summary``            O que aconteceu em cada GP?
``agg_championship_progression`` Como o campeonato evoluiu corrida a corrida?
``agg_circuit_stats``           Que tipo de corrida cada circuito produz?
``agg_teammate_battle``         Quem ganhou o duelo interno de cada equipe?

Regra de ouro: **quem consome a gold não deveria precisar de nenhum JOIN.**
Todo nome legível (piloto, equipe, GP) já vem resolvido.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from f1_pipeline import config
from f1_pipeline.processing.silver import load_silver
from f1_pipeline.utils.io import read_table, write_json, write_table
from f1_pipeline.utils.logging import get_logger

logger = get_logger(__name__)


def _percentual(numerador: pd.Series, denominador: pd.Series) -> pd.Series:
    """Percentual seguro: divisão por zero vira ausência de valor, não erro."""
    num = pd.to_numeric(numerador, errors="coerce").astype("float64")
    den = pd.to_numeric(denominador, errors="coerce").astype("float64")
    return (100 * num / den.where(den != 0)).round(1)


def _resultados_enriquecidos(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """fact_result + dimensões, já com nomes legíveis. Base de quase tudo."""
    return (
        silver["fact_result"]
        .merge(silver["dim_driver"][["driver_id", "piloto", "sigla", "nacionalidade"]], on="driver_id", how="left")
        .merge(silver["dim_constructor"][["constructor_id", "equipe"]], on="constructor_id", how="left")
        .merge(
            silver["dim_race"][["race_key", "gp", "data", "circuit_id"]],
            on="race_key",
            how="left",
        )
        .merge(
            silver["dim_circuit"][["circuit_id", "circuito", "pais"]],
            on="circuit_id",
            how="left",
        )
    )


# ---------------------------------------------------------------------------
# 1. Desempenho do piloto na temporada
# ---------------------------------------------------------------------------


def build_agg_driver_season(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    resultados = _resultados_enriquecidos(silver)
    quali = silver["fact_qualifying"]

    agregado = (
        resultados.groupby(["season", "driver_id", "piloto", "sigla"], as_index=False)
        .agg(
            corridas=("race_key", "nunique"),
            pontos=("points", "sum"),
            vitorias=("vitoria", "sum"),
            podios=("podio", "sum"),
            corridas_pontuadas=("pontuou", "sum"),
            abandonos=("abandonou", "sum"),
            media_chegada=("position", "mean"),
            media_grid=("grid_efetivo", "mean"),
            melhor_resultado=("position", "min"),
            posicoes_ganhas=("posicoes_ganhas", "sum"),
            voltas=("laps", "sum"),
        )
        .round({"media_chegada": 2, "media_grid": 2})
    )

    # Poles vêm da classificação, não do resultado da corrida.
    # `.fillna(False).astype(bool)` não é preciosismo: uma coluna booleana com
    # ausência de valor não pode ser usada como máscara direta no pandas.
    eh_pole = quali["pole"].fillna(False).astype(bool)
    poles = (
        quali[eh_pole]
        .groupby(["season", "driver_id"], as_index=False)
        .agg(poles=("pole", "sum"))
    )
    agregado = agregado.merge(poles, on=["season", "driver_id"], how="left")
    agregado["poles"] = pd.to_numeric(agregado["poles"]).fillna(0).astype(int)

    # Equipe principal do piloto na temporada (a que ele mais correu).
    equipe_principal = (
        resultados.groupby(["season", "driver_id", "equipe"], as_index=False)
        .size()
        .sort_values("size", ascending=False)
        .drop_duplicates(subset=["season", "driver_id"])
        .rename(columns={"equipe": "equipe_principal"})
        .drop(columns="size")
    )
    agregado = agregado.merge(equipe_principal, on=["season", "driver_id"], how="left")

    agregado["taxa_abandono_%"] = _percentual(agregado["abandonos"], agregado["corridas"])
    agregado["taxa_pontuacao_%"] = _percentual(
        agregado["corridas_pontuadas"], agregado["corridas"]
    )
    agregado["pontos_por_corrida"] = (
        agregado["pontos"] / agregado["corridas"].replace(0, pd.NA)
    ).round(2)

    for coluna in ("vitorias", "podios", "abandonos", "corridas_pontuadas"):
        agregado[coluna] = agregado[coluna].astype(int)

    return agregado.sort_values(
        ["season", "pontos"], ascending=[True, False]
    ).reset_index(drop=True)


# ---------------------------------------------------------------------------
# 2. Desempenho da equipe na temporada
# ---------------------------------------------------------------------------


def build_agg_constructor_season(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    resultados = _resultados_enriquecidos(silver)

    agregado = (
        resultados.groupby(["season", "constructor_id", "equipe"], as_index=False)
        .agg(
            gps=("race_key", "nunique"),
            inscricoes=("driver_id", "size"),
            pilotos=("driver_id", "nunique"),
            pontos=("points", "sum"),
            vitorias=("vitoria", "sum"),
            podios=("podio", "sum"),
            abandonos=("abandonou", "sum"),
            media_chegada=("position", "mean"),
            posicoes_ganhas=("posicoes_ganhas", "sum"),
        )
        .round({"media_chegada": 2})
    )

    # Dobradinha = as duas primeiras posições no mesmo GP.
    top2 = resultados[resultados["position"] <= 2]
    dobradinhas = (
        top2.groupby(["season", "constructor_id", "race_key"], as_index=False)
        .size()
        .query("size == 2")
        .groupby(["season", "constructor_id"], as_index=False)
        .size()
        .rename(columns={"size": "dobradinhas"})
    )
    agregado = agregado.merge(dobradinhas, on=["season", "constructor_id"], how="left")
    agregado["dobradinhas"] = pd.to_numeric(agregado["dobradinhas"]).fillna(0).astype(int)

    agregado["taxa_abandono_%"] = _percentual(
        agregado["abandonos"], agregado["inscricoes"]
    )
    for coluna in ("vitorias", "podios", "abandonos"):
        agregado[coluna] = agregado[coluna].astype(int)

    return agregado.sort_values(
        ["season", "pontos"], ascending=[True, False]
    ).reset_index(drop=True)


# ---------------------------------------------------------------------------
# 3. Resumo de cada GP
# ---------------------------------------------------------------------------


def build_agg_race_summary(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    resultados = _resultados_enriquecidos(silver)
    quali = silver["fact_qualifying"].merge(
        silver["dim_driver"][["driver_id", "piloto"]], on="driver_id", how="left"
    )
    paradas = silver["fact_pit_stop"]

    base = (
        resultados.groupby(
            ["race_key", "season", "rodada", "gp", "data", "circuito", "pais"],
            as_index=False,
        )
        .agg(
            largaram=("driver_id", "nunique"),
            abandonos=("abandonou", "sum"),
            pontos_distribuidos=("points", "sum"),
            volta_mais_rapida_kph=("volta_rapida_kph", "max"),
        )
    )
    base["abandonos"] = base["abandonos"].astype(int)
    base["taxa_abandono_%"] = _percentual(base["abandonos"], base["largaram"])

    vencedores = (
        resultados[resultados["position"] == 1][["race_key", "piloto", "equipe"]]
        .rename(columns={"piloto": "vencedor", "equipe": "equipe_vencedora"})
    )
    poles = (
        quali[quali["posicao_grid"] == 1][["race_key", "piloto"]]
        .rename(columns={"piloto": "pole"})
    )
    # Uma parada sob bandeira vermelha pode durar 9 minutos e destruir a média
    # do GP inteiro. Reportamos as duas visões: a média só das paradas normais
    # (a que responde "quão rápido é o pit desta equipe?") e o total real.
    paradas_normais = paradas[~paradas["parada_atipica"]]
    pit = (
        paradas.groupby("race_key", as_index=False)
        .agg(paradas_totais=("parada", "size"))
        .merge(
            paradas_normais.groupby("race_key", as_index=False)
            .agg(
                duracao_media_pit_s=("duracao_s", "mean"),
                duracao_minima_pit_s=("duracao_s", "min"),
            )
            .round({"duracao_media_pit_s": 2, "duracao_minima_pit_s": 2}),
            on="race_key",
            how="left",
        )
    )

    resumo = (
        base.merge(vencedores, on="race_key", how="left")
        .merge(poles, on="race_key", how="left")
        .merge(pit, on="race_key", how="left")
    )
    resumo["pole_venceu"] = resumo["pole"] == resumo["vencedor"]
    return resumo.sort_values(["season", "rodada"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# 4. Evolução do campeonato corrida a corrida
# ---------------------------------------------------------------------------


def build_agg_championship_progression(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Pontos acumulados por rodada — a "corrida dentro da corrida".

    Detalhe técnico importante: um piloto que falta a um GP não tem linha
    naquela rodada. Se simplesmente acumulássemos, a curva dele sumiria do
    gráfico. Por isso completamos a malha (todas as rodadas x todos os
    pilotos da temporada) antes de acumular.
    """
    resultados = _resultados_enriquecidos(silver)
    pontos = resultados.groupby(
        ["season", "rodada", "driver_id"], as_index=False
    )["points"].sum()

    blocos = []
    for season, grupo in pontos.groupby("season"):
        rodadas = sorted(grupo["rodada"].unique())
        pilotos = sorted(grupo["driver_id"].unique())
        malha = pd.MultiIndex.from_product(
            [rodadas, pilotos], names=["rodada", "driver_id"]
        ).to_frame(index=False)
        malha["season"] = season
        bloco = malha.merge(
            grupo, on=["season", "rodada", "driver_id"], how="left"
        ).fillna({"points": 0.0})
        bloco = bloco.sort_values("rodada")
        bloco["pontos_acumulados"] = bloco.groupby("driver_id")["points"].cumsum()
        bloco["posicao_campeonato"] = (
            bloco.groupby("rodada")["pontos_acumulados"]
            .rank(ascending=False, method="min")
            .astype(int)
        )
        blocos.append(bloco)

    progressao = pd.concat(blocos, ignore_index=True).rename(
        columns={"points": "pontos_na_corrida"}
    )
    progressao = progressao.merge(
        silver["dim_driver"][["driver_id", "piloto", "sigla"]], on="driver_id", how="left"
    ).merge(
        silver["dim_race"][["season", "rodada", "gp"]],
        on=["season", "rodada"],
        how="left",
    )
    return progressao.sort_values(["season", "rodada", "posicao_campeonato"]).reset_index(
        drop=True
    )


# ---------------------------------------------------------------------------
# 5. Perfil de cada circuito
# ---------------------------------------------------------------------------


def build_agg_circuit_stats(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    corridas = build_agg_race_summary(silver)
    estatisticas = (
        corridas.groupby(["circuito", "pais"], as_index=False)
        .agg(
            gps_disputados=("race_key", "nunique"),
            media_abandonos=("abandonos", "mean"),
            media_paradas=("paradas_totais", "mean"),
            duracao_media_pit_s=("duracao_media_pit_s", "mean"),
            velocidade_maxima_kph=("volta_mais_rapida_kph", "max"),
            taxa_pole_vitoria_ate_100=("pole_venceu", "mean"),
        )
        .round(
            {
                "media_abandonos": 2,
                "media_paradas": 2,
                "duracao_media_pit_s": 2,
            }
        )
    )
    estatisticas["taxa_pole_vitoria_%"] = (
        100 * estatisticas.pop("taxa_pole_vitoria_ate_100")
    ).round(1)

    # Quanto se ganha (ou perde) de posição, em média, neste circuito?
    resultados = _resultados_enriquecidos(silver)
    ultrapassagens = (
        resultados.groupby("circuito", as_index=False)["posicoes_ganhas"]
        .apply(lambda s: s.abs().mean())
        .rename(columns={"posicoes_ganhas": "movimentacao_media_posicoes"})
    )
    estatisticas = estatisticas.merge(ultrapassagens, on="circuito", how="left")
    estatisticas["movimentacao_media_posicoes"] = estatisticas[
        "movimentacao_media_posicoes"
    ].round(2)

    # Coordenadas vêm junto para o mart poder virar um mapa sem novo JOIN.
    estatisticas = estatisticas.merge(
        silver["dim_circuit"][["circuito", "cidade", "lat", "lon"]],
        on="circuito",
        how="left",
    )

    return estatisticas.sort_values("gps_disputados", ascending=False).reset_index(
        drop=True
    )


# ---------------------------------------------------------------------------
# 6. Duelo entre companheiros de equipe
# ---------------------------------------------------------------------------


def build_agg_teammate_battle(silver: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """O confronto direto que todo fã de F1 discute: quem bate o companheiro?

    Só contamos o duelo quando os dois pilotos da equipe participaram — na
    corrida, só quando ambos completaram a prova (senão um abandono mecânico
    contaria como "derrota" do outro piloto).
    """
    quali = silver["fact_qualifying"]
    resultados = silver["fact_result"]

    placar: dict[tuple, dict] = {}

    def _registrar(chave, campo, incremento=1):
        registro = placar.setdefault(
            chave,
            {
                "season": chave[0],
                "constructor_id": chave[1],
                "driver_id": chave[2],
                "duelos_quali": 0,
                "vitorias_quali": 0,
                "duelos_corrida": 0,
                "vitorias_corrida": 0,
            },
        )
        registro[campo] += incremento

    for (_, season, constructor_id), grupo in quali.groupby(
        ["race_key", "season", "constructor_id"]
    ):
        if len(grupo) != 2:
            continue
        a, b = grupo.itertuples(index=False)
        for chave in ((season, constructor_id, a.driver_id), (season, constructor_id, b.driver_id)):
            _registrar(chave, "duelos_quali")
        vencedor = a if a.posicao_grid < b.posicao_grid else b
        _registrar((season, constructor_id, vencedor.driver_id), "vitorias_quali")

    for (_, season, constructor_id), grupo in resultados.groupby(
        ["race_key", "season", "constructor_id"]
    ):
        if len(grupo) != 2 or not grupo["finalizou"].all():
            continue
        a, b = grupo.itertuples(index=False)
        for chave in ((season, constructor_id, a.driver_id), (season, constructor_id, b.driver_id)):
            _registrar(chave, "duelos_corrida")
        vencedor = a if a.position < b.position else b
        _registrar((season, constructor_id, vencedor.driver_id), "vitorias_corrida")

    duelos = pd.DataFrame(placar.values())
    if duelos.empty:
        return duelos

    duelos = duelos.merge(
        silver["dim_driver"][["driver_id", "piloto"]], on="driver_id", how="left"
    ).merge(
        silver["dim_constructor"][["constructor_id", "equipe"]],
        on="constructor_id",
        how="left",
    )
    duelos["aproveitamento_quali_%"] = _percentual(
        duelos["vitorias_quali"], duelos["duelos_quali"]
    )
    duelos["aproveitamento_corrida_%"] = _percentual(
        duelos["vitorias_corrida"], duelos["duelos_corrida"]
    )
    return duelos.sort_values(["season", "equipe", "piloto"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Orquestração da camada
# ---------------------------------------------------------------------------

BUILDERS = {
    "agg_driver_season": build_agg_driver_season,
    "agg_constructor_season": build_agg_constructor_season,
    "agg_race_summary": build_agg_race_summary,
    "agg_championship_progression": build_agg_championship_progression,
    "agg_circuit_stats": build_agg_circuit_stats,
    "agg_teammate_battle": build_agg_teammate_battle,
}


def build_gold(
    silver: dict[str, pd.DataFrame] | None = None,
    *,
    silver_dir: Path | None = None,
    gold_dir: Path | None = None,
    salvar: bool = True,
) -> dict[str, pd.DataFrame]:
    """Constrói todos os marts analíticos."""
    gold_dir = Path(gold_dir or config.GOLD_DIR)
    silver = silver or load_silver(silver_dir)

    tabelas: dict[str, pd.DataFrame] = {}
    for nome, builder in BUILDERS.items():
        df = builder(silver)
        tabelas[nome] = df
        if salvar:
            destino = write_table(df, gold_dir / nome)
            logger.info(
                "GOLD %-32s | %6d linhas | %2d colunas -> %s",
                nome,
                len(df),
                df.shape[1],
                destino.name,
            )
        else:
            logger.info("GOLD %-32s | %6d linhas (não gravado)", nome, len(df))

    if salvar:
        write_json(
            {
                "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "temporadas": list(config.SEASONS),
                "tabelas": {nome: len(df) for nome, df in tabelas.items()},
            },
            gold_dir / "_metadata.json",
        )
    return tabelas


def load_gold(gold_dir: Path | None = None) -> dict[str, pd.DataFrame]:
    """Lê a camada gold do disco — é o que o app Streamlit consome."""
    gold_dir = Path(gold_dir or config.GOLD_DIR)
    return {nome: read_table(gold_dir / nome) for nome in BUILDERS}
