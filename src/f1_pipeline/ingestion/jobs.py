"""Os *jobs* de ingestão: da API até a camada RAW.

Princípios que estes jobs demonstram:

**RAW é sagrado.** Gravamos o JSON exatamente como a API devolveu. Nenhuma
renomeação, nenhum filtro, nenhuma conversão. Se amanhã descobrirmos um bug na
transformação, o dado original ainda está aqui para reprocessar.

**Idempotência.** Rodar duas vezes o mesmo job produz o mesmo resultado. O
particionamento por temporada (``season=2024/``) permite reprocessar só o que
mudou.

**Rastreabilidade.** Cada partição tem um ``_manifest.json`` com a URL
consultada, o horário, o número de páginas, a contagem de registros e o hash
SHA-256 de cada arquivo. É a certidão de nascimento do dado.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from f1_pipeline import config
from f1_pipeline.ingestion.client import ErgastClient
from f1_pipeline.ingestion.endpoints import ENDPOINTS, Endpoint, get_endpoint
from f1_pipeline.utils.io import (
    ensure_dir,
    file_digest,
    read_json,
    utc_now_iso,
    write_json,
)
from f1_pipeline.utils.logging import get_logger

logger = get_logger(__name__)

MANIFEST_NAME = "_manifest.json"


def partition_path(endpoint_name: str, season: int, raw_dir: Path | None = None) -> Path:
    """Caminho da partição: ``data/raw/<endpoint>/season=<ano>/``.

    O padrão ``coluna=valor`` no nome da pasta é o *Hive partitioning*, lido
    nativamente por Spark, DuckDB, Athena e pelo próprio pandas/pyarrow.
    """
    raw_dir = Path(raw_dir or config.RAW_DIR)
    return raw_dir / endpoint_name / f"season={season}"


# ---------------------------------------------------------------------------
# Ingestão de um endpoint em uma temporada
# ---------------------------------------------------------------------------


def rodadas_da_temporada(
    season: int, client: ErgastClient | None = None, raw_dir: Path | None = None
) -> list[int]:
    """Descobre quais rodadas existem na temporada, lendo o RAW de ``races``.

    Se o calendário ainda não foi ingerido, ingere na hora. É a dependência
    natural entre dois jobs: para pedir "as paradas do GP 5" primeiro é
    preciso saber que existe um GP 5.
    """
    try:
        paginas = load_raw_pages("races", season, raw_dir)
    except FileNotFoundError:
        ingest_endpoint(get_endpoint("races"), season, client=client, raw_dir=raw_dir)
        paginas = load_raw_pages("races", season, raw_dir)

    rodadas = {
        int(race["round"])
        for pagina in paginas
        for race in pagina.get("MRData", {}).get("RaceTable", {}).get("Races", [])
    }
    return sorted(rodadas)


def _baixar_paginas(
    client: ErgastClient,
    url_path: str,
    destino: Path,
    endpoint: Endpoint,
    *,
    max_pages: int | None,
    prefixo: str = "",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int, int]:
    """Baixa e grava as páginas de UMA consulta. Devolve (arquivos, meta, n, total)."""
    arquivos: list[dict[str, Any]] = []
    paginas_meta: list[dict[str, Any]] = []
    total_registros = 0
    total_disponivel = 0

    for pagina, page in enumerate(client.iter_pages(url_path, max_pages=max_pages)):
        arquivo = destino / f"page_{pagina:03d}.json"
        # >>> Aqui está o coração da camada RAW: gravamos o payload cru. <<<
        write_json(page.payload, arquivo)

        registros = page.records(endpoint.table_key, endpoint.records_key)
        total_registros += len(registros)
        total_disponivel += page.total if pagina == 0 else 0
        paginas_meta.append(page.as_metadata())
        arquivos.append(
            {
                "arquivo": f"{prefixo}{arquivo.name}",
                "bytes": arquivo.stat().st_size,
                "blocos_no_json": len(registros),
                "sha256": file_digest(arquivo),
            }
        )
    return arquivos, paginas_meta, total_registros, total_disponivel


def ingest_endpoint(
    endpoint: Endpoint | str,
    season: int,
    *,
    client: ErgastClient | None = None,
    raw_dir: Path | None = None,
    overwrite: bool = True,
    max_pages: int | None = None,
) -> dict[str, Any]:
    """Baixa todas as páginas de um endpoint para uma temporada e grava o RAW.

    Returns
    -------
    dict
        O manifesto da partição (também gravado em ``_manifest.json``).
    """
    if isinstance(endpoint, str):
        endpoint = get_endpoint(endpoint)

    destino = partition_path(endpoint.name, season, raw_dir)
    manifesto_path = destino / MANIFEST_NAME

    if manifesto_path.exists() and not overwrite:
        logger.info(
            "Partição %s/season=%s já existe - pulando (overwrite=False)",
            endpoint.name,
            season,
        )
        return read_json(manifesto_path)

    fechar_no_fim = client is None
    client = client or ErgastClient()
    ensure_dir(destino)

    inicio = time.monotonic()
    arquivos: list[dict[str, Any]] = []
    paginas_meta: list[dict[str, Any]] = []
    total_registros = 0
    total_disponivel = 0

    try:
        if endpoint.por_rodada:
            # Fan-out: uma consulta por rodada, cada uma em sua subpartição.
            for rodada in rodadas_da_temporada(season, client, raw_dir):
                sub = ensure_dir(destino / f"round={rodada:02d}")
                a, m, n, t = _baixar_paginas(
                    client,
                    endpoint.url_path(season, rodada),
                    sub,
                    endpoint,
                    max_pages=max_pages,
                    prefixo=f"round={rodada:02d}/",
                )
                arquivos += a
                paginas_meta += m
                total_registros += n
                total_disponivel += t
        else:
            arquivos, paginas_meta, total_registros, total_disponivel = _baixar_paginas(
                client, endpoint.url_path(season), destino, endpoint, max_pages=max_pages
            )
    finally:
        if fechar_no_fim:
            client.close()

    manifesto = {
        "endpoint": endpoint.name,
        "descricao": endpoint.description,
        "temporada": season,
        "ingerido_em": utc_now_iso(),
        "duracao_segundos": round(time.monotonic() - inicio, 2),
        "arquivos_gravados": len(arquivos),
        "requisicoes_http": len(paginas_meta),
        "blocos_no_json": total_registros,
        "registros_informados_pela_api": total_disponivel,
        "por_rodada": endpoint.por_rodada,
        "base_url": config.API_BASE_URL,
        "arquivos": arquivos,
        "requisicoes": paginas_meta,
    }
    write_json(manifesto, manifesto_path)
    logger.info(
        "RAW gravado: %-22s season=%s | %d arquivo(s) | %d registro(s) | %.2fs",
        endpoint.name,
        season,
        manifesto["arquivos_gravados"],
        total_disponivel,
        manifesto["duracao_segundos"],
    )
    return manifesto


# ---------------------------------------------------------------------------
# Orquestração
# ---------------------------------------------------------------------------


def ingest_season(
    season: int,
    *,
    endpoints: Iterable[Endpoint] = ENDPOINTS,
    client: ErgastClient | None = None,
    raw_dir: Path | None = None,
    overwrite: bool = True,
) -> list[dict[str, Any]]:
    """Ingere todos os endpoints de uma temporada, reaproveitando a conexão."""
    fechar_no_fim = client is None
    client = client or ErgastClient()
    try:
        return [
            ingest_endpoint(
                endpoint,
                season,
                client=client,
                raw_dir=raw_dir,
                overwrite=overwrite,
            )
            for endpoint in endpoints
        ]
    finally:
        if fechar_no_fim:
            client.close()


def ingest_all(
    seasons: Iterable[int] | None = None,
    *,
    endpoints: Iterable[Endpoint] = ENDPOINTS,
    raw_dir: Path | None = None,
    overwrite: bool = True,
) -> pd.DataFrame:
    """Executa a ingestão completa e devolve o resumo como DataFrame."""
    seasons = tuple(seasons or config.SEASONS)
    endpoints = tuple(endpoints)
    logger.info(
        "Iniciando ingestão | temporadas=%s | endpoints=%s",
        list(seasons),
        [e.name for e in endpoints],
    )
    inicio = time.monotonic()
    manifestos: list[dict[str, Any]] = []
    with ErgastClient() as client:
        for season in seasons:
            manifestos.extend(
                ingest_season(
                    season,
                    endpoints=endpoints,
                    client=client,
                    raw_dir=raw_dir,
                    overwrite=overwrite,
                )
            )
        requisicoes = client.request_count

    resumo = manifests_to_dataframe(manifestos)
    logger.info(
        "Ingestão concluída em %.1fs | %d requisições | %d registros",
        time.monotonic() - inicio,
        requisicoes,
        int(resumo["registros"].sum()) if not resumo.empty else 0,
    )
    return resumo


# ---------------------------------------------------------------------------
# Leitura do que já foi ingerido
# ---------------------------------------------------------------------------


def manifests_to_dataframe(manifestos: list[dict[str, Any]]) -> pd.DataFrame:
    """Transforma manifestos em uma tabela de auditoria da ingestão."""
    return pd.DataFrame(
        [
            {
                "endpoint": m["endpoint"],
                "temporada": m["temporada"],
                "requisicoes": m["requisicoes_http"],
                "arquivos": m["arquivos_gravados"],
                "registros": m["registros_informados_pela_api"],
                "bytes": sum(a["bytes"] for a in m["arquivos"]),
                "duracao_s": m["duracao_segundos"],
                "ingerido_em": m["ingerido_em"],
            }
            for m in manifestos
        ]
    )


def load_manifests(raw_dir: Path | None = None) -> pd.DataFrame:
    """Lê todos os ``_manifest.json`` já gravados na camada RAW."""
    raw_dir = Path(raw_dir or config.RAW_DIR)
    manifestos = [read_json(p) for p in sorted(raw_dir.rglob(MANIFEST_NAME))]
    return manifests_to_dataframe(manifestos)


def load_raw_pages(
    endpoint_name: str, season: int, raw_dir: Path | None = None
) -> list[dict[str, Any]]:
    """Carrega os payloads JSON crus de uma partição, em ordem de página."""
    destino = partition_path(endpoint_name, season, raw_dir)
    if not destino.exists():
        raise FileNotFoundError(
            f"Partição não encontrada: {destino}. Rode a ingestão antes "
            f"(notebook 01) ou use `ingest_endpoint('{endpoint_name}', {season})`."
        )
    # `rglob` porque endpoints por rodada gravam em subpastas `round=NN/`.
    return [read_json(p) for p in sorted(destino.rglob("page_*.json"))]


def iter_raw_records(
    endpoint_name: str, seasons: Iterable[int] | None = None, raw_dir: Path | None = None
):
    """Itera pelos registros de um endpoint em várias temporadas.

    Abstrai a paginação: quem chama recebe apenas os registros, sem precisar
    saber em quantos arquivos eles foram gravados.
    """
    endpoint = get_endpoint(endpoint_name)
    for season in tuple(seasons or config.SEASONS):
        for payload in load_raw_pages(endpoint_name, season, raw_dir):
            mrdata = payload.get("MRData", {})
            registros = mrdata.get(endpoint.table_key, {}).get(endpoint.records_key, [])
            for registro in registros:
                yield season, registro
