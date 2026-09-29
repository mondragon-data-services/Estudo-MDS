-- Aula: RAG com SQL Server 2022 sem tipo VECTOR (ele só chega no 2025)
-- Script equivalente ao notebook 01 (para rodar no SSMS ou sqlcmd)

-- Pode ser rodado quantas vezes quiser: tudo o que ele cria, ele apaga antes.
-- ATENÇÃO: como as tabelas são recriadas, os dados da aula somem. Rode o
-- notebook 02 depois para recarregar as frases e gerar os embeddings.

IF DB_ID('RagPoliticos') IS NULL
    CREATE DATABASE RagPoliticos;
GO
-- Nível 160 = SQL Server 2022. Necessário para o GENERATE_SERIES (rag.fn_VetorParaLinhas).
ALTER DATABASE RagPoliticos SET COMPATIBILITY_LEVEL = 160;
GO
USE RagPoliticos;
GO

-- Limpeza, na ordem inversa da criação: primeiro quem depende, depois quem é dependido.
DROP PROCEDURE IF EXISTS rag.usp_BuscaSemanticaTSQL;
DROP PROCEDURE IF EXISTS rag.usp_BuscaPalavraChave;
DROP VIEW      IF EXISTS rag.vw_Frases;
DROP FUNCTION  IF EXISTS rag.fn_VetorParaLinhas;
DROP TABLE     IF EXISTS rag.FraseEmbedding;   -- filha sai antes da mãe (FK)
DROP TABLE     IF EXISTS rag.Frase;
DROP TABLE     IF EXISTS rag.Politico;
DROP TABLE     IF EXISTS rag.FraseEmbeddingItem;  -- da versão 2017 da aula
DROP TYPE      IF EXISTS rag.Embedding;        -- só depois da tabela que o usava
DROP SCHEMA    IF EXISTS rag;                  -- o schema precisa estar vazio
GO

CREATE SCHEMA rag;
GO

-- Tipo de dado "apelido" (alias type): documenta a intenção da coluna.
-- Por baixo é VARBINARY(MAX): bytes crus de floats de 4 bytes.
CREATE TYPE rag.Embedding FROM VARBINARY(MAX) NULL;
GO

CREATE TABLE rag.Politico (
    PoliticoId INT IDENTITY(1,1) CONSTRAINT PK_Politico PRIMARY KEY,
    Nome       NVARCHAR(150) NOT NULL CONSTRAINT UQ_Politico_Nome UNIQUE,
    Pais       NVARCHAR(60)  NOT NULL,
    Cargo      NVARCHAR(150) NULL
);
GO

CREATE TABLE rag.Frase (
    FraseId        INT IDENTITY(1,1) CONSTRAINT PK_Frase PRIMARY KEY,
    PoliticoId     INT NOT NULL CONSTRAINT FK_Frase_Politico REFERENCES rag.Politico(PoliticoId),
    Texto          NVARCHAR(1000) NOT NULL,   -- texto em português (o que vamos vetorizar)
    TextoOriginal  NVARCHAR(1000) NULL,       -- idioma original da frase
    IdiomaOriginal CHAR(2)        NULL,
    Ano            SMALLINT       NULL,
    Contexto       NVARCHAR(300)  NULL,
    Fonte          NVARCHAR(400)  NULL
);
GO

-- Tabela separada para embeddings: permite ter mais de um modelo por frase
-- e re-vetorizar sem mexer na tabela de negócio.
CREATE TABLE rag.FraseEmbedding (
    FraseId    INT           NOT NULL CONSTRAINT FK_FraseEmb_Frase REFERENCES rag.Frase(FraseId),
    Modelo     NVARCHAR(200) NOT NULL,
    Dimensoes  SMALLINT      NOT NULL,
    Vetor      rag.Embedding NOT NULL,
    CriadoEm   DATETIME2(0)  NOT NULL CONSTRAINT DF_FraseEmb_CriadoEm DEFAULT SYSUTCDATETIME(),
    CONSTRAINT PK_FraseEmbedding PRIMARY KEY (FraseId, Modelo),
    -- Governança: garante que o tamanho em bytes bate com as dimensões (float32 = 4 bytes)
    CONSTRAINT CK_FraseEmb_Tamanho CHECK (DATALENGTH(Vetor) = Dimensoes * 4)
);
GO

