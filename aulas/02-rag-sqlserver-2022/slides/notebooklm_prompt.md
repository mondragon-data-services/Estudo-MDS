# Slides da Aula 02 no NotebookLM

## Como usar

1. Crie um notebook novo no NotebookLM.
2. Adicione como fonte **apenas** o arquivo `notebooklm_fonte.md` (desta pasta).
   Uma fonte só evita que o NotebookLM misture conteúdo de outras aulas.
3. No painel **Estúdio**, escolha a geração de **apresentação de slides** e abra a opção de
   personalizar.
4. Cole o **Prompt completo** abaixo. Se o campo tiver limite de caracteres, use o
   **Prompt curto** — o documento-fonte já traz o roteiro detalhado.
5. Gere, revise os números contra a seção **"Fatos verificados"** da fonte e, se algum
   slide sair carregado, peça: *"Divida o slide N em dois, uma ideia em cada."*

---

## Prompt completo

```text
Crie uma apresentação de slides em PORTUGUÊS DO BRASIL para uma aula de 2 horas chamada
"Quem disse? Busca semântica com SQL Server 2022". Público: alunos de engenharia de dados
que sabem SQL básico e NÃO conhecem IA. Use SOMENTE o conteúdo da fonte; não invente
números, versões nem recursos. Todos os números devem ser exatamente os da seção
"Fatos verificados".

ESTRUTURA
- Siga o "Roteiro slide a slide" da fonte, na mesma ordem: abertura, 5 partes e fechamento.
- Mostre o progresso em cada slide ("Parte 2 de 5") e termine cada parte com um slide
  de recapitulação de até 3 itens.
- Slides marcados com 🎬 são demonstrações ao vivo: faça um slide simples, com um ícone
  de "play" e uma frase dizendo o que será mostrado.

ERGONOMIA COGNITIVA (obrigatório)
- Uma ideia por slide. O título é a conclusão do slide, escrito como uma afirmação curta
  (ex.: "O LIKE procura letras, não significados"), nunca só um tema.
- No máximo 3 itens por slide, cada um com até 12 palavras. Nada de parágrafos.
- Quando houver um número importante (11×, 1.536 bytes, 0,014 ms × 250 ms, 1 milhão),
  mostre-o em destaque, grande, com uma legenda curta.
- Código: no máximo 6 linhas, fonte monoespaçada grande, com a linha principal destacada.
- Destaque apenas UM elemento por slide (cor, seta ou círculo).
- Muito espaço em branco; layout consistente em todos os slides.

ILUSTRAÇÕES
- Todo slide de conteúdo tem uma ilustração que explica a ideia; use a descrição
  "Ilustração" de cada slide da fonte.
- Estilo: ilustração plana (flat), limpa, amigável, fundo claro, poucos elementos, sem
  fotos realistas e sem texto dentro das imagens (o texto fica no slide).
- Use as metáforas recorrentes sempre com o mesmo desenho: GPS de significado (mapa com
  alfinetes), caixa lacrada (vetor em VARBINARY), bibliotecário (o SQL Server), sombra
  na parede (gráfico 3D), cadeado (tabela somente leitura).

CORES COM SIGNIFICADO FIXO
- Azul #2a78d6 = SQL Server 2022 / nossa aula. Laranja #eb6834 = SQL Server 2025
  on-premise. Verde-água #1baf7a = Azure SQL. Vermelho #d03b3b = só alertas e
  limitações. Cinza #898781 = secundário. Fundo #f9f9f7, texto #0b0b0b.
- Nunca use a cor de uma plataforma para outra coisa.

TOM
- Didático, direto, com analogias do cotidiano; termos técnicos (embedding, VARBINARY,
  VECTOR_DISTANCE, RAG) sempre explicados na primeira vez em que aparecem.
- O slide 25 (tabela somente leitura no SQL Server 2025 on-premise) é o ponto alto:
  dê a ele destaque visual com o cadeado vermelho e mostre que o "cadastrar frase ao
  vivo" do nosso app quebraria.
- Feche com a frase: "No 2022, o SQL Server guarda e a aplicação pensa. No 2025, o SQL
  Server guarda e pensa."

NOTAS DO APRESENTADOR
- Coloque nas notas o conteúdo marcado com 🗣️ na fonte.
```

---

## Prompt curto (se houver limite de caracteres)

```text
Slides em português do Brasil, para alunos de dados sem conhecimento de IA. Siga o
"Roteiro slide a slide" da fonte na ordem, usando só os "Fatos verificados". Uma ideia por
slide, título-afirmação, no máximo 3 itens curtos, números grandes em destaque, código
com até 6 linhas. Ilustração flat em todo slide (sem texto na imagem), com as metáforas
fixas da fonte. Cores fixas: azul 2022, laranja 2025, verde-água Azure, vermelho só para
alertas. Recapitulação ao fim de cada parte. Notas do apresentador com os itens 🗣️.
```

---

## Pedidos de ajuste úteis depois da primeira versão

- "Refaça o slide N com menos texto: só o título, o número em destaque e a ilustração."
- "Use a mesma ilustração do bibliotecário nos slides 11, 17, 22 e 28, mudando só a cor."
- "Transforme o slide 27 numa tabela com as linhas coloridas pelas cores fixas."
- "Crie uma versão de 12 slides com só os pontos principais, para uma palestra de 30 minutos."
