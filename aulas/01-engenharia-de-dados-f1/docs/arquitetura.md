# Decisões de arquitetura

Este documento registra **por que** o projeto é do jeito que é. Em engenharia de
dados, quase todo erro caro nasce de uma decisão que ninguém escreveu — e que
seis meses depois ninguém lembra por que foi tomada.

O formato de cada seção é sempre o mesmo: **contexto → decisão → consequência**.

---

## 1. Quatro camadas em vez de uma transformação só

**Contexto.** Seria possível ir da API direto ao gráfico em umas 40 linhas.

**Decisão.** Separar em `raw → bronze → silver → gold`, cada camada com uma
única responsabilidade.

**Consequência.**

* ✅ Bug na transformação se corrige reprocessando o `raw`, sem chamar a API.
* ✅ Cada célula do bronze é conferível contra o JSON original — auditoria real.
* ✅ A regra de negócio existe em um lugar só (silver), não espalhada.
* ❌ Mais arquivos, mais disco, mais código para ler no começo.

O custo é real, mas paga-se na primeira vez que alguém pergunta "de onde veio
esse número?".

---

## 2. RAW guarda o payload cru, não uma versão "já limpa"

**Contexto.** É tentador gravar já em tabela, com os nomes que a gente prefere.

**Decisão.** Gravar o JSON exatamente como a API devolveu, particionado por
temporada, acompanhado de `_manifest.json` com URL, horário, contagens e hash
SHA-256 de cada arquivo.

**Consequência.** O `raw` vira a fonte da verdade local. Se a API sair do ar,
mudar o contrato ou corrigir um dado retroativamente, o histórico continua aqui.
O hash permite provar que o arquivo não foi alterado depois de gravado.

---

## 3. Particionamento no padrão Hive (`season=2024/`)

**Contexto.** Poderíamos gravar tudo em um arquivo por endpoint.

**Decisão.** `data/raw/<endpoint>/season=<ano>/page_NNN.json`, e
`round=NN/` quando o endpoint é por rodada.

**Consequência.** É o padrão que Spark, DuckDB, Athena e pyarrow leem
nativamente. Mais importante: permite **reprocessar só a partição que mudou**,
em vez de tudo.

---

## 4. Parquet nas camadas tabulares, não CSV

**Contexto.** CSV é universal e legível em qualquer editor.

**Decisão.** Parquet para bronze/silver/gold, com fallback automático para CSV se
o `pyarrow` não estiver instalado (`src/f1_pipeline/utils/io.py`).

**Consequência.** Parquet é colunar, comprimido e — o que mais importa aqui —
**preserva os tipos**. Um CSV relido devolve tudo como texto, jogando fora
justamente o trabalho que a camada silver fez. O fallback garante que o projeto
roda mesmo numa instalação mínima.

---

## 5. Validação como portão entre camadas, não como etapa final

**Contexto.** O caminho comum é validar no fim, "antes de publicar".

**Decisão.** Três portões: bronze (contrato), silver (semântica), gold
(reconciliação). Em produção, `--parar-se-reprovar` interrompe o pipeline.

**Consequência.** O erro é detectado onde nasceu, não três camadas adiante. E as
perguntas são diferentes em cada portão — "a fonte mudou?" é uma pergunta
distinta de "minha agregação está certa?".

---

## 6. Suites de bronze testam forma; suites de silver/gold testam significado

**Contexto.** Na bronze todo valor ainda é texto, por decisão da camada.

**Decisão.** Bronze usa expressões regulares, conjuntos de valores, unicidade e
contagem de linhas. Silver e gold usam faixas numéricas e relações entre colunas.

**Consequência.** Não se tenta validar "pontos entre 0 e 26" sobre a string
`"26"`. Cada camada é validada com o vocabulário que ela realmente tem.

---

## 7. Toda expectativa carrega uma descrição em português

**Contexto.** A mensagem padrão do GX é
`expect_compound_columns_to_be_unique falhou em [season, round, driver_id]`.

**Decisão.** Todo `Expectation` recebe `meta={"descricao": "..."}`.

**Consequência.** O relatório e o app mostram *"Um piloto aparece uma única vez
por corrida"*. A validação deixa de ser um artefato de engenharia e vira uma
conversa possível com o time de negócio.

---

## 8. `status` classifica a corrida, e não o texto literal da API

**Contexto.** A Ergast escrevia `"+1 Lap"`; a Jolpica escreve `"Lapped"`.

**Decisão.** A regra reconhece as duas formas, e a constante
`STATUS_COMPLETOU_PREFIXOS` fica documentada em `processing/silver.py`.

**Consequência.** Este é o exemplo canônico do projeto para **erro silencioso**:
quem tivesse fixado o texto antigo passaria a contar ~10 abandonos por corrida em
vez de 0, sem nenhuma exceção sendo levantada. É a razão de existir do notebook
02.

---

## 9. Outliers são marcados, não removidos

**Contexto.** Uma parada de box sob bandeira vermelha durou 543 segundos e
destruía a média de pit stop do GP.

**Decisão.** A silver marca `parada_atipica = duracao_s > 60`; a gold calcula a
média **sem** as atípicas, mas mantém o total real de paradas.

**Consequência.** O dado verdadeiro continua lá. Quem consome escolhe a visão de
acordo com a pergunta — "quão rápido é o pit desta equipe?" e "quanto tempo os
carros ficaram parados?" são perguntas diferentes.

---

## 10. A gold é modelada pela pergunta, não pelo dado

**Contexto.** Poderíamos entregar as tabelas silver ao app e deixá-lo agregar.

**Decisão.** Uma tabela gold por pergunta de negócio, com todos os nomes
legíveis já resolvidos.

**Consequência.** O app não faz nenhum JOIN e não aplica nenhuma regra: só
desenha. Se amanhã surgir um Power BI ao lado do Streamlit, os dois lerão os
mesmos números — porque a definição está na gold, não na ferramenta.

---

## 11. O código de produção mora em `src/`, não nos notebooks

**Contexto.** Seria mais direto escrever tudo dentro do notebook.

**Decisão.** A lógica vive em `src/f1_pipeline/`, testada e importável; o
notebook narra, chama e mostra.

**Consequência.** O mesmo código roda no notebook, no `scripts/run_pipeline.py`
e nos testes. Não existe a versão "do notebook" divergindo da versão "de
produção" — um clássico das equipes de dados.

---

## 12. Duas famílias de teste, com papéis distintos

**Decisão.** Great Expectations testa o **dado** (que muda a cada execução);
pytest testa o **código** (que muda a cada commit).

**Consequência.** Uma regra como "pódios ≥ vitórias" existe nos dois lugares de
propósito: como expectativa (o dado de hoje cumpre?) e como teste unitário (a
função de agregação está correta?). São falhas diferentes com causas diferentes.

---

## 13. Limitação assumida: corridas sprint fora da carga

**Contexto.** Desde 2021 existem sprints, que valem pontos, em
`/{season}/sprint`.

**Decisão.** Não ingerir, e documentar a consequência em todos os lugares onde
o número aparece (README, rodapé do app, notebook 03).

**Consequência.** Os totais ficam abaixo do campeonato oficial. Escolha
pedagógica: dá ao aluno um exercício com resultado verificável contra a realidade
— e ensina que **limitação conhecida e documentada** é aceitável, enquanto
limitação escondida é dívida.
