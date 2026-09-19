# Estudo MDS — aulas de dados da Mondragon Data Services

Repositório-livro: cada aula é um **capítulo** em sua própria pasta dentro de
[`aulas/`](aulas/), com notebooks, código, documentação e (quando faz sentido)
um app Streamlit. Tudo em português, feito para ser lido na ordem e rodado na
máquina do aluno.

## Sumário

| # | Aula | Assuntos | SQL Server? |
|---|---|---|:---:|
| 01 | [Engenharia de Dados na prática: as três fases de um pipeline](aulas/01-engenharia-de-dados-f1/) | ingestão de API, Great Expectations, bronze/silver/gold, Streamlit | — |
| 02 | [Quem disse? RAG com SQL Server 2017](aulas/02-rag-sqlserver-2017/) | embeddings em `VARBINARY`, busca semântica, RAG, Streamlit | ✅ |

## Como o repositório está organizado

```text
Estudo-MDS/
├── README.md              ← este sumário
├── .env.example           ← conexão com o SQL Server local (copie para .env)
├── comum/                 ← pacote Python mds_comum: conexão e scripts T-SQL
├── scripts/
│   ├── preparar-aula.ps1  ← cria a .venv de uma aula e registra o kernel
│   └── preparar-aula.sh
├── docs/
│   └── sqlserver.md       ← instância, autenticação, driver ODBC
└── aulas/
    ├── _modelo/           ← esqueleto para começar uma aula nova
    ├── 01-engenharia-de-dados-f1/
    └── 02-rag-sqlserver-2017/
```

Três regras deixam cada aula independente e, ao mesmo tempo, sem repetição:

1. **Cada aula é autocontida.** Tem o próprio `README.md`, `requirements.txt`
   e `.venv`. Os comandos da aula (`streamlit run ...`, `python scripts/...`)
   são executados **de dentro da pasta dela**.
2. **O SQL Server é um só.** Todas as aulas usam a instância que já existe na
   máquina (configurada no `.env` da raiz); cada aula cria **o seu banco**
   dentro dela (ex.: `RagPoliticos`).
3. **A conexão é escrita uma vez.** As aulas que usam banco instalam o pacote
   [`comum/`](comum/) (`-e ../../comum` no `requirements.txt`) e chamam
   `mds_comum.sqlserver.conectar("NomeDoBanco")`.

## Primeiros passos

Pré-requisitos: **Python 3.10+** e, para aulas com banco, uma instância de
**SQL Server 2017 ou mais novo** e o **ODBC Driver 18 for SQL Server**
(veja [docs/sqlserver.md](docs/sqlserver.md)).

```bash
git clone https://github.com/mondragon-data-services/Estudo-MDS.git
cd Estudo-MDS

# 1. Conexão com o SQL Server (só para aulas que usam banco)
cp .env.example .env                 # Windows: copy .env.example .env
                                     # ajuste SQL_SERVER para a sua instância

# 2. Ambiente de uma aula
.\scripts\preparar-aula.ps1 02-rag-sqlserver-2017     # Windows (PowerShell)
bash scripts/preparar-aula.sh 02-rag-sqlserver-2017   # Linux / macOS
```

Depois, siga o README da aula. No VS Code, abra o notebook e escolha o kernel
**Python (aula &lt;nome-da-aula&gt;)**.

## Criando uma aula nova

1. Copie [`aulas/_modelo/`](aulas/_modelo/) para `aulas/NN-nome-curto/`
   (número com dois dígitos, nome em minúsculas com hífens).
2. Ajuste o `README.md`, o `requirements.txt` e o nome do banco em `src/config.py`.
3. Rode `scripts/preparar-aula` com o nome da pasta nova.
4. Acrescente uma linha no **Sumário** acima.

## Licença

MIT.
