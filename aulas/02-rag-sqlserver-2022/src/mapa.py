"""
Matemática do "mapa das embeddings": achatar 384 dimensões em 3 para enxergar.

Ninguém enxerga 384 eixos. Para desenhar, projetamos os vetores em 3 dimensões,
como a sombra de um objeto na parede: a sombra perde detalhe, mas o que está
perto no objeto tende a continuar perto na sombra.

A busca de verdade continua acontecendo nas 384 dimensões; o mapa é só a foto.
"""
import numpy as np


def pca_3d(matriz: np.ndarray, grupos=None) -> tuple[np.ndarray, np.ndarray, dict, float]:
    """PCA "na mão" com NumPy (SVD): as 3 direções em que os pontos mais variam.

    ``grupos`` (opcional) desconta a diferença de FORMATO entre tipos de texto.
    Frases inteiras e palavras soltas ocupam regiões diferentes do espaço só por
    serem frases ou palavras; sem o desconto, o eixo principal do mapa vira
    "frase x palavra" em vez de "assunto". Centralizar cada grupo na sua própria
    média remove esse deslocamento e deixa os eixos para o significado.

    Devolve (coordenadas 3D, componentes, médias por grupo, fração da variação preservada).
    Componentes e médias servem para projetar pontos novos no MESMO mapa.
    """
    grupos = np.zeros(len(matriz), dtype=int) if grupos is None else np.asarray(grupos)
    medias = {g: matriz[grupos == g].mean(axis=0) for g in np.unique(grupos)}
    centrada = matriz - np.vstack([medias[g] for g in grupos])
    _, s, vt = np.linalg.svd(centrada, full_matrices=False)
    componentes = vt[:3]
    variancia = s ** 2
    preservada = float(variancia[:3].sum() / variancia.sum())
    return centrada @ componentes.T, componentes, medias, preservada


def projetar(vetores: np.ndarray, componentes: np.ndarray, media: np.ndarray) -> np.ndarray:
    """Leva vetores novos (ex.: a pergunta) para o mapa já calculado, sem redesenhá-lo."""
    return (np.atleast_2d(vetores) - media) @ componentes.T


def tsne_3d(matriz: np.ndarray, semente: int = 42) -> np.ndarray:
    """t-SNE: não preserva distâncias grandes, mas agrupa muito bem os vizinhos."""
    from sklearn.manifold import TSNE

    perplexidade = max(2, min(12, len(matriz) // 4))
    return TSNE(n_components=3, perplexity=perplexidade, init="pca",
                learning_rate="auto", random_state=semente).fit_transform(matriz)


def similaridades(consulta: np.ndarray, matriz: np.ndarray) -> np.ndarray:
    """Cosseno entre a consulta e cada linha. Vetores normalizados: é o produto escalar."""
    consulta = consulta / np.linalg.norm(consulta)
    return matriz @ consulta


def tipo_do_texto(texto: str) -> str:
    """Formato de um texto novo: até 2 palavras conta como "Palavra"; mais que isso, "Frase"."""
    return "Palavra" if len(texto.split()) <= 2 else "Frase"


def similaridades_sem_formato(consulta: np.ndarray, matriz: np.ndarray, grupos, grupo_consulta: str) -> np.ndarray:
    """Cosseno descontando o formato: compara "assunto com assunto".

    Palavras soltas são parecidas entre si só por serem palavras soltas: sem desconto,
    "traficante" fica mais perto de "conquista" (0,64) do que de uma frase sobre
    traficantes (0,44). Subtraindo de cada vetor a média do seu tipo (frase ou
    palavra) e normalizando de novo, sobra o que diferencia um texto dos outros do
    mesmo tipo — o sentido. É o mesmo desconto que o PCA usa para desenhar.
    """
    grupos = np.asarray(grupos)
    medias = {g: matriz[grupos == g].mean(axis=0) for g in np.unique(grupos)}
    centrada = matriz - np.vstack([medias[g] for g in grupos])
    centrada /= np.linalg.norm(centrada, axis=1, keepdims=True)
    q = consulta - medias.get(grupo_consulta, next(iter(medias.values())))
    return centrada @ (q / np.linalg.norm(q))


def vizinhos_preservados(sim_384: np.ndarray, coords: np.ndarray, ponto: np.ndarray, k: int) -> int:
    """Dos k vizinhos de verdade (384 dimensões), quantos também são os k mais próximos no mapa 3D?"""
    reais = set(np.argsort(-sim_384)[:k])
    no_mapa = set(np.argsort(np.linalg.norm(coords - ponto, axis=1))[:k])
    return len(reais & no_mapa)
