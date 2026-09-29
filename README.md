# Estudo MDS — aulas de dados da Mondragon Data Services

Repositório-livro: cada aula é um **capítulo** em sua própria pasta dentro de
[`aulas/`](aulas/), com notebooks, código, documentação e (quando faz sentido)
um app Streamlit. Tudo em português, feito para ser lido na ordem e rodado na
máquina do aluno.

## Sumário

| # | Aula | Assuntos | SQL Server? | Vídeo |
|---|---|---|:---:|---|
| 01 | [Engenharia de Dados na prática: as três fases de um pipeline](aulas/01-engenharia-de-dados-f1/) | ingestão de API, Great Expectations, bronze/silver/gold, Streamlit | — | [▶️ Assistir](https://youtu.be/XRq_M2O74Q0) |
| 02 | [Quem disse? RAG com SQL Server 2022](aulas/02-rag-sqlserver-2022/) | embeddings em `VARBINARY`, `GENERATE_SERIES`, busca semântica, RAG, Streamlit | ✅ | [▶️ Assistir](https://youtu.be/FpewoB6I1Ig) |

## Como o repositório está organizado

```text
Estudo-MDS/
├── README.md              ← este sumário
├── requirements.txt       ← ambiente único: inclui o requirements de cada aula
├── .env.example           ← conexão com o SQL Server local (copie para .env)
├── comum/                 ← pacote Python mds_comum: conexão e scripts T-SQL
├── scripts/
│   ├── preparar-ambiente.ps1  ← cria a .venv da raiz e registra o kernel
│   └── preparar-ambiente.sh
├── docs/
│   └── sqlserver.md       ← instância, autenticação, driver ODBC
└── aulas/
    ├── _modelo/           ← esqueleto para começar uma aula nova
    ├── 01-engenharia-de-dados-f1/
    └── 02-rag-sqlserver-2022/
```

Regras que deixam cada aula independente e, ao mesmo tempo, sem repetição:

1. **Cada aula é autocontida no conteúdo.** Tem o próprio `README.md` e
   `requirements.txt`. Os comandos da aula (`streamlit run ...`,
   `python scripts/...`) são executados **de dentro da pasta dela**.
2. **O ambiente Python é um só.** Uma `.venv` na raiz, com as dependências de
   todas as aulas, e um kernel — **`Python (Estudo-MDS)`** — já configurado em
   todos os notebooks. É a `.venv` que o VS Code encontra sozinho, sem precisar
   caçar interpretador.
3. **O SQL Server é um só.** Todas as aulas usam a instância que já existe na
   máquina (configurada no `.env` da raiz); cada aula cria **o seu banco**
   dentro dela (ex.: `RagPoliticos`).
4. **A conexão é escrita uma vez.** O pacote [`comum/`](comum/) vem instalado
   no ambiente; as aulas chamam `mds_comum.sqlserver.conectar("NomeDoBanco")`.
5. **Os notebooks podem ser rodados quantas vezes você quiser.** Objetos de banco
   são apagados com `DROP ... IF EXISTS` antes de serem criados — assim a criação
   fica visível na aula e nada falha com "objeto já existe" na segunda execução.

## Primeiros passos

Pré-requisitos: **Python 3.10+** e, para aulas com banco, uma instância de
**SQL Server 2022 ou mais novo** e o **ODBC Driver 18 for SQL Server**
(veja [docs/sqlserver.md](docs/sqlserver.md)).

```bash
git clone https://github.com/mondragon-data-services/Estudo-MDS.git
cd Estudo-MDS

# 1. Conexão com o SQL Server (só para aulas que usam banco)
cp .env.example .env                 # Windows: copy .env.example .env
                                     # ajuste SQL_SERVER para a sua instância

# 2. Ambiente Python (uma vez; serve para todas as aulas)
.\scripts\preparar-ambiente.ps1     # Windows (PowerShell)
bash scripts/preparar-ambiente.sh     # Linux / macOS
```

Depois, siga o README da aula. No VS Code os notebooks já abrem com o kernel
**Python (Estudo-MDS)**; se ele pedir para escolher, é esse (ou a `.venv` da
raiz, em *Python Environments*).

## Criando uma aula nova

1. Copie [`aulas/_modelo/`](aulas/_modelo/) para `aulas/NN-nome-curto/`
   (número com dois dígitos, nome em minúsculas com hífens).
2. Ajuste o `README.md`, o `requirements.txt` e o nome do banco em `src/config.py`.
3. Inclua `-r aulas/NN-nome-curto/requirements.txt` no `requirements.txt` da raiz
   e rode `scripts/preparar-ambiente` de novo.
4. Acrescente uma linha no **Sumário** acima.

## Licença

MIT.
