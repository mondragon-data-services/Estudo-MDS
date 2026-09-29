# Aula 02 — "Quem disse?": busca semântica com SQL Server 2022 (sem tipo VECTOR)

**Documento-fonte para geração de slides.** Contém todo o conteúdo da aula, os números
medidos de verdade nos notebooks, as analogias, a descrição das ilustrações e as notas
do apresentador. Mondragon Data Services — curso de Engenharia de Dados.

---

## 0. Ficha da aula

| Item | Conteúdo |
|---|---|
| Público | alunos de dados/engenharia de dados; conhecem SQL básico; **não** precisam saber IA |
| Duração | 2 horas (com 4 demonstrações ao vivo) |
| Ferramentas | SQL Server 2022, Python, notebooks Jupyter, app Streamlit "Quem disse?" |
| Base de dados da aula | **31 frases de 23 políticos e ministros do STF**: frases históricas (Churchill, Lincoln, Kennedy, Roosevelt, Getúlio Vargas, JK, Ulysses Guimarães, Mandela, Merkel…), frases polêmicas de Jair Bolsonaro durante a pandemia (2020) e falas de ministros do STF (Barroso em 2022; Gilmar Mendes, Edson Fachin, André Mendonça e Alexandre de Moraes na sessão de 15/09/2026). Todas as frases recentes têm fonte jornalística. |
| Modelo de IA | `paraphrase-multilingual-MiniLM-L12-v2`: gratuito, roda na CPU, entende vários idiomas, gera vetores de **384 números** |

### Objetivos (o aluno sai sabendo)
1. Explicar o que é um **embedding** e por que "perto = sentido parecido".
2. Guardar embeddings no **SQL Server 2022**, que **não tem** tipo de vetor, usando `VARBINARY`.
3. Fazer **busca semântica** e comparar com a busca por palavra-chave (`LIKE`).
4. Entender o **"R" do RAG** (Retrieval: buscar o contexto certo para um LLM).
5. Saber o que muda no **SQL Server 2025** e no **Azure SQL**, incluindo a limitação do índice vetorial on-premise.

---

## 1. Identidade visual e regras de ergonomia cognitiva

### Cores com significado fixo (usar sempre a mesma cor para a mesma coisa)
| Cor | Hex | Significa |
|---|---|---|
| Azul | `#2a78d6` | SQL Server **2022** / a nossa aula |
| Laranja | `#eb6834` | SQL Server **2025** on-premise |
| Verde-água | `#1baf7a` | **Azure SQL** (nuvem) |
| Vermelho | `#d03b3b` | **somente** alertas e limitações (a "pegadinha") |
| Cinza | `#898781` | coisas fora do tema / secundárias |
| Fundo | `#f9f9f7` (claro) | texto principal `#0b0b0b` |

### Personagens visuais recorrentes (mesma metáfora do começo ao fim)
- 🧭 **GPS de significado** — o modelo coloca cada frase num ponto de um mapa.
- 📦 **Caixa lacrada** — o vetor guardado em `VARBINARY`: o banco guarda, mas não sabe abrir.
- 📚 **Bibliotecário** — o SQL Server. No 2022 ele só guarda caixas lacradas; no 2025 ele sabe ler as impressões digitais.
- 🔦 **Sombra na parede** — o gráfico 3D: achatar 384 dimensões em 3 perde detalhe.
- 🔒 **Cadeado** — a tabela que vira somente leitura com índice vetorial no 2025 on-premise.

### Regras de ergonomia cognitiva
- **Uma ideia por slide.** O título é a conclusão (uma frase-afirmação), não um tema.
- **No máximo 3 itens** por slide, com até ~12 palavras cada.
- **Número grande** quando houver um número importante (ex.: "11×", "1.536 bytes").
- **Imagem + frase curta** (codificação dupla); sem parágrafos longos.
- **Código com no máximo 6 linhas**, só o essencial, com a linha importante destacada.
- **Sinalização**: destacar 1 elemento por slide (cor, seta ou círculo).
- **Indicador de progresso** (Parte 1 de 5…) e **slide de recapitulação** ao fim de cada parte.
- Slides marcados com 🎬 são momentos de **demonstração ao vivo** (o professor sai do slide).

---

## 2. Roteiro slide a slide

