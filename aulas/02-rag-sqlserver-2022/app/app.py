"""
Quem disse? Busca semântica de frases de políticos
SQL Server 2022 (vetores em VARBINARY) + similaridade calculada no Python
ou no próprio banco (T-SQL com GENERATE_SERIES).

Rodar (na pasta da aula):  streamlit run app/app.py

Este arquivo só monta a navegação; cada página vive em app/paginas/.
"""
import streamlit as st

st.set_page_config(page_title="Quem disse?", page_icon="🗣️", layout="wide")

navegacao = st.navigation([
    st.Page("paginas/quem_disse.py", title="Quem disse?", icon="🗣️", default=True),
    st.Page("paginas/mapa_embeddings.py", title="Mapa das embeddings", icon="🧭"),
])
navegacao.run()
