"""
App Streamlit da aula.

Rodar (na pasta da aula):  streamlit run app/app.py
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))   # permite "from src import ..."

import pandas as pd
import streamlit as st
from mds_comum import sqlserver

from src import config

st.set_page_config(page_title="Aula NN", layout="wide")
st.title("Aula NN")

if not sqlserver.banco_existe(config.SQL_DATABASE):
    st.warning(f"O banco **{config.SQL_DATABASE}** ainda não existe. Rode o notebook 01 primeiro.")
    st.stop()

with sqlserver.conectar(config.SQL_DATABASE) as conn:
    st.dataframe(pd.read_sql("SELECT DB_NAME() AS banco, @@VERSION AS versao", conn))