> Formato de cada slide: **Título** (a mensagem) · Conteúdo · Ilustração · 🗣️ Nota do apresentador.

### ABERTURA

**Slide 1 — Capa**
- Título: **Quem disse? Busca semântica com SQL Server 2022**
- Subtítulo: Embeddings, `VARBINARY` e o "R" do RAG — sem o tipo `VECTOR`
- Ilustração: balões de fala de políticos famosos flutuando e convergindo para um cilindro de banco de dados azul; do cilindro saem pontos ligados por linhas finas (uma constelação).

**Slide 2 — Você lembra da ideia, não da frase exata**
- Conteúdo: *"Quem disse que a única coisa que devemos temer é o próprio medo?"* → fácil. Agora: *"Quem falou sobre ter coragem para enfrentar o pânico?"*
- Ilustração: pessoa pensativa com um balão contendo um ícone de coração/escudo (coragem), e um ponto de interrogação.
- 🗣️ Pergunte à turma. A resposta é Franklin D. Roosevelt (1933) — mas nenhuma palavra da pergunta aparece na frase dele.

**Slide 3 — O `LIKE` procura letras, não significados**
- Conteúdo: busca por `coragem` → **0 resultados**. Seis perguntas escritas "com outras palavras" → `LIKE` achou **0 em todas**; a busca semântica acertou todas.
- Exemplos reais medidos:
  - "não desistir nunca da luta" → **Churchill**: "Lutaremos nas praias… nunca nos renderemos."
  - "democracia é o povo governando" → **Lincoln**: "O governo do povo, pelo povo e para o povo…"
  - "tentativa de golpe de Estado" → **Alexandre de Moraes**: "Está a serviço de um grupo político que tentou dar um golpe no país." (0,74)
- Ilustração: duas lupas lado a lado — a do `LIKE` procurando letras soltas (vazia, cinza), a semântica encontrando um balão de fala (azul, iluminada).

### PARTE 1 DE 5 — O QUE É UM EMBEDDING

**Slide 4 — Um embedding é um endereço no mapa do significado**
- Conteúdo: o modelo transforma cada frase em **384 números** — as "coordenadas" dela. Frases com sentido parecido ficam **perto**, mesmo sem palavras em comum.
- Ilustração: 🧭 um GPS/mapa com alfinetes; os alfinetes "medo", "pânico" e "pavor" juntos num bairro; "futebol" e "chocolate" num bairro distante.
- 🗣️ Analogia: o modelo é um GPS de significado. Um mapa comum tem 2 eixos (latitude, longitude); este tem 384.

**Slide 5 — Parecido de verdade: os números provam**
- Conteúdo (similaridade de 0 a 1 com a busca "coragem para enfrentar o pânico"):
  - pânico → **0,84**
  - medo → **0,70**
  - computador → **0,04**
- Ilustração: três barras horizontais (a de "pânico" cheia e azul-escura, "computador" quase vazia) — ou três "impressões digitais" coloridas, duas parecidas e uma diferente.
- 🗣️ Similaridade de cosseno: 1 = mesma direção, 0 = sem relação.

**Slide 6 — O modelo entende vários idiomas**
- Conteúdo: pergunta em inglês ou espanhol, resposta em português:
  - "we will never give up" → **Churchill** (0,52)
  - "tenemos que derribar el muro" → **Reagan**: "Senhor Gorbachev, derrube este muro!" (0,63)
- Ilustração: bandeiras/balões em três idiomas apontando para o mesmo alfinete no mapa.

**Slide 6b — Frases polêmicas: o modelo acha pelo sentido… mas não sabe história**
- Conteúdo:
  - "não é minha responsabilidade contar os mortos" → **Bolsonaro**: "Não sou coveiro, tá?" (0,51)
  - "você perdeu a eleição, pare de incomodar" → **Barroso**: "Perdeu, mané, não amola." (0,66)
  - "o julgamento vai ficar para a história" → **Fachin**: "O país olha para esta Corte…" (0,73)
  - Limite: "tomar vacina tem efeitos estranhos" **não** encontra "Se você virar um jacaré, é problema seu." — a frase não fala de vacina; o contexto histórico está fora do texto.
