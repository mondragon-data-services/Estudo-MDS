# Aula 02 — Quem disse? RAG com SQL Server 2017 (sem tipo VECTOR)

Aula da Mondragon Data Services: guardar embeddings em `VARBINARY(MAX)` no SQL Server
e calcular a similaridade semântica na aplicação (Python + NumPy + Streamlit).

A técnica só usa recursos do **SQL Server 2017** — ou seja, funciona em qualquer
versão sem o tipo `VECTOR`. Na aula rodamos na instância local (2022), em um banco novo.

## Estrutura

```
.env.example                opcional: banco e modelo desta aula (a conexão fica no .env da raiz)
requirements.txt            inclui ../../comum (conexão compartilhada com o SQL Server)
data/frases_politicos.csv   21 frases de 18 políticos (texto em PT + original)
sql/01_criar_banco.sql      mesmo DDL do notebook 01, para SSMS/sqlcmd
src/config.py               banco da aula (RagPoliticos) e modelo de embeddings
src/banco.py                conectar() e executar_script() — vêm de mds_comum
src/vetores.py              vetor <-> bytes, cosseno e índice em memória
notebooks/01_criar_banco.ipynb
notebooks/02_gerar_embeddings.ipynb
notebooks/03_busca_semantica.ipynb
app/app.py                  aplicação Streamlit "Quem disse?"
```

## Passo a passo

1. **SQL Server** (uma vez, na raiz do repositório — serve para todas as aulas):
   ```bash
   cp .env.example .env        # ajuste SQL_SERVER para a sua instância (ex.: .\DEV2022)
   ```
   Autenticação e driver ODBC: [docs/sqlserver.md](../../docs/sqlserver.md).
2. **Ambiente Python da aula** (na raiz do repositório):
   ```bash
   .\scripts\preparar-aula.ps1 02-rag-sqlserver-2017     # Windows
   bash scripts/preparar-aula.sh 02-rag-sqlserver-2017   # Linux / macOS
   ```
3. No VS Code (extensões Python e Jupyter), abra os notebooks na ordem 01, 02, 03
   e selecione o kernel **Python (aula 02-rag-sqlserver-2017)**.
4. Rode o app, **de dentro da pasta da aula**:
   ```bash
   cd aulas/02-rag-sqlserver-2017
   .venv\Scripts\activate            # Linux/macOS: source .venv/bin/activate
   streamlit run app/app.py
   ```

## Observações

* O notebook 01 cria o banco `RagPoliticos` na instância compartilhada. Para usar
  outro nome, crie um `.env` nesta pasta com `SQL_DATABASE=...`.
* Na primeira execução o modelo `paraphrase-multilingual-MiniLM-L12-v2` é baixado do
  Hugging Face (cerca de 470 MB). Rode o notebook 02 antes da aula para deixar em cache.
* O código não usa nada que não exista no SQL Server 2017; funciona igual em 2019/2022.
