"""Conexão com o SQL Server e execução de scripts T-SQL com separador GO."""

from __future__ import annotations

import re

import pyodbc

from . import config


def conectar(database: str | None = None, autocommit: bool = False) -> pyodbc.Connection:
    """Abre conexão com o SQL Server. database=None conecta no master."""
    cfg = config.sqlserver()
    if cfg.autenticacao_windows:
        credenciais = "Trusted_Connection=yes;"      # usuário logado no Windows
    else:
        credenciais = f"UID={cfg.usuario};PWD={cfg.senha};"
    cs = (
        f"DRIVER={{{cfg.driver}}};"
        f"SERVER={cfg.servidor};"
        f"{credenciais}"
        f"DATABASE={database or 'master'};"
        "TrustServerCertificate=yes;Encrypt=no;"
    )
    return pyodbc.connect(cs, autocommit=autocommit)


def executar_script(conn: pyodbc.Connection, script: str) -> None:
    """Executa um script T-SQL dividido por linhas 'GO' (como no SSMS)."""
    lotes = re.split(r"^\s*GO\s*$", script, flags=re.MULTILINE | re.IGNORECASE)
    cur = conn.cursor()
    for lote in lotes:
        if lote.strip():
            cur.execute(lote)
    if not conn.autocommit:
        conn.commit()


def garantir_banco(nome: str) -> None:
    """Cria o banco da aula na instância compartilhada, se ainda não existir."""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", nome):
        raise ValueError(f"Nome de banco inválido: {nome!r}")
    with conectar(autocommit=True) as conn:   # CREATE DATABASE exige autocommit
        conn.execute(f"IF DB_ID(N'{nome}') IS NULL CREATE DATABASE [{nome}];")


def banco_existe(nome: str) -> bool:
    with conectar() as conn:
        return conn.execute("SELECT DB_ID(?)", nome).fetchone()[0] is not None
