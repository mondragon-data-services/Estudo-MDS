"""Página 4 — o que cada GP e cada circuito produzem."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

import theme  # noqa: E402
from data_access import exigir_dados, rodape, seletor_de_temporada  # noqa: E402

st.set_page_config(
    page_title="Corridas e circuitos | F1 Analytics", page_icon="🛞", layout="wide"
)
theme.registrar_template()
st.markdown(theme.CSS_APP, unsafe_allow_html=True)

dados = exigir_dados()

st.title("🛞 Corridas e circuitos")

aba_corridas, aba_circuitos = st.tabs(["Por corrida", "Por circuito"])

# ---------------------------------------------------------------------------
with aba_corridas:
    temporada = seletor_de_temporada(dados, chave="temporada_corridas")
    corridas = dados["agg_race_summary"].query("season == @temporada").sort_values(
        "rodada"
    )

    colunas = st.columns(4)
    cartoes = [
        ("GPs", f"{len(corridas)}", f"{int(corridas['paradas_totais'].sum())} pit stops"),
        (
            "Pit stop médio",
            f"{corridas['duracao_media_pit_s'].mean():.1f}s",
            f"mais rápido: {corridas['duracao_minima_pit_s'].min():.1f}s",
        ),
        (
            "Pole virou vitória",
            f"{100 * corridas['pole_venceu'].mean():.0f}%",
            "das corridas da temporada",
        ),
        (
            "Abandonos por GP",
            f"{corridas['abandonos'].mean():.1f}",
            f"máximo: {int(corridas['abandonos'].max())}",
        ),
    ]
    for coluna, (rotulo, valor, apoio) in zip(colunas, cartoes):
        coluna.markdown(theme.cartao_kpi(rotulo, valor, apoio), unsafe_allow_html=True)

    st.plotly_chart(
        theme.barra_horizontal(
            corridas.assign(rotulo=corridas["rodada"].astype(str) + ". " + corridas["gp"]),
            x="abandonos",
            y="rotulo",
            titulo=f"Abandonos por GP — {temporada}",
            rotulo_x="Carros que não completaram a prova",
            cor=theme.CATEGORICA[7],
        ),
        key="grafico_abandonos_gp",
    )

    st.dataframe(
        corridas[
            [
                "rodada",
                "gp",
                "circuito",
                "pais",
                "vencedor",
                "equipe_vencedora",
                "pole",
                "pole_venceu",
                "abandonos",
                "paradas_totais",
                "duracao_media_pit_s",
            ]
        ],
        hide_index=True,
    )

# ---------------------------------------------------------------------------
with aba_circuitos:
    circuitos = dados["agg_circuit_stats"]
    st.caption(
        "Agregado de todas as temporadas carregadas: cada circuito tem uma "
        "'personalidade' — uns punem o carro, outros premiam a estratégia."
    )

    esquerda, direita = st.columns(2)
    with esquerda:
        st.plotly_chart(
            theme.barra_horizontal(
                circuitos.nlargest(12, "media_abandonos"),
                x="media_abandonos",
                y="circuito",
                titulo="Circuitos que mais quebram carros",
                rotulo_x="Média de abandonos por GP",
                cor=theme.CATEGORICA[7],
                formato_valor=".1f",
            ),
            key="grafico_circuitos_abandono",
        )
    with direita:
        st.plotly_chart(
            theme.barra_horizontal(
                circuitos.nlargest(12, "movimentacao_media_posicoes"),
                x="movimentacao_media_posicoes",
                y="circuito",
                titulo="Circuitos onde o grid mais se mexe",
                rotulo_x="Média de posições ganhas ou perdidas por piloto",
                cor=theme.CATEGORICA[2],
                formato_valor=".1f",
            ),
            key="grafico_circuitos_movimento",
        )

    if {"lat", "lon"}.issubset(circuitos.columns):
        st.subheader("Onde ficam")
        mapa = circuitos.dropna(subset=["lat", "lon"])[["lat", "lon"]]
        st.map(mapa, size=40, color="#2a78d6")

    st.dataframe(circuitos, hide_index=True)

rodape()