- Ilustração: lupa encontrando três balões de fala; num quarto balão, um jacaré com um ponto de interrogação (o modelo não conhece o contexto).
- 🗣️ Tom neutro: as frases estão na base porque são públicas, documentadas e com fonte — não para tomar partido. A lição técnica é: o embedding representa **o texto**, não o que você sabe sobre ele. Para buscar pelo contexto, guarde o contexto junto (coluna `Contexto`) e vetorize os dois.

**Slide 7 — 🎬 DEMO: o mapa das embeddings em 3D**
- Conteúdo: app "Quem disse?", página **Mapa das embeddings** — as frases da aula + 42 palavras de 7 **campos semânticos** (medo e coragem, guerra e resistência, democracia e povo, pátria e união, justiça e corrupção, progresso e trabalho, e **fora do tema**: futebol, chocolate, gato…).
- Ilustração: nuvem de pontos 3D com três aglomerados coloridos e um grupo cinza afastado; um quadrado preto "SUA BUSCA" ligado por linhas tracejadas aos vizinhos.
- 🗣️ Mostre: palavras do mesmo campo formam nuvens; "fora do tema" fica longe de tudo (é o grupo de controle). Palavras do mesmo campo têm similaridade média 0,51–0,59 entre si contra 0,37–0,43 com as de fora.

**Slide 8 — O gráfico é uma sombra: a busca de verdade é nas 384 dimensões**
- Conteúdo: achatar 384 eixos em 3 perde informação — o desenho guarda só **~20%** da variação. Por isso **nunca** se busca no desenho.
- Ilustração: 🔦 lanterna projetando a sombra de um objeto 3D complexo numa parede — a sombra é reconhecível, mas perde detalhes.
- 🗣️ PCA = sombra estável (o mapa não se mexe e a busca "cai" nele). t-SNE = reorganiza para manter vizinhos juntos.

**Slide 9 — Pegadinha: compare coisas do mesmo formato**
- Conteúdo: busca **"traficante"** no mapa.
  - Cosseno puro: a palavra *conquista* aparece em 1º (0,64) e a frase do Lula sobre traficantes fica em **19º**.
  - Descontando o formato: a frase do Lula vai para o **1º lugar** (0,52).
- Ilustração: duas balanças — na da esquerda, uma palavra solta "pesa" mais que uma frase inteira (errado, vermelho); na da direita, equilibradas por assunto (certo, azul).
- 🗣️ Palavra solta parece próxima de qualquer outra palavra solta só por ser palavra solta. Lição prática: faça a pergunta no mesmo formato do que está guardado (frase com frase).

**Slide 10 — Recapitulando a Parte 1**
- Embedding = 384 números = endereço no mapa do significado.
- Perto = parecido (cosseno). Funciona entre idiomas.
- O gráfico 3D é uma sombra; a busca real é nas 384 dimensões.

### PARTE 2 DE 5 — GUARDANDO NO SQL SERVER 2022

**Slide 11 — O SQL Server 2022 não tem tipo de vetor**
- Conteúdo: `DECLARE @v VECTOR(3)` → erro: *"Parameter or variable '@v' has an invalid data type."* · `VECTOR_DISTANCE` → *"is not a recognized built-in function name."*
- Ilustração: 📚 bibliotecário (azul) segurando uma caixa com etiqueta "VECTOR" e fazendo cara de dúvida.
- 🗣️ Tipo `VECTOR` e `VECTOR_DISTANCE` só existem no SQL Server 2025 e no Azure SQL.

**Slide 12 — A saída: 384 números × 4 bytes = 1.536 bytes num `VARBINARY`**
- Conteúdo: cada número é um *float32* (4 bytes). O vetor inteiro vira **exatamente 1.536 bytes** — e volta sem perder nada.
- Ilustração: 📦 uma fileira de 384 contas coloridas sendo compactadas numa caixa lacrada com a etiqueta "1.536 bytes".
- Código (3 linhas):
  ```sql
  CREATE TYPE rag.Embedding FROM VARBINARY(MAX);
  -- 384 floats x 4 bytes = 1.536 bytes
  CHECK (DATALENGTH(Vetor) = Dimensoes * 4)
  ```

**Slide 13 — Por que não JSON? Porque ocupa 11× mais**
- Conteúdo: o mesmo vetor → `VARBINARY` **1.536 bytes** · `NVARCHAR` com JSON **16.910 bytes** → **11×** maior, e ainda precisa ser "lido" (parse) a cada uso.
- Ilustração: duas pilhas lado a lado — uma caixinha azul pequena e uma torre alta de papel.

