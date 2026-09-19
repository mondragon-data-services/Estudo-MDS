"""Conexão com o SQL Server e execução de scripts T-SQL com separador GO.

A implementação é compartilhada por todas as aulas e vive em
comum/src/mds_comum/sqlserver.py. Aqui só a reexportamos com o nome da aula,
para que os notebooks possam escrever ``banco.conectar(...)``.
"""
from mds_comum.sqlserver import conectar, executar_script

__all__ = ["conectar", "executar_script"]
