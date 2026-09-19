"""
O coração da aula: como guardar e comparar embeddings SEM o tipo VECTOR.

Ideia: um embedding é só uma lista de floats. Cada float32 ocupa 4 bytes.
Então 384 floats viram exatamente 384 x 4 = 1536 bytes -> cabe num VARBINARY.
O SQL Server 2017 guarda os bytes; o Python (NumPy) faz a matemática.
"""
import numpy as np

DTYPE = np.dtype("<f4")  # float32 little-endian: formato fixo, independente da máquina


def vetor_para_bytes(vetor) -> bytes:
    """[0.12, -0.5, ...] -> b'\\x8f\\xc2\\xf5=...' (para gravar no VARBINARY)."""
    return np.asarray(vetor, dtype=DTYPE).tobytes()


def bytes_para_vetor(dados: bytes) -> np.ndarray:
    """b'...' lido do VARBINARY -> array NumPy de float32."""
    return np.frombuffer(dados, dtype=DTYPE)


def similaridade_cosseno(consulta: np.ndarray, matriz: np.ndarray) -> np.ndarray:
    """
    Cosseno entre a consulta (d,) e cada linha da matriz (n, d).
    1.0 = mesmo sentido, 0 = sem relação.
    Como gravamos os vetores JÁ normalizados (norma = 1),
    o cosseno vira um simples produto escalar: matriz @ consulta.
    """
    consulta = consulta / np.linalg.norm(consulta)
    return matriz @ consulta


class IndiceEmMemoria:
    """Carrega todos os embeddings do banco para a RAM e busca por força bruta."""

    def __init__(self, ids: list[int], matriz: np.ndarray):
        self.ids = np.asarray(ids)
        self.matriz = matriz.astype(DTYPE)

    @classmethod
    def do_banco(cls, conn, modelo: str) -> "IndiceEmMemoria":
        cur = conn.cursor()
        cur.execute(
            "SELECT FraseId, Vetor FROM rag.FraseEmbedding WHERE Modelo = ? ORDER BY FraseId",
            modelo,
        )
        linhas = cur.fetchall()
        if not linhas:
            raise RuntimeError("Nenhum embedding encontrado. Rode o notebook 02 primeiro.")
        ids = [l.FraseId for l in linhas]
        matriz = np.vstack([bytes_para_vetor(l.Vetor) for l in linhas])
        return cls(ids, matriz)

    def buscar(self, vetor_consulta: np.ndarray, k: int = 5) -> list[tuple[int, float]]:
        scores = similaridade_cosseno(vetor_consulta, self.matriz)
        top = np.argsort(-scores)[:k]
        return [(int(self.ids[i]), float(scores[i])) for i in top]
