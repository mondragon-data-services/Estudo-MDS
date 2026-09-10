"""Página 1 — a evolução do campeonato corrida a corrida."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

import theme  # noqa: E402
from data_access import exigir_dados, rodape, seletor_de_temporada  # noqa: E402

st.set_page_config(page_title="Campeonato | F1 Analytics", page_icon="🏆", layout="wide")
theme.registrar_template()
st.markdown(theme.CSS_APP, unsafe_allow_html=True)

dados = exigir_dados()

st.title("🏆 A corrida pelo título")
st.caption(
    "Pontos acumulados rodada a rodada. A **linha** é a forma certa aqui porque "
    "a pergunta é sobre *evolução no tempo*, não sobre comparar totais."
)

temporada = seletor_de_temporada(dados, chave="temporada_campeonato")

progressao = dados["agg_championship_progression"].query("season == @temporada")
pilotos = dados["agg_driver_season"].query("season == @temporada")

# Máximo de 8 séries: acima disso nenhuma paleta segura distingue as linhas.
# Em vez de "inventar" uma nona cor, limitamos a seleção — essa é a decisão
# correta de visualização, não uma limitação técnica.
ordem_por_pontos = pilotos.sort_values("pontos", ascending=False)["piloto"].tolist()
padrao = ordem_por_pontos[:5]

selecionados = st.multiselect(
    f"Pilotos no gráfico (máximo {theme.MAX_SERIES})",
    options=ordem_por_pontos,
    default=padrao,
    max_selections=theme.MAX_SERIES,
)

if not selecionados:
    st.info("Escolha pelo menos um piloto para desenhar o gráfico.")
else:
    # A cor segue o piloto, e não a posição dele na lista: trocar a seleção
    # não repinta quem já estava no gráfico.
    cores = theme.cores_por_entidade(ordem_por_pontos[: theme.MAX_SERIES])
    for piloto in selecionados:
        cores.setdefault(piloto, theme.CATEGORICA[len(cores) % theme.MAX_SERIES])

    recorte = progressao[progressao["piloto"].isin(selecionados)].sort_values(
        ["piloto", "rodada"]
    )
    st.plotly_chart(
        theme.linha_temporal(
            recorte,
            x="rodada",
            y="pontos_acumulados",
            serie="piloto",
            titulo=f"Pontos acumulados — {temporada}",
            rotulo_y="Pontos acumulados",
            cores=cores,
        ),
        key="grafico_progressao",
    )

    with st.expander("Ver os mesmos dados em tabela"):
        st.dataframe(
            recorte.pivot_table(
                index="rodada", columns="piloto", values="pontos_acumulados"
            ),
        )

st.divider()

esquerda, direita = st.columns(2)

with esquerda:
    st.plotly_chart(
        theme.barras_agrupadas(
            pilotos.nlargest(10, "pontos"),
            x="sigla",
            series={"vitorias": "Vitórias", "podios": "Pódios", "poles": "Poles"},
            titulo=f"Vitórias, pódios e poles — {temporada}",
            rotulo_y="Quantidade",
        ),
        key="grafico_conquistas",
    )
    st.caption(
        "As três medidas dividem a mesma escala (contagem), então cabem no "
        "mesmo eixo. Medidas de escalas diferentes exigiriam dois gráficos."
    )

with direita:
    corridas = dados["agg_race_summary"].query("season == @temporada")
    vencedores = (
        corridas.groupby("vencedor", as_index=False)
        .size()
        .rename(columns={"size": "vitorias"})
        .sort_values("vitorias", ascending=False)
    )
    st.plotly_chart(
        theme.barra_horizontal(
            vencedores,
            x="vitorias",
            y="vencedor",
            titulo=f"Quem venceu os GPs de {temporada}",
            rotulo_x="Vitórias",
            cor=theme.CATEGORICA[2],
        ),
        key="grafico_vencedores",
    )

rodape()
