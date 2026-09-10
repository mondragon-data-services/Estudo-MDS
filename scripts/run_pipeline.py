"""Ponto de entrada do pipeline sem precisar instalar o pacote.

    python scripts/run_pipeline.py --help

Se você instalou o projeto (``pip install -e .``), pode usar o comando
``f1-pipeline`` diretamente no terminal.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Permite rodar direto do clone do repositório, sem `pip install`.
RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from f1_pipeline.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
