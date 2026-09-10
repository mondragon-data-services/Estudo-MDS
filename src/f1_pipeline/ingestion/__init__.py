"""Fase 1 — Ingestão: da API pública até a camada RAW."""

from f1_pipeline.ingestion.client import ApiError, ApiPage, ErgastClient
from f1_pipeline.ingestion.endpoints import ENDPOINTS, Endpoint, get_endpoint
from f1_pipeline.ingestion.jobs import (
    ingest_all,
    ingest_endpoint,
    ingest_season,
    iter_raw_records,
    load_manifests,
    load_raw_pages,
    manifests_to_dataframe,
    partition_path,
    rodadas_da_temporada,
)

__all__ = [
    "ApiError",
    "ApiPage",
    "ErgastClient",
    "ENDPOINTS",
    "Endpoint",
    "get_endpoint",
    "ingest_all",
    "ingest_endpoint",
    "ingest_season",
    "iter_raw_records",
    "load_manifests",
    "load_raw_pages",
    "manifests_to_dataframe",
    "partition_path",
    "rodadas_da_temporada",
]
