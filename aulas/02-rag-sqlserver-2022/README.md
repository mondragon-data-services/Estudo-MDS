# Aula 02 — Quem disse? RAG com SQL Server 2022 (sem tipo VECTOR)

Aula da Mondragon Data Services: guardar embeddings em `VARBINARY(MAX)` no
**SQL Server 2022** e calcular a similaridade semântica — na aplicação
(Python + NumPy) ou no próprio banco (T-SQL) — com um app Streamlit por cima.

O tipo `VECTOR` e a função `VECTOR_DISTANCE` só chegam no SQL Server 2025. A aula
mostra como fazer busca semântica **antes** deles, aproveitando uma novidade do
2022: o `GENERATE_SERIES`, que permite ao T-SQL ler os floats de dentro do
`VARBINARY` (função `rag.fn_VetorParaLinhas`). O banco `RagPoliticos` é criado na
instância que já existe, com nível de compatibilidade 160.

## Estrutura

```
.env.example                opcional: banco e modelo desta aula (a conexão fica no .env da raiz)
requirements.txt            dependências da aula (incluído pelo requirements.txt da raiz)
data/frases_politicos.csv   31 frases de 23 políticos e ministros do STF (texto em PT + original + fonte)
data/campos_semanticos.csv  palavras por campo semântico, usadas no mapa 3D (edite à vontade)
sql/01_criar_banco.sql      mesmo DDL do notebook 01 (tabelas, função e procedures), para o SSMS
src/config.py               banco da aula (RagPoliticos) e modelo de embeddings
src/banco.py                conectar() e executar_script() — vêm de mds_comum
src/vetores.py              vetor <-> bytes, cosseno e índice em memória
src/mapa.py                 PCA e t-SNE: achatar 384 dimensões em 3 para desenhar
notebooks/01_criar_banco.ipynb
notebooks/02_gerar_embeddings.ipynb
notebooks/03_busca_semantica.ipynb
notebooks/04_sql_server_2025_e_azure.ipynb   E no 2025? E no Azure SQL? (roteiro + medições ao vivo)
slides/notebooklm_fonte.md  conteúdo completo da aula para gerar os slides no NotebookLM
slides/notebooklm_prompt.md prompt de personalização dos slides + como usar
app/app.py                  aplicação Streamlit (navegação entre as páginas)
app/paginas/quem_disse.py   "Quem disse?": palavra-chave x semântica, em Python ou T-SQL
app/paginas/mapa_embeddings.py  "Mapa das embeddings": frases e palavras num gráfico 3D
```

## Passo a passo

1. **SQL Server** (uma vez, na raiz do repositório — serve para todas as aulas):
   ```bash
   cp .env.example .env        # ajuste SQL_SERVER para a sua instância (ex.: .\DEV2022)
   ```
   Autenticação e driver ODBC: [docs/sqlserver.md](../../docs/sqlserver.md).
2. **Ambiente Python** (uma vez, na raiz do repositório — serve para todas as aulas):
   ```bash
   .\scripts\preparar-ambiente.ps1     # Windows
   bash scripts/preparar-ambiente.sh     # Linux / macOS
   ```
3. No VS Code (extensões Python e Jupyter), abra os notebooks na ordem 01, 02, 03 e 04.
   O kernel **Python (Estudo-MDS)** já vem configurado; se o VS Code pedir, escolha
   ele (ou a `.venv` da raiz em *Python Environments*).
4. Rode o app, com a `.venv` ativa e **de dentro da pasta da aula**:
   ```bash
   .venv\Scripts\activate            # na raiz; Linux/macOS: source .venv/bin/activate
   cd aulas/02-rag-sqlserver-2022
   streamlit run app/app.py
   ```

## Notebook 04: SQL Server 2025 on-premise × Azure SQL

Fecha a aula com a pergunta "e se eu tivesse o tipo `VECTOR`?". Ao vivo, no 2022, ele
prova que `VECTOR`/`VECTOR_DISTANCE` não existem e mede a força bruta no app × no banco.
Em **roteiro T-SQL** (não executa no 2022), mostra:

* no **SQL Server 2025**, `VECTOR_DISTANCE` resolve a busca exata dentro do banco;
* o **índice vetorial on-premise** (preview) deixa a tabela **somente leitura**: o
  "Cadastrar frase ao vivo" do app quebraria (Msg 42231);
* no **Azure SQL Database** o índice versão 3 já aceita `INSERT`/`UPDATE` e se atualiza sozinho.

## O app tem duas páginas

* **Quem disse?** — digite uma ideia e descubra o autor. Compara a busca por
  palavra-chave (`LIKE`) com a semântica, calculada no Python ou no próprio banco.
* **Mapa das embeddings** — as frases da aula e 42 palavras de *campos semânticos*
  (medo e coragem, guerra, democracia, pátria…) num gráfico 3D que dá para girar.
  A busca vira um ponto ligado aos vizinhos mais próximos. Mostra também quanto o
  desenho preserva (o mapa é uma "sombra" das 384 dimensões) e os 384 números de
  cada texto lado a lado. O campo *Fora do tema* (futebol, chocolate…) serve de
  controle: fica longe de tudo.

## Observações

* O notebook 01 cria o banco `RagPoliticos` na instância compartilhada. Para usar
  outro nome, crie um `.env` nesta pasta com `SQL_DATABASE=...`.
* Na primeira execução o modelo `paraphrase-multilingual-MiniLM-L12-v2` é baixado do
  Hugging Face (cerca de 470 MB). Rode o notebook 02 antes da aula para deixar em cache.
* **Dá para repetir a aula quantas vezes quiser:** o notebook 01 apaga e recria os
  objetos (`DROP ... IF EXISTS`), e o 02 recarrega frases e embeddings. Para começar
  do zero inclusive o banco, ponha `RECRIAR_BANCO = True` na seção 3 do notebook 01.
* Requer **SQL Server 2022** (versão 16) ou mais novo: o notebook 01 confere a versão
  e define o nível de compatibilidade 160, exigido pelo `GENERATE_SERIES`.
* No app, a barra lateral alterna onde a similaridade é calculada. **Python** é mais
  rápido (vetores em memória); **T-SQL** mostra que o banco sozinho resolve e já
  enxerga frases recém-cadastradas, sem recarregar nada.
