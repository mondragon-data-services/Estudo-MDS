-- Aula: RAG com SQL Server 2017 sem tipo VECTOR
-- Script equivalente ao notebook 01 (para rodar no SSMS ou sqlcmd)

IF DB_ID('RagPoliticos') IS NULL
    CREATE DATABASE RagPoliticos;
GO
USE RagPoliticos;
GO

IF SCHEMA_ID('rag') IS NULL
    EXEC('CREATE SCHEMA rag');
GO

-- Tipo de dado "apelido" (alias type): documenta a intenção da coluna.
-- Por baixo é VARBINARY(MAX): bytes crus de floats de 4 bytes.
IF TYPE_ID('rag.Embedding') IS NULL
    CREATE TYPE rag.Embedding FROM VARBINARY(MAX) NULL;
GO

IF OBJECT_ID('rag.Politico') IS NULL
CREATE TABLE rag.Politico (
    PoliticoId INT IDENTITY(1,1) CONSTRAINT PK_Politico PRIMARY KEY,
    Nome       NVARCHAR(150) NOT NULL CONSTRAINT UQ_Politico_Nome UNIQUE,
    Pais       NVARCHAR(60)  NOT NULL,
    Cargo      NVARCHAR(150) NULL
);
GO

IF OBJECT_ID('rag.Frase') IS NULL
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
IF OBJECT_ID('rag.FraseEmbedding') IS NULL
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

-- BÔNUS: o mesmo vetor "explodido" em linhas (uma linha por dimensão).
-- Serve para provar que dá para calcular o cosseno em T-SQL puro no 2017.
IF OBJECT_ID('rag.FraseEmbeddingItem') IS NULL
CREATE TABLE rag.FraseEmbeddingItem (
    FraseId INT           NOT NULL,
    Modelo  NVARCHAR(200) NOT NULL,
    Dim     SMALLINT      NOT NULL,
    Valor   REAL          NOT NULL,
    CONSTRAINT PK_FraseEmbeddingItem PRIMARY KEY (Modelo, Dim, FraseId)
);
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

-- BÔNUS: busca semântica em T-SQL puro (SQL Server 2016+), sem tipo VECTOR.
-- O vetor da pergunta chega como JSON; OPENJSON o transforma em linhas (Dim, Valor).
-- Como os vetores são normalizados, cosseno = soma dos produtos (produto escalar).
CREATE OR ALTER PROCEDURE rag.usp_BuscaSemanticaTSQL
    @VetorJson NVARCHAR(MAX),
    @Modelo    NVARCHAR(200),
    @K         INT = 5
AS
BEGIN
    SET NOCOUNT ON;
    WITH consulta AS (
        SELECT CAST([key] AS SMALLINT) AS Dim, CAST([value] AS REAL) AS Valor
        FROM OPENJSON(@VetorJson)
    )
    SELECT TOP (@K) v.FraseId, v.Politico, v.Texto,
           SUM(CAST(e.Valor AS FLOAT) * c.Valor) AS Similaridade
    FROM rag.FraseEmbeddingItem e
    JOIN consulta c ON c.Dim = e.Dim
    JOIN rag.vw_Frases v ON v.FraseId = e.FraseId
    WHERE e.Modelo = @Modelo
    GROUP BY v.FraseId, v.Politico, v.Texto
    ORDER BY Similaridade DESC;
END;
GO
