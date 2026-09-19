# Aula NN — Título da aula

> **Modelo.** Copie esta pasta para `aulas/NN-nome-curto/`, troque `NN` e o
> título, e apague este aviso. Pastas que começam com `_` não são aulas.

Uma frase dizendo o que a pessoa vai saber fazer ao final.

## Estrutura

```
.env.example        opcional: valores só desta aula (ex.: SQL_DATABASE)
requirements.txt    dependências da aula (inclui ../../comum se usar SQL Server)
notebooks/          a aula em si, na ordem 01, 02, ...
src/                código reaproveitado pelos notebooks e pelo app
sql/                scripts T-SQL equivalentes (para rodar no SSMS)
data/               dados pequenos de exemplo
app/app.py          app Streamlit (opcional)
```

## Passo a passo

1. Conexão com o SQL Server (na raiz, uma vez): `.env` criado a partir do `.env.example`
2. Ambiente da aula (na raiz):
   ```bash
   .\scripts\preparar-aula.ps1 NN-nome-curto     # Windows
   bash scripts/preparar-aula.sh NN-nome-curto   # Linux / macOS
   ```
3. Abra os notebooks e escolha o kernel **Python (aula NN-nome-curto)**.
4. App (de dentro da pasta da aula): `streamlit run app/app.py`
