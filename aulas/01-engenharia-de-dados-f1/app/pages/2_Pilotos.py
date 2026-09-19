"""Página 2 — o perfil de um piloto na temporada."""

from __future__ import annotations

import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

import theme  # noqa: E402
from data_access import exigir_dados, rodape, seletor_de_temporada  # noqa: E402

st.set_page_config(page_title="Pilotos | F1 Analytics", page_icon="🏎️", layout="wide")
theme.registrar_template()
st.markdown(theme.CSS_APP, unsafe_allow_html=True)

dados = exigir_dados()

st.title("🏎️ Perfil do piloto")
st.caption(
    "Um recorte por vez: escolha a temporada e o piloto. Números grandes para "
    "os fatos, gráficos só onde existe comparação a fazer."
)

coluna_temporada, coluna_piloto = st.columns([1, 2])
with coluna_temporada:
    temporada = seletor_de_temporada(dados, chave="temporada_pilotos")

pilotos = dados["agg_driver_season"].query("season == @temporada").sort_values(
    "pontos", ascending=False
)
with coluna_piloto:
    nome = st.selectbox("Piloto", pilotos["piloto"].tolist(), key="piloto_escolhido")

piloto = pilotos[pilotos["piloto"] == nome].iloc[0]

colunas = st.columns(5)
cartoes = [
    ("Pontos", f"{piloto['pontos']:.0f}", f"{piloto['pontos_por_corrida']:.1f} por GP"),
    ("Vitórias", f"{int(piloto['vitorias'])}", f"{int(piloto['podios'])} pódios"),
    ("Poles", f"{int(piloto['poles'])}", f"largada média: {piloto['media_grid']:.1f}"),
    (
        "Chegada média",
        f"{piloto['media_chegada']:.1f}",
        f"melhor resultado: {int(piloto['melhor_resultado'])}º",
    ),
    (
        "Abandonos",
        f"{int(piloto['abandonos'])}",
        f"{piloto['taxa_abandono_%']:.0f}% dos GPs",
    ),
]
for coluna, (rotulo, valor, apoio) in zip(colunas, cartoes):
    coluna.markdown(theme.cartao_kpi(rotulo, valor, apoio), unsafe_allow_html=True)

st.divider()

# ---------------------------------------------------------------------------
# Largada x chegada: a única forma que responde "ele ganha ou perde posições?"
# ---------------------------------------------------------------------------
progressao = dados["agg_championship_progression"].query(
    "season == @temporada and piloto == @nome"
)

esquerda, direita = st.columns(2)

with esquerda:
    st.plotly_chart(
        theme.barras_agrupadas(
            pilotos.nlargest(12, "pontos"),
            x="sigla",
            series={"media_grid": "Largada média", "media_chegada": "Chegada média"},
            titulo=f"Largada média x chegada média — {temporada}",
            rotulo_y="Posição (menor é melhor)",
        ),
        key="grafico_grid_chegada",
    )
    st.caption(
        "Barra de chegada mais baixa que a de largada = o piloto ganha posições "
        "na corrida. Mesma unidade, mesmo eixo."
    )

with direita:
    figura = go.Figure(
        go.Scatter(
            x=progressao["rodada"],
            y=progressao["posicao_campeonato"],
            mode="lines+markers",
            line=dict(width=2, color=theme.CATEGORICA[0]),
            marker=dict(size=8, line=dict(width=2, color=theme.SUPERFICIE)),
            hovertemplate="Rodada %{x}<br>%{y}º no campeonato<extra></extra>",
        )
    )
    figura.update_layout(
        title=f"Posição de {nome} no campeonato, rodada a rodada",
        xaxis_title="Rodada",
        yaxis_title="Posição no campeonato",
        yaxis=dict(autorange="reversed"),
        height=420,
    )
    st.plotly_chart(figura, key="grafico_posicao_campeonato")
    st.caption("Eixo invertido: 1º lugar no topo, como todo mundo espera ler.")

st.divider()

# ---------------------------------------------------------------------------
# Duelo com o companheiro de equipe
# ---------------------------------------------------------------------------
st.subheader("Duelo com o companheiro de equipe")
duelos = dados["agg_teammate_battle"].query("season == @temporada and piloto == @nome")

if duelos.empty:
    st.info("Sem duelos registrados: o piloto não teve companheiro fixo na temporada.")
else:
    duelo = duelos.iloc[0]
    colunas = st.columns(4)
    colunas[0].markdown(
        theme.cartao_kpi(
            "Classificação",
            f"{int(duelo['vitorias_quali'])} × {int(duelo['duelos_quali'] - duelo['vitorias_quali'])}",
            f"{duelo['aproveitamento_quali_%']:.0f}% de aproveitamento",
        ),
        unsafe_allow_html=True,
    )
    colunas[1].markdown(
        theme.cartao_kpi(
            "Corrida",
            f"{int(duelo['vitorias_corrida'])} × {int(duelo['duelos_corrida'] - duelo['vitorias_corrida'])}",
            f"{duelo['aproveitamento_corrida_%']:.0f}% de aproveitamento",
        ),
        unsafe_allow_html=True,
    )
    colunas[2].markdown(
        theme.cartao_kpi("Equipe", str(duelo["equipe"]), "duelos diretos"),
        unsafe_allow_html=True,
    )
    colunas[3].markdown(
        theme.cartao_kpi(
            "Regra do duelo",
            "só com os dois na pista",
            "abandono mecânico não conta como derrota",
        ),
        unsafe_allow_html=True,
    )

st.subheader("Todos os pilotos da temporada")
st.dataframe(
    pilotos[
        [
            "piloto",
            "equipe_principal",
            "corridas",
            "pontos",
            "vitorias",
            "podios",
            "poles",
            "media_grid",
            "media_chegada",
            "posicoes_ganhas",
            "taxa_abandono_%",
        ]
    ],
    hide_index=True,
)

rodape()