**Slide 14 — Três decisões de DBA no modelo de dados**
- Conteúdo:
  1. **Tabela separada** para embeddings: trocar de modelo não mexe na tabela de negócio.
  2. **Chave (FraseId, Modelo)**: vetores de modelos diferentes não são comparáveis.
  3. **CHECK de tamanho**: o banco recusa vetor com tamanho errado (governança).
- Ilustração: diagrama de 3 tabelas — `Politico` → `Frase` → `FraseEmbedding` — com um escudo sobre a terceira.
- 🗣️ No notebook 02, tentamos gravar um vetor de 100 números e o CHECK bloqueou.

**Slide 15 — Recapitulando a Parte 2**
- 2022 não tem `VECTOR` → guardamos bytes em `VARBINARY`.
- 1.536 bytes por frase; JSON seria 11× maior.
- O banco garante a qualidade (tabela separada, chave com o modelo, CHECK).

### PARTE 3 DE 5 — BUSCANDO

**Slide 16 — Busca semântica em 4 passos**
- Conteúdo: ① a pergunta vira vetor → ② compara com **todas** as frases → ③ ordena pela similaridade → ④ devolve as mais próximas.
- Ilustração: esteira de fábrica com 4 estações numeradas.
- 🗣️ Não existe `LIKE` no meio: a pergunta é comparada com todas as frases ("força bruta"). O `LIKE` do app é só para comparação.

**Slide 17 — No 2022, o bibliotecário guarda e a aplicação faz a conta**
- Conteúdo: dois caminhos, a mesma resposta:
  - **Aplicação (NumPy)**: carrega todos os vetores uma vez (48 KB) → **0,02 ms** por busca.
  - **Banco (T-SQL "na mão" com `GENERATE_SERIES`)**: abre os bytes número a número → **~450 ms** por busca.
- Ilustração: 📦 pilha de caixas lacradas; à esquerda alguém leva todas para casa e compara rapidinho; à direita o bibliotecário abre caixa por caixa, suando.
- 🗣️ No 2022 existe um dilema: rápido exige levar tudo para a aplicação; não levar nada é lento. E a força bruta cresce com a base: com 22 frases o T-SQL levava ~250 ms; com 32, ~450 ms.

**Slide 18 — Força bruta aguenta muito: 1 milhão de frases**
- Conteúdo: **1 milhão de vetores** = **1,43 GB** de memória → busca em **132 ms**.
- Ilustração: número gigante "1.000.000" com um cronômetro marcando 0,13 s.
- 🗣️ Até centenas de milhares de frases, força bruta em memória resolve. Acima disso: índice vetorial (FAISS, hnswlib, ou o do SQL Server 2025).

**Slide 19 — O "R" do RAG: buscar o contexto certo para o LLM**
- Conteúdo: RAG = **R**etrieval (buscar) + **A**ugmented (enriquecer o prompt) + **G**eneration (o LLM responde). O SQL Server + a busca semântica fazem o **R**.
- Ilustração: funil — pergunta do usuário entra, o banco devolve 3 frases, elas entram num prompt, e um robô/LLM responde "segundo Roosevelt…".
- Exemplo de prompt montado:
  > Responda usando APENAS as frases abaixo. Se não houver resposta, diga que não sabe.
  > – "A única coisa que devemos temer é o próprio medo." (Franklin D. Roosevelt, 1933)
  > Pergunta: Quem falou sobre não ter medo?

**Slide 20 — 🎬 DEMO: o app "Quem disse?"**
- Conteúdo: modo quiz (o autor fica escondido), palavra-chave × semântica lado a lado, cálculo em Python ou em T-SQL, e **cadastro de uma frase nova ao vivo** (gera o embedding e grava no SQL Server).
- Ilustração: tela de app com um campo de busca, três cartões de frases e um botão "Quem disse?".

**Slide 21 — Recapitulando a Parte 3**
- A busca compara a pergunta com todas as frases (força bruta).
- No 2022: rápido na aplicação, lento no banco.
- A busca semântica é o "R" do RAG.

### PARTE 4 DE 5 — E NO SQL SERVER 2025?

