"""Recursos compartilhados pelas páginas do app (carregados uma vez por servidor)."""
import sys
from pathlib import Path

PASTA_AULA = Path(__file__).resolve().parents[1]
if str(PASTA_AULA) not in sys.path:
    sys.path.append(str(PASTA_AULA))   # permite "from src import ..."

import numpy as np
import pandas as pd
import streamlit as st
from sentence_transformers import SentenceTransformer

from src import banco, config
from src.vetores import IndiceEmMemoria


@st.cache_resource(show_spinner="Carregando o modelo de embeddings...")
def carregar_modelo():
    return SentenceTransformer(config.MODELO_EMBEDDING)


@st.cache_resource(show_spinner="Lendo os vetores do SQL Server 2022...")
def carregar_indice():
    with banco.conectar(config.SQL_DATABASE) as conn:
        indice = IndiceEmMemoria.do_banco(conn, config.MODELO_EMBEDDING)
        frases = pd.read_sql("SELECT * FROM rag.vw_Frases", conn).set_index("FraseId")
    return indice, frases


@st.cache_data(show_spinner="Transformando textos em vetores...")
def vetorizar(textos: tuple[str, ...]) -> np.ndarray:
    """Embeddings normalizados de uma lista de textos (em cache: a lista é a chave)."""
    return carregar_modelo().encode(list(textos), normalize_embeddings=True)


@st.cache_data
def carregar_campos_semanticos() -> pd.DataFrame:
    """Palavras agrupadas por campo semântico. Edite data/campos_semanticos.csv à vontade."""
    return pd.read_csv(PASTA_AULA / "data" / "campos_semanticos.csv")
