"""Página 5 — a qualidade dos dados exposta a quem consome o dado.

Esta página existe por um motivo pedagógico forte: **confiança em dado não se
declara, se demonstra**. O mesmo relatório que o Great Expectations gera no
pipeline aparece aqui, ao lado dos números, para quem toma decisão.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

import theme  # noqa: E402
from data_access import carregar_relatorio_qualidade, rodape  # noqa: E402

st.set_page_config(
    page_title="Qualidade dos dados | F1 Analytics", page_icon="✅", layout="wide"
)
theme.registrar_template()
st.markdown(theme.CSS_APP, unsafe_allow_html=True)

st.title("✅ Qualidade dos dados")
st.caption(
    "Resultado do Great Expectations nas três camadas: contrato da fonte "
    "(bronze), semântica do dado (silver) e reconciliação das agregações (gold)."
)

relatorio = carregar_relatorio_qualidade()

if relatorio is None:
    st.warning(
        "Nenhum relatório encontrado. Rode `python scripts/run_pipeline.py` ou o "
        "notebook `02_qualidade_great_expectations.ipynb` para gerá-lo."
    )
    st.stop()

# --- visão geral ------------------------------------------------------------
aprovadas = relatorio["regras_executadas"] - relatorio["regras_reprovadas"]
status_geral = "APROVADO" if relatorio["sucesso_geral"] else "REPROVADO"
cor_status = theme.STATUS["bom"] if relatorio["sucesso_geral"] else theme.STATUS["critico"]
icone_status = "✅" if relatorio["sucesso_geral"] else "⛔"

colunas = st.columns(4)
colunas[0].markdown(
    theme.cartao_kpi("Status geral", f"{icone_status} {status_geral}", relatorio["etapa"]),
    unsafe_allow_html=True,
)
colunas[1].markdown(
    theme.cartao_kpi(
        "Regras aprovadas",
        f"{aprovadas}/{relatorio['regras_executadas']}",
        f"{relatorio['tabelas_validadas']} tabelas validadas",
    ),
    unsafe_allow_html=True,
)
colunas[2].markdown(
    theme.cartao_kpi(
        "Regras reprovadas", f"{relatorio['regras_reprovadas']}", "0 é o alvo"
    ),
    unsafe_allow_html=True,
)
colunas[3].markdown(
    theme.cartao_kpi("Última execução", relatorio["gerado_em"][:16].replace("T", " "), "UTC"),
    unsafe_allow_html=True,
)

st.divider()

# --- por tabela -------------------------------------------------------------
resumo = pd.DataFrame(
    [
        {
            "camada": r["tabela"].split("_")[0],
            "tabela": r["tabela"],
            "regras": r["total_regras"],
            "aprovadas": r["regras_ok"],
            "reprovadas": r["regras_falhas"],
            "linhas": r["linhas_avaliadas"],
            "status": "APROVADO" if r["sucesso"] else "REPROVADO",
        }
        for r in relatorio["resultados"]
    ]
)

st.subheader("Resultado por tabela")
st.dataframe(
    resumo,
    hide_index=True,
    column_config={
        "reprovadas": st.column_config.NumberColumn("reprovadas", format="%d"),
    },
)

# --- detalhe regra a regra --------------------------------------------------
st.subheader("Regra a regra")
st.caption(
    "Cada expectativa carrega uma descrição em português. Um erro de qualidade "
    "só é útil quando quem lê entende o que ele significa para o negócio."
)

tabela_escolhida = st.selectbox("Tabela", resumo["tabela"].tolist(), key="tabela_gx")
detalhado = next(
    r for r in relatorio["resultados"] if r["tabela"] == tabela_escolhida
)

for detalhe in detalhado["detalhes"]:
    icone = "✅" if detalhe["sucesso"] else "⛔"
    with st.container(border=True):
        esquerda, direita = st.columns([3, 1])
        esquerda.markdown(
            f"{icone} **{detalhe['regra']}** — `{detalhe['coluna']}`  \n"
            f"{detalhe['descricao'] or '_sem descrição_'}"
        )
        direita.markdown(
            f"<div style='text-align:right;color:{theme.TINTA_SECUNDARIA};font-size:12px'>"
            f"{detalhe['linhas_avaliadas']:,} linhas avaliadas<br>"
            f"{detalhe['linhas_inesperadas']:,} fora do esperado "
            f"({detalhe['percentual_inesperado']:.2f}%)</div>",
            unsafe_allow_html=True,
        )
        if not detalhe["sucesso"] and detalhe["exemplos"]:
            st.code("Exemplos do que falhou: " + ", ".join(detalhe["exemplos"]))

st.info(
    "O relatório HTML completo (Data Docs) fica em `docs/data_docs/index.html` — "
    "abra no navegador para ver o histórico de todas as validações.",
    icon="📄",
)

rodape()
