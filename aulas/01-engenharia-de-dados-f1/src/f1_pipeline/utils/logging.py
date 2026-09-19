"""Logging padronizado.

Em um projeto de dados o log é a principal evidência do que aconteceu em uma
execução. Padronizamos o formato para que notebooks, scripts e o app mostrem
mensagens iguais.
"""

from __future__ import annotations

import logging
import sys

_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)-28s | %(message)s"
_DATEFMT = "%H:%M:%S"


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Devolve um logger configurado (idempotente: não duplica handlers)."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(stream=sys.stdout)
        handler.setFormatter(logging.Formatter(_FORMAT, datefmt=_DATEFMT))
        logger.addHandler(handler)
        logger.propagate = False
    logger.setLevel(level)
    return logger
