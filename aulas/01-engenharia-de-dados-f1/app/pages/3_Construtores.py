"""Página 3 — as equipes: pontuação, confiabilidade e duelos internos."""

from __future__ import annotations

import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

import theme  # noqa: E402
from data_access import exigir_dados, rodape, seletor_de_temporada  # noqa: E402

st.set_page_config(page_title="Construtores | F1 Analytics", page_icon="🏭", layout="wide")
theme.registrar_template()
st.markdown(theme.CSS_APP, unsafe_allow_html=True)

dados = exigir_dados()

st.title("🏭 Construtores")
st.caption(
    "Na F1 o campeonato de equipes é decidido por dois carros somados — por isso "
    "confiabilidade pesa tanto quanto velocidade."
)

temporada = seletor_de_temporada(dados, chave="temporada_construtores")
equipes = dados["agg_constructor_season"].query("season == @temporada").sort_values(
    "pontos", ascending=False
)

esquerda, direita = st.columns(2)

with esquerda:
    st.plotly_chart(
        theme.barra_horizontal(
            equipes,
            x="pontos",
            y="equipe",
            titulo=f"Pontos por equipe — {temporada}",
            rotulo_x="Pontos",
        ),
        key="grafico_pontos_equipe",
    )

with direita:
    st.plotly_chart(
        theme.barra_horizontal(
            equipes.sort_values("taxa_abandono_%", ascending=False),
            x="taxa_abandono_%",
            y="equipe",
            titulo=f"Taxa de abandono — {temporada}",
            rotulo_x="% das inscrições que não completaram a prova",
            cor=theme.CATEGORICA[7],
            formato_valor=".1f",
        ),
        key="grafico_abandono_equipe",
    )
    st.caption(
        "Vermelho aqui não é 'a cor da equipe': é a cor de uma métrica em que "
        "**mais é pior**. Coerência de significado é o que faz a cor informar."
    )

st.divider()

# ---------------------------------------------------------------------------
# Duelo interno: barras divergentes a partir de um zero comum
# ---------------------------------------------------------------------------
st.subheader("Duelo entre companheiros de equipe")
st.caption(
    "Confronto direto na classificação. Só contam os GPs em que os dois pilotos "
    "da equipe participaram."
)

duelos = dados["agg_teammate_battle"].query("season == @temporada")
equipe_escolhida = st.selectbox(
    "Equipe", equipes["equipe"].tolist(), key="equipe_duelo"
)
recorte = duelos[duelos["equipe"] == equipe_escolhida].sort_values(
    "vitorias_quali", ascending=False
)

if len(recorte) < 2:
    st.info("Esta equipe não teve uma dupla estável na temporada.")
else:
    figura = go.Figure()
    for i, linha in enumerate(recorte.itertuples(index=False)):
        figura.add_trace(
            go.Bar(
                x=[linha.vitorias_quali, linha.vitorias_corrida],
                y=["Classificação", "Corrida"],
                name=linha.piloto,
                orientation="h",
                marker=dict(color=theme.CATEGORICA[i % theme.MAX_SERIES], cornerradius=4),
                text=[linha.vitorias_quali, linha.vitorias_corrida],
                textposition="inside",
                insidetextfont=dict(color="#ffffff", size=13),
                hovertemplate=f"<b>{linha.piloto}</b><br>%{{y}}: %{{x}} confrontos vencidos<extra></extra>",
            )
        )
    figura.update_layout(
        title=f"Confrontos vencidos — {equipe_escolhida}, {temporada}",
        barmode="stack",
        bargap=0.45,
        xaxis_title="Confrontos diretos vencidos",
        height=300,
    )
    st.plotly_chart(figura, key="grafico_duelo_equipe")

st.subheader("Resumo das equipes")
st.dataframe(
    equipes[
        [
            "equipe",
            "gps",
            "pilotos",
            "pontos",
            "vitorias",
            "podios",
            "dobradinhas",
            "media_chegada",
            "taxa_abandono_%",
        ]
    ],
    hide_index=True,
)

rodape()
