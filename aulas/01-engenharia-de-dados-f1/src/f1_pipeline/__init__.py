"""Pipeline didático de Engenharia de Dados usando dados públicos da Fórmula 1.

Três fases, três subpacotes:

* :mod:`f1_pipeline.ingestion`  -> extrai da API pública e grava a camada RAW
* :mod:`f1_pipeline.quality`    -> valida a fonte e a ingestão com Great Expectations
* :mod:`f1_pipeline.processing` -> transforma RAW -> BRONZE -> SILVER -> GOLD
"""

__version__ = "1.0.0"

from f1_pipeline import config  # noqa: F401  (reexportado por conveniência)

__all__ = ["config", "__version__"]
