"""Testa se todas as páginas do app carregam sem erro.

O Streamlit tem um framework de teste (``AppTest``) que executa o script da
página sem abrir navegador. É a forma barata de garantir que ninguém quebrou a
interface ao mexer no pipeline.

Estes testes são pulados automaticamente se a camada gold ainda não existir.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
APP = RAIZ / "app"
PAGINAS = [APP / "streamlit_app.py", *sorted((APP / "pages").glob("*.py"))]

sem_dados = not (RAIZ / "data" / "gold" / "agg_driver_season.parquet").exists()


@pytest.mark.skipif(sem_dados, reason="rode o pipeline antes: python scripts/run_pipeline.py")
@pytest.mark.parametrize("pagina", PAGINAS, ids=lambda p: p.name)
def test_pagina_carrega_sem_excecao(pagina: Path):
    app = AppTest.from_file(str(pagina), default_timeout=60).run()
    assert not app.exception, f"{pagina.name} levantou exceção: {app.exception}"
