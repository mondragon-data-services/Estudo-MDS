"""Orquestrador do pipeline completo (o que um Airflow/Dagster chamaria de DAG).

Uso::

    python scripts/run_pipeline.py                     # tudo, temporadas padrão
    python scripts/run_pipeline.py --seasons 2023-2024
    python scripts/run_pipeline.py --skip-ingest       # reprocessa a partir do RAW
    python scripts/run_pipeline.py --parar-se-reprovar # qualidade bloqueia o pipeline

A sequência é sempre a mesma:

    ingestão -> bronze -> [qualidade] -> silver -> [qualidade] -> gold -> [qualidade]

Repare que a validação não é uma etapa isolada no fim: ela é um **portão**
entre camadas. Dado ruim não deveria chegar ao analista.
"""

from __future__ import annotations

import argparse
import sys
import time

from f1_pipeline import config
from f1_pipeline.ingestion import ingest_all
from f1_pipeline.processing.bronze import build_bronze
from f1_pipeline.processing.gold import build_gold
from f1_pipeline.processing.silver import build_silver
from f1_pipeline.quality import context as gx_context
from f1_pipeline.quality import suites as gx_suites
from f1_pipeline.utils.logging import get_logger

logger = get_logger("f1_pipeline.cli")


def _parse_seasons(texto: str) -> tuple[int, ...]:
    if "-" in texto and "," not in texto:
        inicio, fim = (int(p) for p in texto.split("-", 1))
        return tuple(range(inicio, fim + 1))
    return tuple(int(p) for p in texto.split(","))


def _validar(camada: str, tabelas: dict, registro_de_suites: dict, gx_ctx, parar: bool):
    resultados = []
    for nome, fabrica_suite in registro_de_suites.items():
        if nome not in tabelas:
            continue
        resultados.append(
            gx_context.validate_dataframe(
                tabelas[nome],
                fabrica_suite(),
                asset_name=f"{camada}_{nome}",
                context=gx_ctx,
                build_docs=False,
                raise_on_failure=parar,
            )
        )
    return resultados


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Pipeline de dados da Fórmula 1: ingestão, processamento e marts analíticos.",
    )
    parser.add_argument(
        "--seasons",
        default=",".join(str(s) for s in config.SEASONS),
        help="Temporadas: '2023,2024' ou '2021-2024'. Padrão: %(default)s",
    )
    parser.add_argument("--skip-ingest", action="store_true", help="Reaproveita o RAW já baixado.")
    parser.add_argument("--skip-quality", action="store_true", help="Não roda o Great Expectations.")
    parser.add_argument(
        "--no-overwrite",
        action="store_true",
        help="Na ingestão, pula partições que já existem (carga incremental).",
    )
    parser.add_argument(
        "--parar-se-reprovar",
        action="store_true",
        help="Interrompe o pipeline se alguma expectativa falhar (comportamento de produção).",
    )
    args = parser.parse_args(argv)

    temporadas = _parse_seasons(args.seasons)
    inicio = time.monotonic()
    logger.info("=" * 78)
    logger.info("PIPELINE F1 | temporadas: %s", list(temporadas))
    logger.info("=" * 78)

    # ---------------------------------------------------------------- FASE 1
    if args.skip_ingest:
        logger.info("[1/3] Ingestão pulada (--skip-ingest)")
    else:
        logger.info("[1/3] INGESTÃO: API pública -> data/raw")
        ingest_all(temporadas, overwrite=not args.no_overwrite)

    # ---------------------------------------------------------------- FASE 2
    logger.info("[2/3] PROCESSAMENTO: raw -> bronze -> silver -> gold")
    bronze = build_bronze(temporadas)

    gx_ctx = None if args.skip_quality else gx_context.get_context()
    resultados = []
    if not args.skip_quality:
        logger.info("      Portão de qualidade #1: contrato da fonte (bronze)")
        resultados += _validar(
            "bronze", bronze, gx_suites.BRONZE_SUITES, gx_ctx, args.parar_se_reprovar
        )

    silver = build_silver(bronze)
    if not args.skip_quality:
        logger.info("      Portão de qualidade #2: semântica do dado (silver)")
        resultados += _validar(
            "silver", silver, gx_suites.SILVER_SUITES, gx_ctx, args.parar_se_reprovar
        )

    gold = build_gold(silver)
    if not args.skip_quality:
        logger.info("      Portão de qualidade #3: reconciliação das agregações (gold)")
        resultados += _validar(
            "gold", gold, gx_suites.GOLD_SUITES, gx_ctx, args.parar_se_reprovar
        )
        gx_context.save_quality_report(resultados, etapa="pipeline_completo")
        gx_context.publish_data_docs(gx_ctx)

    # ---------------------------------------------------------------- FASE 3
    logger.info("[3/3] ANALYTICS: os marts estão prontos em data/gold")
    logger.info("      Suba o app com:  streamlit run app/streamlit_app.py")

    logger.info("-" * 78)
    if resultados:
        reprovadas = sum(r.regras_falhas for r in resultados)
        total = sum(r.total_regras for r in resultados)
        logger.info(
            "Qualidade: %d/%d regras aprovadas em %d tabelas",
            total - reprovadas,
            total,
            len(resultados),
        )
    logger.info(
        "Pipeline concluído em %.1fs | gold: %s",
        time.monotonic() - inicio,
        {nome: len(df) for nome, df in gold.items()},
    )
    return 0 if all(r.sucesso for r in resultados) else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