**Slide 22 — No 2025, o bibliotecário aprende a ler**
- Conteúdo: tipo nativo **`VECTOR(384)`** · função **`VECTOR_DISTANCE`** · o banco pode até pedir o vetor ao modelo (**`AI_GENERATE_EMBEDDINGS`**).
- Ilustração: 📚 bibliotecário (laranja) com óculos lendo as "impressões digitais" das caixas abertas.
- Código (4 linhas):
  ```sql
  SELECT TOP (5) Texto,
         VECTOR_DISTANCE('cosine', @pergunta, Vetor) AS distancia
  FROM rag.FraseVetor
  ORDER BY distancia;
  ```

**Slide 23 — A força bruta continua — mas dentro do banco**
- Conteúdo: `VECTOR_DISTANCE` é **sempre exata**: compara com todas as linhas. Diferença: roda **no banco, nativo e rápido**; nada vai para a aplicação; frase nova aparece na hora.
- Número: a Microsoft recomenda busca exata para até **~50 mil vetores**.
- Ilustração: mesma esteira do slide 16, agora dentro do prédio da biblioteca (laranja).

**Slide 24 — Índice vetorial: rápido, mas aproximado**
- Conteúdo: `CREATE VECTOR INDEX` (algoritmo **DiskANN**) vai direto à "vizinhança" sem olhar todas as linhas. Em troca, pode deixar escapar um vizinho.
- Ilustração: índice remissivo de um livro apontando direto para uma página.

**Slide 25 — ⚠️ A pegadinha: no 2025 on-premise, a tabela vira somente leitura**
- Conteúdo:
  - Com índice vetorial, **INSERT, UPDATE, DELETE e MERGE são bloqueados**: *Msg 42231 — "Data modification statement failed because table has a vector index on it."*
  - Para mudar dados: apagar o índice → alterar → **reconstruir tudo**.
  - Ainda é **preview**; exige ≥ **100 linhas** e chave primária `INT` única.
- Ilustração: 🔒 cadeado vermelho sobre uma tabela; ao lado, o botão "Cadastrar nova frase" do nosso app riscado.
- 🗣️ O "cadastrar frase ao vivo" do nosso app quebraria num SQL Server 2025 on-premise com índice vetorial.

**Slide 26 — No Azure SQL, a pegadinha já foi resolvida**
- Conteúdo: o **índice versão 3** (só no Azure SQL Database e no Fabric, por enquanto) aceita INSERT/UPDATE e **se atualiza sozinho**; filtros entram durante a busca; sintaxe `SELECT TOP (N) WITH APPROXIMATE`.
- Ilustração: nuvem verde-água com um cadeado aberto e uma frase nova entrando na tabela.

**Slide 27 — O quadro para levar para casa**
| | Onde calcula | Força bruta? | Frase nova ao vivo |
|---|---|---|---|
| 2022 — aplicação (nossa aula) | app (NumPy) | sim | ✅ após recarregar |
| 2022 — T-SQL caseiro | banco, "na mão" | sim | ✅ na hora (lento) |
| 2025 — `VECTOR_DISTANCE` | banco, nativo | sim | ✅ na hora |
| 2025 on-premise — índice (preview) | banco, aproximado | não | ❌ somente leitura |
| Azure SQL — índice v3 | banco, aproximado | não | ✅ na hora |
- Ilustração: tabela com as linhas pintadas nas cores fixas (azul, laranja, verde-água) e a célula ❌ em vermelho.

### PARTE 5 DE 5 — FECHAMENTO

**Slide 28 — A frase da aula**
> **No 2022, o SQL Server guarda e a aplicação pensa.**
> **No 2025, o SQL Server guarda e pensa.**
> **A gambiarra da aula é fazer o 2022 pensar.**
- Ilustração: dois bibliotecários lado a lado — o azul (2022) guardando caixas lacradas, o laranja (2025) lendo e comparando.

**Slide 29 — Para discutir**
1. Nosso app cadastra frases ao vivo. Num SQL Server 2025 on-premise, você usaria índice vetorial?
2. Um catálogo de 5 milhões de produtos que muda uma vez por noite: índice on-premise resolveria?
3. Por que comparar uma palavra solta com frases inteiras engana a busca?
4. Você colocaria um recurso em *preview* em produção?

