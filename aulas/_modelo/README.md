# Aula NN — Título da aula

> **Modelo.** Copie esta pasta para `aulas/NN-nome-curto/`, troque `NN` e o
> título, e apague este aviso. Pastas que começam com `_` não são aulas.

Uma frase dizendo o que a pessoa vai saber fazer ao final.

## Estrutura

```
.env.example        opcional: valores só desta aula (ex.: SQL_DATABASE)
requirements.txt    dependências da aula (incluído pelo requirements.txt da raiz)
notebooks/          a aula em si, na ordem 01, 02, ...
src/                código reaproveitado pelos notebooks e pelo app
sql/                scripts T-SQL equivalentes (para rodar no SSMS)
data/               dados pequenos de exemplo
app/app.py          app Streamlit (opcional)
```

## Convenções das aulas

* Os notebooks rodam **na ordem** (01, 02, ...) e podem ser repetidos à vontade:
  cada objeto de banco é apagado com `DROP ... IF EXISTS` antes de ser criado.
* A criação fica explícita (nada de `IF ... IS NULL`), porque em aula o que
  interessa é mostrar o objeto nascendo.
* A ordem do `DROP` é a inversa da criação: procedures e views, depois tabelas
  filhas, depois tabelas mãe, tipos e, por último, o schema.

## Passo a passo

1. Conexão com o SQL Server (na raiz, uma vez): `.env` criado a partir do `.env.example`
2. Inclua a aula no `requirements.txt` da raiz (`-r aulas/NN-nome-curto/requirements.txt`)
   e atualize o ambiente (na raiz):
   ```bash
   .\scripts\preparar-ambiente.ps1     # Windows
   bash scripts/preparar-ambiente.sh     # Linux / macOS
   ```
3. Abra os notebooks: o kernel **Python (Estudo-MDS)** já vem configurado.
4. App (de dentro da pasta da aula): `streamlit run app/app.py`
