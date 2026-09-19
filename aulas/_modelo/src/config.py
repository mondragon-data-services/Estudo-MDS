"""Configuração da aula.

A conexão com o SQL Server vem do .env da RAIZ do repositório (mds_comum).
Aqui ficam só os valores desta aula, sobrescrevíveis no .env desta pasta.
"""
import os
from pathlib import Path

from mds_comum import config as comum

PASTA_AULA = Path(__file__).resolve().parents[1]
comum.carregar_env(PASTA_AULA)

# Banco desta aula dentro da instância compartilhada. Use um nome por aula.
SQL_DATABASE = os.getenv("SQL_DATABASE", "AulaNN")
