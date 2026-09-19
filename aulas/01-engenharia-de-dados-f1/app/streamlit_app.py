"""FASE 3 — ANALYTICS: a camada que as pessoas realmente veem.

Rode com:

    streamlit run app/streamlit_app.py

Este arquivo é a página inicial. As demais páginas estão em ``app/pages/`` e o
Streamlit as descobre sozinho, montando o menu lateral pela ordem do nome do
arquivo.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR))

import theme  # noqa: E402
from data_access import exigir_dados, rodape, seletor_de_temporada  # noqa: E402

st.set_page_config(
    page_title="F1 Analytics | Engenharia de Dados",
    page_icon="🏁",
    layout="wide",
)
theme.registrar_template()
st.markdown(theme.CSS_APP, unsafe_allow_html=True)

dados = exigir_dados()

# ---------------------------------------------------------------------------
# Cabeçalho
# ---------------------------------------------------------------------------
st.title("🏁 F1 Analytics")
st.caption(
    "Fase 3 de 3 do pipeline: ingestão → processamento → **analytics**. "
    "Tudo nesta tela vem da camada *gold*, sem nenhuma transformação feita aqui."
)

temporada = seletor_de_temporada(dados, chave="temporada_home")

pilotos = dados["agg_driver_season"].query("season == @temporada")
equipes = dados["agg_constructor_season"].query("season == @temporada")
corridas = dados["agg_race_summary"].query("season == @temporada")

# ---------------------------------------------------------------------------
# KPIs — quando a resposta é um número só, mostre o número, não um gráfico
# ---------------------------------------------------------------------------
campeao = pilotos.iloc[0]
equipe_campea = equipes.iloc[0]

colunas = st.columns(5)
cartoes = [
    ("Corridas", f"{len(corridas)}", f"{corridas['largaram'].sum()} inscrições"),
    ("Pilotos", f"{pilotos['driver_id'].nunique()}", f"{len(equipes)} equipes"),
    (
        "Campeão",
        campeao["sigla"] if campeao["sigla"] else campeao["piloto"],
        f"{campeao['piloto']} · {campeao['pontos']:.0f} pts",
    ),
    (
        "Equipe campeã",
        equipe_campea["equipe"],
        f"{equipe_campea['pontos']:.0f} pts · {equipe_campea['vitorias']} vitórias",
    ),
    (
        "Abandonos",
        f"{int(corridas['abandonos'].sum())}",
        f"{corridas['taxa_abandono_%'].mean():.1f}% das largadas",
    ),
]
for coluna, (rotulo, valor, apoio) in zip(colunas, cartoes):
    coluna.markdown(theme.cartao_kpi(rotulo, valor, apoio), unsafe_allow_html=True)

st.divider()

# ---------------------------------------------------------------------------
# Dois gráficos: comparar equipes e comparar pilotos
# ---------------------------------------------------------------------------
esquerda, direita = st.columns(2)

with esquerda:
    st.plotly_chart(
        theme.barra_horizontal(
            equipes.sort_values("pontos", ascending=False),
            x="pontos",
            y="equipe",
            titulo=f"Pontos por equipe — {temporada}",
            rotulo_x="Pontos no campeonato de construtores",
        ),
        key="grafico_equipes",
    )

with direita:
    top10 = pilotos.nlargest(10, "pontos")
    st.plotly_chart(
        theme.barra_horizontal(
            top10,
            x="pontos",
            y="piloto",
            titulo=f"Top 10 pilotos — {temporada}",
            rotulo_x="Pontos no campeonato de pilotos",
            cor=theme.CATEGORICA[1],
        ),
        key="grafico_pilotos",
    )

# ---------------------------------------------------------------------------
# Tabela — o "table view" que garante acessibilidade dos gráficos acima
# ---------------------------------------------------------------------------
st.subheader("Classificação de pilotos")
tabela = pilotos[
    [
        "piloto",
        "equipe_principal",
        "corridas",
        "pontos",
        "vitorias",
        "podios",
        "poles",
        "media_chegada",
        "taxa_abandono_%",
    ]
].rename(
    columns={
        "piloto": "Piloto",
        "equipe_principal": "Equipe",
        "corridas": "GPs",
        "pontos": "Pontos",
        "vitorias": "Vitórias",
        "podios": "Pódios",
        "poles": "Poles",
        "media_chegada": "Chegada média",
        "taxa_abandono_%": "Abandono %",
    }
)
st.dataframe(tabela, hide_index=True)

with st.expander("Como esta tela foi construída (as três fases do pipeline)"):
    st.markdown(
        """
| Fase | O que acontece | Onde ver |
|---|---|---|
| **1. Ingestão** | Um cliente HTTP com retry e rate limit lê a API pública da F1 e grava o JSON cru, particionado por temporada, com manifesto e hash. | `notebooks/01_ingestao.ipynb` |
| **1.5 Qualidade** | O Great Expectations valida o contrato da fonte antes de qualquer transformação, e revalida depois. | `notebooks/02_qualidade_great_expectations.ipynb` |
| **2. Processamento** | `bronze` (tabular fiel) → `silver` (tipado e modelado em estrela) → `gold` (agregações). | `notebooks/03_processamento_agregacoes.ipynb` |
| **3. Analytics** | Este app. Ele só lê a `gold` — nenhuma regra de negócio mora aqui. | `notebooks/04_analytics.ipynb` |
        """
    )

rodape()