**Slide 30 — Referências e material**
- Repositório da aula: `aulas/02-rag-sqlserver-2022` (notebooks 01–04 + app Streamlit).
- Microsoft Learn: *Vector search and vector indexes*, *VECTOR_DISTANCE*, *CREATE VECTOR INDEX*, *ALTER DATABASE SCOPED CONFIGURATION (ALLOW_STALE_VECTOR_INDEX)*, *Erros 41400–49999*.
- Redgate Simple Talk: *Vector search in SQL Server: VECTOR_DISTANCE, VECTOR_SEARCH, and index trade-offs*.
- *Recursos em preview mudam rápido — conferir a documentação antes de cada turma.*

---

## 3. Glossário (para o slide de apoio ou notas)

| Termo | Em uma frase |
|---|---|
| Embedding | lista de números que representa o significado de um texto |
| Dimensão | cada um dos 384 números do embedding |
| Similaridade de cosseno | quão "na mesma direção" dois vetores apontam (1 = igual, 0 = nada a ver) |
| Força bruta (kNN exato) | comparar a pergunta com todos os vetores |
| Índice vetorial (ANN) | atalho para achar vizinhos sem comparar com todos; aproximado |
| DiskANN | algoritmo de índice vetorial usado pelo SQL Server |
| `VARBINARY` | coluna de bytes crus; o banco guarda sem entender |
| `VECTOR(n)` | tipo nativo de vetor do SQL Server 2025 / Azure SQL |
| RAG | buscar contexto (R), enriquecer o prompt (A), gerar a resposta (G) |
| PCA / t-SNE | técnicas para achatar muitas dimensões em 2 ou 3 e desenhar |

---

## 4. Fatos verificados (não alterar os números)

- 31 frases no CSV, 23 políticos/ministros (32 no banco, com a frase do Lula cadastrada ao vivo pelo app); modelo `paraphrase-multilingual-MiniLM-L12-v2`; **384** dimensões; **1.536 bytes** por vetor.
- JSON em `NVARCHAR`: **16.910 bytes** para o mesmo vetor → **11×**.
- "coragem para enfrentar o pânico": pânico **0,841**; medo **0,696**; computador **0,035**; frase mais próxima: Roosevelt (0,569).
- `LIKE` com as 6 perguntas "com outras palavras": **0 resultados** em todas.
- Frases recentes (busca semântica, similaridade): "tentativa de golpe de Estado" → Moraes 0,741; "o julgamento vai ficar para a história" → Fachin 0,727; "corrupção e falta de ética" → Gilmar Mendes 0,679; "você perdeu a eleição, pare de incomodar" → Barroso 0,658; "não é minha responsabilidade contar os mortos" → Bolsonaro ("Não sou coveiro, tá?") 0,512; "tomar vacina tem efeitos estranhos" **não** encontra a frase do jacaré.
- Fontes das frases recentes: Estado de Minas/AFP (19/06/2021, frases de Bolsonaro sobre a pandemia), Correio Braziliense (20/04/2020, "Não sou coveiro"), CNN Brasil ("Perdeu, mané, não amola", nov/2022), Correio Braziliense (sessão do STF de 15/09/2026).
- "we will never give up" → Churchill (0,523). "tenemos que derribar el muro" → Reagan (0,628).
- Busca na aplicação: **0,02 ms** (48 KB de vetores); busca em T-SQL com `GENERATE_SERIES`: **~450 ms** com 32 frases (era ~250 ms com 22) — máquina do professor.
- 1 milhão de vetores: **1,43 GB** de RAM; busca em **~0,13 s** (132–136 ms, NumPy, força bruta).
- Mapa 3D (PCA descontando o formato): **~20%** da variação preservada.
- "traficante": cosseno puro → frase do Lula em **19º** (conquista 0,644 em 1º); descontando o formato → **1º** (0,516).
- SQL Server 2025: `VECTOR_DISTANCE` é sempre exata; Microsoft recomenda busca exata para < ~50.000 vetores.
- SQL Server 2025 on-premise: índice vetorial em **preview**; exige ≥ 100 linhas e PK clusterizada `INT`; **tabela somente leitura** (Msg 42231); `ALLOW_STALE_VECTOR_INDEX` indisponível no SQL Server 2025.
- Azure SQL Database / Fabric: índice **versão 3** com suporte completo a INSERT/UPDATE/DELETE/MERGE; sintaxe `TOP (N) WITH APPROXIMATE`; usar `TOP_N` num índice v3 gera Msg 42274.
