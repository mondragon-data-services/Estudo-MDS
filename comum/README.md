# mds_comum — código compartilhado entre as aulas

Pacote pequeno, instalado em modo editável na `.venv` de cada aula que usa o
SQL Server. Ele existe para que a conexão com o banco seja **escrita uma vez**:
toda aula nova só precisa escolher o nome do seu banco.

```text
mds_comum/
├── config.py      acha a raiz do repositório e carrega os arquivos .env
└── sqlserver.py   conectar(), executar_script() (lotes com GO), garantir_banco()
```

## Como uma aula usa

No `requirements.txt` da aula:

```text
-e ../../comum
```

(o caminho é relativo à pasta da aula — rode o `pip install` de dentro dela).

No código:

```python
from mds_comum import sqlserver

with sqlserver.conectar("MeuBancoDaAula") as conn:
    ...
```

## De onde vêm as configurações

Em ordem de prioridade (o primeiro que definir a variável vence):

1. variáveis de ambiente já definidas no terminal;
2. `aulas/<aula>/.env` — valores só daquela aula (ex.: `SQL_DATABASE`);
3. `.env` na raiz do repositório — conexão com o SQL Server, comum a todas.

Alterou o código daqui? Como a instalação é editável, todas as aulas enxergam
a mudança na hora. Só reinicie o kernel do notebook ou o Streamlit.