-- Transforma um vetor VARBINARY (float32 little-endian) em linhas (Dim, Valor).
-- GENERATE_SERIES é novidade do SQL Server 2022: no 2017 seria preciso uma tabela
-- de números ou gravar o vetor "explodido" (uma linha por dimensão).
-- float32 (IEEE 754): 1 bit de sinal, 8 de expoente, 23 de mantissa.
CREATE OR ALTER FUNCTION rag.fn_VetorParaLinhas (@Vetor VARBINARY(MAX))
RETURNS TABLE
AS RETURN
SELECT CAST(s.value AS SMALLINT) AS Dim,
       CASE WHEN f.Expoente = 0 THEN 0.0E0      -- zero (e subnormais, desprezíveis aqui)
            ELSE (1 - 2 * f.Sinal) * (1 + f.Mantissa / 8388608.0E0) * POWER(2.0E0, f.Expoente - 127)
       END AS Valor
FROM GENERATE_SERIES(0, CAST(DATALENGTH(@Vetor) / 4 - 1 AS INT)) AS s
-- 4 bytes invertidos (little-endian) -> inteiro de 32 bits sem sinal
CROSS APPLY (SELECT CAST(SUBSTRING(@Vetor, s.value * 4 + 4, 1) + SUBSTRING(@Vetor, s.value * 4 + 3, 1)
                       + SUBSTRING(@Vetor, s.value * 4 + 2, 1) + SUBSTRING(@Vetor, s.value * 4 + 1, 1) AS BIGINT) AS Bits) AS b
-- Separa os campos com divisão inteira: 8388608 = 2^23 e 256 = 2^8
CROSS APPLY (SELECT b.Bits / 8388608 / 256    AS Sinal,
                    (b.Bits / 8388608) % 256 AS Expoente,
                    b.Bits % 8388608         AS Mantissa) AS f;
GO

CREATE OR ALTER VIEW rag.vw_Frases AS
SELECT f.FraseId, p.Nome AS Politico, p.Pais, p.Cargo,
       f.Texto, f.TextoOriginal, f.IdiomaOriginal, f.Ano, f.Contexto, f.Fonte
FROM rag.Frase f
JOIN rag.Politico p ON p.PoliticoId = f.PoliticoId;
GO

-- Busca por palavra-chave: o jeito "clássico". Ignora acentos e maiúsculas (CI_AI).
CREATE OR ALTER PROCEDURE rag.usp_BuscaPalavraChave
    @Termo NVARCHAR(200)
AS
BEGIN
    SET NOCOUNT ON;
    SELECT FraseId, Politico, Texto, Ano
    FROM rag.vw_Frases
    WHERE Texto COLLATE Latin1_General_CI_AI LIKE N'%' + @Termo + N'%'
       OR TextoOriginal COLLATE Latin1_General_CI_AI LIKE N'%' + @Termo + N'%';
END;
GO

-- BÔNUS: busca semântica em T-SQL puro no SQL Server 2022, sem tipo VECTOR.
-- O vetor da pergunta chega em VARBINARY, no mesmo formato dos vetores gravados.
-- Como os vetores são normalizados, cosseno = soma dos produtos (produto escalar).
CREATE OR ALTER PROCEDURE rag.usp_BuscaSemanticaTSQL
    @Vetor  VARBINARY(MAX),
    @Modelo NVARCHAR(200),
    @K      INT = 5
AS
BEGIN
    SET NOCOUNT ON;
    WITH consulta AS (
        SELECT Dim, Valor FROM rag.fn_VetorParaLinhas(@Vetor)
    )
    SELECT TOP (@K) v.FraseId, v.Politico, v.Texto,
           SUM(e.Valor * c.Valor) AS Similaridade
    FROM rag.FraseEmbedding fe
    CROSS APPLY rag.fn_VetorParaLinhas(fe.Vetor) AS e
    JOIN consulta c ON c.Dim = e.Dim
    JOIN rag.vw_Frases v ON v.FraseId = fe.FraseId
    WHERE fe.Modelo = @Modelo
    GROUP BY v.FraseId, v.Politico, v.Texto
    ORDER BY Similaridade DESC;
END;
GO
