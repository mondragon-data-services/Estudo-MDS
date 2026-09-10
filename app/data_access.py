"""Acesso aos dados pelo app — a camada GOLD e nada além dela.

Repare no contrato: o aplicativo **não** conhece a API da F1, não sabe o que é
paginação e não faz nenhum JOIN. Ele lê tabelas prontas. Essa separação é o que
permite trocar a fonte de dados sem tocar em uma linha da interface.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from f1_pipeline import config  # noqa: E402
from f1_pipeline.processing.gold import BUILDERS as TABELAS_GOLD  # noqa: E402
from f1_pipeline.utils.io import read_table  # noqa: E402

MENSAGEM_SEM_DADOS = """
### Os dados ainda não foram gerados

Este app lê a camada **gold**, que é produzida pelo pipeline. Rode uma vez:

```bash
python scripts/run_pipeline.py
```

ou execute os notebooks `01`, `02` e `03` na ordem.
"""


@st.cache_data(show_spinner="Carregando os marts analíticos...")
def carregar_gold() -> dict[str, pd.DataFrame]:
    """Lê todas as tabelas gold. O cache evita reler o Parquet a cada clique."""
    return {nome: read_table(config.GOLD_DIR / nome) for nome in TABELAS_GOLD}


@st.cache_data(show_spinner=False)
def carregar_relatorio_qualidade() -> dict | None:
    """Lê o relatório do Great Expectations, se o pipeline já o gerou."""
    caminho = config.REPORTS_DIR / "quality_report.json"
    if not caminho.exists():
        return None
    return json.loads(caminho.read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def metadados_gold() -> dict:
    caminho = config.GOLD_DIR / "_metadata.json"
    if not caminho.exists():
        return {}
    return json.loads(caminho.read_text(encoding="utf-8"))


def exigir_dados() -> dict[str, pd.DataFrame]:
    """Carrega a gold ou explica ao usuário como gerá-la."""
    try:
        return carregar_gold()
    except FileNotFoundError:
        st.error("Camada gold não encontrada.")
        st.markdown(MENSAGEM_SEM_DADOS)
        st.stop()


def seletor_de_temporada(dados: dict[str, pd.DataFrame], chave: str) -> int:
    """Filtro de temporada padronizado — sempre no topo, sempre igual."""
    temporadas = sorted(dados["agg_driver_season"]["season"].unique(), reverse=True)
    return st.selectbox("Temporada", temporadas, key=chave)


def rodape() -> None:
    meta = metadados_gold()
    gerado = meta.get("gerado_em", "—")
    st.markdown(
        f'<p class="rodape">Fonte: API pública Jolpica/Ergast &nbsp;·&nbsp; '
        f"camada gold gerada em {gerado} &nbsp;·&nbsp; "
        f"pontuação de corridas sprint não incluída.</p>",
        unsafe_allow_html=True,
    )
