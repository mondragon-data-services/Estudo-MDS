"""Configuração da aula.

A conexão com o SQL Server (servidor, usuário, senha, driver) é a mesma para
todas as aulas e vem do .env da RAIZ do repositório. Aqui ficam só os valores
desta aula, que podem ser sobrescritos em aulas/02-rag-sqlserver-2017/.env.
"""
import os
from pathlib import Path

from mds_comum import config as comum

PASTA_AULA = Path(__file__).resolve().parents[1]
comum.carregar_env(PASTA_AULA)

_sql = comum.sqlserver()
SQL_SERVER   = _sql.servidor
SQL_USER     = _sql.usuario
SQL_PASSWORD = _sql.senha
ODBC_DRIVER  = _sql.driver

# Banco desta aula dentro da instância compartilhada.
SQL_DATABASE = os.getenv("SQL_DATABASE", "RagPoliticos")

# Modelo multilíngue: entende português, inglês, francês, alemão...
# 384 dimensões, roda em CPU, não precisa de chave de API.
MODELO_EMBEDDING = os.getenv(
    "MODELO_EMBEDDING",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)
