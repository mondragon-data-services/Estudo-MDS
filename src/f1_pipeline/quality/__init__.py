"""Fase 1.5 — Qualidade de dados com Great Expectations.

A validação acontece em dois momentos do pipeline:

* **Na ingestão (bronze)** — a fonte mudou? veio registro faltando? o
  contrato da API continua o mesmo?
* **Depois do processamento (silver/gold)** — a transformação preservou a
  verdade do dado? as agregações batem com a fonte?
"""

from f1_pipeline.quality.context import (
    QualityCheckResult,
    details_to_dataframe,
    get_context,
    publish_data_docs,
    results_to_dataframe,
    save_quality_report,
    validate_dataframe,
)
from f1_pipeline.quality import suites

__all__ = [
    "QualityCheckResult",
    "details_to_dataframe",
    "get_context",
    "publish_data_docs",
    "results_to_dataframe",
    "save_quality_report",
    "validate_dataframe",
    "suites",
]
