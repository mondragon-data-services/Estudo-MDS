# SQL Server compartilhado

Todas as aulas usam **a mesma instância de SQL Server que já existe na sua
máquina** (aqui, a instância nomeada `DEV2022`, SQL Server 2022). Cada aula
cria o **seu próprio banco** dentro dela — ex.: `RagPoliticos` — então as aulas
não se atrapalham e nenhum banco que você já tem é tocado.

## Configurar (uma vez)

Na raiz do repositório:

```bash
cp .env.example .env          # Windows: copy .env.example .env
```

e ajuste `SQL_SERVER` para a sua instância:

| Situação | `SQL_SERVER` |
|---|---|
| Instância nomeada (ex.: Developer/Express) | `.\DEV2022`, `.\SQLEXPRESS` |
| Instância padrão | `localhost` |
| Outra máquina ou porta fixa (exige TCP habilitado) | `servidor,1433` |

Não sabe o nome da instância? No PowerShell:

```powershell
Get-Service MSSQL*        # MSSQL$DEV2022 -> instância ".\DEV2022"; MSSQLSERVER -> "localhost"
```

### Autenticação

* **Windows (padrão, recomendado):** `SQL_TRUSTED_CONNECTION=yes`. Usa o seu
  usuário do Windows; nenhuma senha fica em arquivo. Seu usuário precisa poder
  criar bancos (`dbcreator` ou `sysadmin`) — quem instalou o SQL Server já tem.
* **SQL Server (usuário e senha):** `SQL_TRUSTED_CONNECTION=no` e preencha
  `SQL_USER` / `SQL_PASSWORD`. Exige a instância em modo misto.

O `.env` está no `.gitignore`: ele nunca vai para o GitHub.

## Driver ODBC (uma vez por máquina)

O Python conversa com o SQL Server pelo **ODBC Driver 18 for SQL Server**:

* **Windows:** instalador da Microsoft ("ODBC Driver 18 for SQL Server").
  Confira com `Get-OdbcDriver -Name *SQL*`.
* **Mac:** `brew tap microsoft/mssql-release https://github.com/Microsoft/homebrew-mssql-release && brew install msodbcsql18`
* **Linux:** pacote `msodbcsql18` do repositório da Microsoft.

## Conferir a conexão

```bash
sqlcmd -S .\DEV2022 -E -C -Q "SELECT @@VERSION"
```

ou, pelo Python de qualquer aula que use banco:

```python
from mds_comum import sqlserver
sqlserver.conectar().execute("SELECT @@VERSION").fetchone()
```

## Versão do SQL Server

As aulas são escritas para rodar em **SQL Server 2017 ou mais novo**: nada do
que usamos exige recurso recente. A instância local é 2022 — funciona igual.

## Não tem SQL Server instalado?

Instale o **SQL Server 2022 Developer** (gratuito) ou suba um container:

```bash
docker run -d --name mds-sqlserver -e ACCEPT_EULA=Y -e "MSSQL_SA_PASSWORD=Aula@MDS2022!" \
  -p 1433:1433 mcr.microsoft.com/mssql/server:2022-latest
```

e use no `.env`: `SQL_SERVER=localhost,1433`, `SQL_TRUSTED_CONNECTION=no`,
`SQL_USER=sa`, `SQL_PASSWORD=Aula@MDS2022!`.
