# 🏁 Engenharia de Dados na prática: as três fases de um pipeline

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Great Expectations](https://img.shields.io/badge/Great%20Expectations-1.x-ff6310)
![Streamlit](https://img.shields.io/badge/Streamlit-1.49%2B-FF4B4B?logo=streamlit&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-2.x-150458?logo=pandas&logoColor=white)
![Licença](https://img.shields.io/badge/licen%C3%A7a-MIT-green)

Projeto didático que constrói, do zero e ponta a ponta, um pipeline de dados
real usando a **API pública da Fórmula 1** — da ingestão até um aplicativo
analítico que qualquer pessoa consegue usar.

> Feito para ser lido na ordem, rodado na máquina do aluno e publicado no
> GitHub. Todo o conteúdo está em português, em cinco notebooks comentados.

```
   FASE 1: INGESTÃO            FASE 2: PROCESSAMENTO         FASE 3: ANALYTICS
 ┌───────────────────┐      ┌──────────────────────────┐   ┌──────────────────┐
 │  API pública F1   │      │  bronze → silver → gold  │   │  App Streamlit   │
 │  (Jolpica/Ergast) │      │                          │   │                  │
 └─────────┬─────────┘      └────────────┬─────────────┘   └────────▲─────────┘
           │                             │                          │
           ▼                             ▼                          │
     data/raw/*.json  ──────────►  data/bronze  ──► data/silver ──► data/gold
     (JSON cru,                   (tabular,        (tipado,       (agregado,
      particionado,                fiel à           modelo         pronto para
      com manifesto)               fonte)           estrela)       consumo)
           │                             │                          │
           └────────► ✅ GREAT EXPECTATIONS valida cada passagem ◄───┘
                    (contrato da fonte, semântica, reconciliação)
```

| Fase | Ferramenta | Pergunta que responde |
|---|---|---|
| **1. Ingestão** | Python + `requests` + `tenacity` | Como trago o dado sem perder nada e sem derrubar a fonte? |
| **1.5 Qualidade** | **Great Expectations** | Posso confiar no que acabei de trazer? |
| **2. Processamento** | Python + pandas + Parquet | Como transformo isso em algo que responde perguntas? |
| **3. Analytics** | **Streamlit** + Plotly | Como coloco isso na mão de quem decide? |

---

## Começando

Pré-requisito: **Python 3.10 ou superior**.

```bash
git clone https://github.com/mondragon-data-services/Estudo-MDS.git
cd Estudo-MDS

python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux / macOS

pip install -r requirements.txt
```

Ou, se preferir, use o script pronto — ele também registra o kernel do Jupyter:

```bash
.\scripts\setup.ps1             # Windows (PowerShell)
bash scripts/setup.sh           # Linux / macOS
```

### Rodar o pipeline inteiro (≈ 3 minutos)

```bash
python scripts/run_pipeline.py --seasons 2021-2024
```

```
ingestão → bronze → [PORTÃO 1] → silver → [PORTÃO 2] → gold → [PORTÃO 3] → Data Docs
```

| Opção | Para quê |
|---|---|
| `--seasons 2024` | carregar só uma temporada (mais rápido para a primeira aula) |
| `--skip-ingest` | reprocessar a partir do `raw`, sem tocar na API |
| `--no-overwrite` | carga incremental: baixa só o que ainda não existe |
| `--parar-se-reprovar` | comportamento de produção: qualidade reprovada interrompe o pipeline |

### Abrir o aplicativo analítico

```bash
streamlit run app/streamlit_app.py
```

A camada `gold` já vem versionada no repositório, então o app funciona
**logo após o clone**, mesmo antes de rodar o pipeline.

### Seguir a aula pelos notebooks

```bash
jupyter lab notebooks/
```

Os cinco notebooks **já vêm com todas as saídas salvas**: dá para ler a aula
inteira aqui no GitHub, sem instalar nada. Rodar é necessário só para mexer no
código ou executar ao vivo em sala.

<details>
<summary><b>Prefere o VS Code? Leia isto antes</b> — dois tropeços comuns</summary>

<br>

**1. O botão ▶ não faz nada.** Falta a extensão Jupyter (as extensões
`ms-python.*` sozinhas não executam notebooks):

```bash
code --install-extension ms-toolsai.jupyter
```

Depois recarregue a janela: `Ctrl+Shift+P` → `Developer: Reload Window`.

**2. O kernel não aparece na lista.** Registre o ambiente do projeto:

```bash
.venv\Scripts\python.exe -m ipykernel install --user --name f1-pipeline --display-name "Python (f1-pipeline)"
```

No notebook, clique em **Select Kernel** (canto superior direito) e escolha
**`Python (f1-pipeline)`**.

**Em qualquer um dos casos:** a primeira célula de cada notebook é o *bootstrap*
(configura o `sys.path` e importa o `pandas`). Rode-a antes das demais, senão as
seguintes falham com `NameError`.

</details>

> **Windows:** se `python` não for reconhecido no terminal, o Python não está no
> PATH. Use o interpretador do ambiente virtual diretamente —
> `.venv\Scripts\python.exe -m streamlit run app/streamlit_app.py` — ou ative o
> ambiente com `.venv\Scripts\activate`.

---

## A aula, em cinco notebooks

| # | Notebook | O que o aluno faz |
|---|---|---|
| 00 | [`00_visao_geral.ipynb`](notebooks/00_visao_geral.ipynb) | Entende as três fases, a arquitetura em camadas e a fonte de dados. Faz a primeira requisição à API. |
| 01 | [`01_ingestao.ipynb`](notebooks/01_ingestao.ipynb) | Paginação, rate limit, retry com backoff, camada raw particionada, manifesto com SHA-256, idempotência e ingestão em *fan-out*. |
| 02 | [`02_qualidade_great_expectations.ipynb`](notebooks/02_qualidade_great_expectations.ipynb) | Monta uma suite de expectativas peça por peça, valida a camada bronze, **quebra o dado de propósito** para ver o portão fechar e gera os Data Docs. |
| 03 | [`03_processamento_agregacoes.ipynb`](notebooks/03_processamento_agregacoes.ipynb) | Tipagem, regras de negócio, modelo estrela (dimensões e fatos), seis marts analíticos e reconciliação gold × silver. |
| 04 | [`04_analytics.ipynb`](notebooks/04_analytics.ipynb) | Princípios de visualização (forma antes de cor), gráficos, um anti-padrão lado a lado e a construção do app Streamlit. |

Todos os notebooks estão **executados e com as saídas salvas** — dá para ler
tudo direto no GitHub, sem rodar nada.

---

## Estrutura do repositório

```
Estudo-MDS/
├── notebooks/               # A aula: 00 a 04, na ordem
│
├── src/f1_pipeline/         # O código de produção que os notebooks chamam
│   ├── config.py            #   toda configuração em um lugar só
│   ├── cli.py               #   orquestrador do pipeline (o "DAG")
│   ├── ingestion/           #   FASE 1: cliente HTTP, catálogo de endpoints, jobs
│   ├── quality/             #   Great Expectations: contexto + suites de regras
│   ├── processing/          #   FASE 2: bronze.py → silver.py → gold.py
│   └── utils/               #   logging padronizado e entrada/saída de arquivos
│
├── app/                     # FASE 3: aplicativo Streamlit multipágina
│   ├── streamlit_app.py     #   página inicial: KPIs e visão geral
│   ├── theme.py             #   paleta validada, template Plotly, componentes
│   ├── data_access.py       #   leitura da gold com cache
│   └── pages/               #   Campeonato, Pilotos, Construtores, Corridas, Qualidade
│
├── data/                    # raw → bronze → silver → gold
├── gx/                      # projeto Great Expectations (suites versionadas)
├── docs/data_docs/          # relatório HTML das validações (gerado)
├── reports/                 # relatório de qualidade em JSON (lido pelo app)
├── scripts/run_pipeline.py  # o pipeline inteiro em um comando
└── tests/                   # pytest: testa a LÓGICA (o GX testa o DADO)
```

**Por que o código não mora dentro dos notebooks?** Notebook é ótimo para
*explicar* e péssimo para *reusar*. A lógica vive em `src/`, testada e
importável; o notebook conta a história, chama a lógica e mostra o resultado.

---

## As camadas de dados (arquitetura *medallion*)

| Camada | Regra | O que se ganha |
|---|---|---|
| **raw** | grava o payload **exatamente** como veio da API | achou um bug 3 meses depois? reprocessa sem chamar a API de novo |
| **bronze** | achata para tabela, **sem** converter tipo nem filtrar | cada célula pode ser conferida contra o JSON: é auditável |
| **silver** | tipa, limpa, aplica regra de negócio e modela em estrela | uma única definição de "abandono" para o projeto inteiro |
| **gold** | agrega por pergunta de negócio | o app não faz JOIN nem regra: ele só desenha |

### O modelo dimensional (silver)

```
        dim_driver ─┐
     dim_constructor┼─► fact_result ◄── dim_race ──► dim_circuit
                    ┘   (grão: 1 piloto × 1 corrida)
```

### Os marts analíticos (gold)

| Tabela | Pergunta que responde |
|---|---|
| `agg_driver_season` | Como foi a temporada de cada piloto? |
| `agg_constructor_season` | Como foi a temporada de cada equipe? |
| `agg_race_summary` | O que aconteceu em cada GP? |
| `agg_championship_progression` | Como o campeonato evoluiu rodada a rodada? |
| `agg_circuit_stats` | Que tipo de corrida cada circuito produz? |
| `agg_teammate_battle` | Quem venceu o duelo interno de cada equipe? |

---

## Qualidade de dados

**55 expectativas em 10 tabelas**, distribuídas em três portões:

| Portão | Camada | O que verifica | Exemplos |
|---|---|---|---|
| 1 | bronze | **contrato da fonte** (forma) | as colunas existem? `points` casa com `^\d+(\.\d+)?$`? a chave (temporada, rodada, piloto) é única? |
| 2 | silver | **semântica** (significado) | pontuação entre 0 e 26; grid entre 0 e 30; `finalizou` é booleano de verdade |
| 3 | gold | **reconciliação** | pódios ≥ vitórias; corridas ≥ pódios; percentuais entre 0 e 100 |

Cada expectativa carrega uma descrição em português — é ela que aparece no
relatório e na página **Qualidade dos Dados** do app. Um erro de qualidade só é
útil quando quem lê entende o que ele significa para o negócio.

Saídas geradas:

* `docs/data_docs/index.html` — relatório HTML completo (Data Docs)
* `reports/quality_report.json` — resumo consumido pelo app

---

## O aplicativo

| Página | Conteúdo |
|---|---|
| **Início** | KPIs da temporada, pontos por equipe, top 10 pilotos, classificação |
| **Campeonato** | Pontos acumulados rodada a rodada, conquistas, vencedores de GP |
| **Pilotos** | Perfil individual, largada × chegada, posição no campeonato, duelo interno |
| **Construtores** | Pontos, confiabilidade e confronto direto entre companheiros |
| **Corridas e circuitos** | Abandonos, pit stops, mapa dos circuitos |
| **Qualidade dos dados** | O resultado do Great Expectations, regra a regra |

As cores seguem uma paleta categórica de ordem fixa, validada para daltonismo, e
a mesma paleta é usada nos notebooks — só muda a ferramenta (matplotlib gera
imagem estática que aparece no GitHub; Plotly gera interatividade no app).

---

## Testes

```bash
pytest -q
```

Duas famílias de testes, com papéis diferentes:

* `tests/test_transformacoes.py` — a **lógica**: conversão de tempo, regra do
  `Lapped`, grid do pit lane, tipos e reconciliação da agregação;
* `tests/test_app.py` — a **interface**: todas as páginas do Streamlit carregam
  sem exceção (usando o `AppTest` do próprio Streamlit).

> O Great Expectations testa o **dado**; o pytest testa o **código**. Um não
> substitui o outro.

---

## A fonte de dados

[**Jolpica-F1 API**](https://github.com/jolpica/jolpica-f1) — sucessora mantida
pela comunidade da clássica Ergast API, desativada no fim de 2024. Pública,
sem chave de acesso, mesmo contrato da Ergast.

```
https://api.jolpi.ca/ergast/f1/{temporada}/results.json?limit=100&offset=0
```

**Limites respeitados pelo cliente:** ~4 requisições por segundo, máximo de 100
registros por página, `User-Agent` identificando o projeto. Uma API pública
gratuita é mantida por voluntários — ingestão educada é o que a mantém no ar.

### Limitação conhecida (proposital)

Os totais de pontos ficam **abaixo do campeonato oficial** porque este projeto
não ingere as corridas **sprint** (endpoint `/{season}/sprint`). Isso é
intencional: virou o exercício 1 do notebook 01.

---

## Para quem vai dar a aula

Sugestão de divisão em quatro encontros:

| Encontro | Notebooks | Conceitos-chave |
|---|---|---|
| 1 | 00 e 01 | Camadas, raw sagrado, paginação, rate limit, retry, idempotência, linhagem |
| 2 | 02 | Erro silencioso, contrato de dados, expectativas, `mostly`, portão de qualidade |
| 3 | 03 | Tipagem, regra de negócio centralizada, grão, modelo estrela, outliers, reconciliação |
| 4 | 04 + app | Escolha de forma, papéis da cor, anti-padrões, cache, qualidade exposta ao usuário |

Cada notebook termina com **exercícios**, do mais simples (ingerir mais um
endpoint) ao mais aberto (criar uma métrica nova com a expectativa que a
protege).

---

## Licença

MIT — use, adapte e ensine à vontade.

Os dados da Fórmula 1 são fornecidos pela Jolpica-F1 API sob os termos dela.
Este projeto não tem qualquer vínculo com a Formula One Group.
