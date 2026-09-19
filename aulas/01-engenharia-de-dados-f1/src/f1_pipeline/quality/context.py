"""Cola entre o pipeline e o Great Expectations (GX 1.x).

O vocabulário do GX 1.x, na ordem em que as peças se encaixam:

``DataContext``          o "projeto" de qualidade (fica na pasta ``gx/``)
``DataSource``           de onde o dado vem (aqui: DataFrames pandas em memória)
``DataAsset``            uma tabela dentro dessa fonte
``BatchDefinition``      qual recorte da tabela será validado (aqui: a tabela toda)
``ExpectationSuite``     o conjunto de regras que o dado precisa cumprir
``ValidationDefinition`` amarra "este lote" + "estas regras"
``Checkpoint``           executa a validação e dispara ações (ex.: gerar Data Docs)
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

import great_expectations as gx
from great_expectations.checkpoint import UpdateDataDocsAction
from great_expectations.data_context.types.base import ProgressBarsConfig

from f1_pipeline import config
from f1_pipeline.utils.io import ensure_dir, write_json
from f1_pipeline.utils.logging import get_logger

logger = get_logger(__name__)

DATASOURCE_NAME = "f1_pandas"
BATCH_DEFINITION_NAME = "lote_completo"


# ---------------------------------------------------------------------------
# Contexto
# ---------------------------------------------------------------------------


def get_context(project_root: Path | None = None) -> Any:
    """Abre (ou cria) o projeto GX em ``<raiz>/gx``.

    Usamos o modo ``file`` — e não ``ephemeral`` — porque queremos que suites,
    resultados e Data Docs fiquem persistidos entre execuções, exatamente como
    aconteceria em um ambiente de produção versionado.
    """
    root = Path(project_root or config.PROJECT_ROOT)
    ensure_dir(root)
    context = gx.get_context(mode="file", project_root_dir=str(root))
    # Sem barras de progresso: nos notebooks e nos logs elas só poluem a saída.
    context.variables.progress_bars = ProgressBarsConfig(
        globally=False, metric_calculations=False
    )
    logger.info("Contexto GX pronto em %s", root / "gx")
    return context


def _batch_definition(context: Any, asset_name: str) -> Any:
    """Devolve (criando se necessário) o BatchDefinition de uma tabela."""
    data_source = context.data_sources.add_or_update_pandas(DATASOURCE_NAME)
    try:
        asset = data_source.get_asset(asset_name)
    except LookupError:
        asset = data_source.add_dataframe_asset(name=asset_name)
    try:
        return asset.get_batch_definition(BATCH_DEFINITION_NAME)
    except KeyError:
        return asset.add_batch_definition_whole_dataframe(BATCH_DEFINITION_NAME)


# ---------------------------------------------------------------------------
# Resultado em formato amigável
# ---------------------------------------------------------------------------


@dataclass
class QualityCheckResult:
    """Resumo legível de uma validação — é o que gravamos e mostramos no app."""

    tabela: str
    suite: str
    sucesso: bool
    total_regras: int
    regras_ok: int
    regras_falhas: int
    linhas_avaliadas: int
    validado_em: str
    detalhes: list[dict[str, Any]] = field(default_factory=list)

    @property
    def taxa_sucesso(self) -> float:
        if self.total_regras == 0:
            return 0.0
        return 100.0 * self.regras_ok / self.total_regras

    def to_dict(self) -> dict[str, Any]:
        return {
            "tabela": self.tabela,
            "suite": self.suite,
            "sucesso": self.sucesso,
            "total_regras": self.total_regras,
            "regras_ok": self.regras_ok,
            "regras_falhas": self.regras_falhas,
            "taxa_sucesso": round(self.taxa_sucesso, 2),
            "linhas_avaliadas": self.linhas_avaliadas,
            "validado_em": self.validado_em,
            "detalhes": self.detalhes,
        }

    def failures(self) -> list[dict[str, Any]]:
        return [d for d in self.detalhes if not d["sucesso"]]

    def __repr__(self) -> str:  # pragma: no cover - conveniência no notebook
        status = "APROVADO" if self.sucesso else "REPROVADO"
        return (
            f"<QualityCheckResult {self.tabela}: {status} "
            f"({self.regras_ok}/{self.total_regras} regras, "
            f"{self.linhas_avaliadas} linhas)>"
        )


def _extract_details(validation_result: Any, n_rows: int) -> list[dict[str, Any]]:
    """Traduz o resultado bruto do GX para uma lista de dicionários simples."""
    detalhes: list[dict[str, Any]] = []
    for item in validation_result.results:
        payload = item.to_json_dict()
        cfg = payload.get("expectation_config", {}) or {}
        kwargs = cfg.get("kwargs", {}) or {}
        result = payload.get("result", {}) or {}
        alvo = kwargs.get("column") or kwargs.get("column_list") or "(tabela inteira)"
        if isinstance(alvo, list):
            alvo = ", ".join(str(c) for c in alvo)
        detalhes.append(
            {
                "regra": cfg.get("type", "?"),
                "coluna": alvo,
                "descricao": (cfg.get("meta") or {}).get("descricao", ""),
                "sucesso": bool(payload.get("success")),
                "linhas_avaliadas": int(result.get("element_count", n_rows) or n_rows),
                "linhas_inesperadas": int(result.get("unexpected_count", 0) or 0),
                "percentual_inesperado": round(
                    float(result.get("unexpected_percent", 0.0) or 0.0), 3
                ),
                "exemplos": [
                    str(v) for v in (result.get("partial_unexpected_list") or [])[:5]
                ],
                "parametros": {
                    k: v
                    for k, v in kwargs.items()
                    if k not in {"batch_id", "column", "column_list"}
                },
            }
        )
    return detalhes


# ---------------------------------------------------------------------------
# Execução
# ---------------------------------------------------------------------------


def validate_dataframe(
    df: pd.DataFrame,
    suite: Any,
    asset_name: str,
    *,
    context: Any | None = None,
    build_docs: bool = True,
    raise_on_failure: bool = False,
) -> QualityCheckResult:
    """Valida um DataFrame contra uma ExpectationSuite e devolve um resumo.

    Parameters
    ----------
    df:
        A tabela a validar (bronze, silver ou gold).
    suite:
        Suite construída em :mod:`f1_pipeline.quality.suites`.
    asset_name:
        Nome lógico da tabela dentro do GX (é o que aparece nos Data Docs).
    build_docs:
        Se ``True``, atualiza os Data Docs (o relatório HTML) ao final.
    raise_on_failure:
        Em produção normalmente é ``True``: se a qualidade falha, o pipeline
        para e o dado ruim não avança. Nos notebooks deixamos ``False`` para
        conseguir *mostrar* a falha em vez de só quebrar.
    """
    context = context or get_context()
    suite = context.suites.add_or_update(suite)
    batch_definition = _batch_definition(context, asset_name)

    validation_definition = context.validation_definitions.add_or_update(
        gx.ValidationDefinition(
            name=f"vd_{asset_name}", data=batch_definition, suite=suite
        )
    )
    actions = [UpdateDataDocsAction(name="atualiza_data_docs")] if build_docs else []
    checkpoint = context.checkpoints.add_or_update(
        gx.Checkpoint(
            name=f"cp_{asset_name}",
            validation_definitions=[validation_definition],
            actions=actions,
            result_format="SUMMARY",
        )
    )

    logger.info(
        "Validando '%s' (%d linhas) com a suite '%s'", asset_name, len(df), suite.name
    )
    checkpoint_result = checkpoint.run(batch_parameters={"dataframe": df})
    validation_result = next(iter(checkpoint_result.run_results.values()))

    detalhes = _extract_details(validation_result, len(df))
    resultado = QualityCheckResult(
        tabela=asset_name,
        suite=suite.name,
        sucesso=bool(validation_result.success),
        total_regras=len(detalhes),
        regras_ok=sum(1 for d in detalhes if d["sucesso"]),
        regras_falhas=sum(1 for d in detalhes if not d["sucesso"]),
        linhas_avaliadas=len(df),
        validado_em=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        detalhes=detalhes,
    )

    registrar = logger.info if resultado.sucesso else logger.error
    registrar(
        "%s | %s: %d/%d regras aprovadas",
        "APROVADO" if resultado.sucesso else "REPROVADO",
        asset_name,
        resultado.regras_ok,
        resultado.total_regras,
    )
    if raise_on_failure and not resultado.sucesso:
        quebras = ", ".join(
            "{regra}({coluna})".format(**d) for d in resultado.failures()
        )
        raise ValueError(f"Qualidade reprovada em '{asset_name}': {quebras}")
    return resultado


# ---------------------------------------------------------------------------
# Relatórios
# ---------------------------------------------------------------------------


def results_to_dataframe(resultados: list[QualityCheckResult]) -> pd.DataFrame:
    """Visão consolidada: uma linha por tabela validada."""
    return pd.DataFrame(
        [
            {
                "tabela": r.tabela,
                "regras": r.total_regras,
                "aprovadas": r.regras_ok,
                "reprovadas": r.regras_falhas,
                "taxa_sucesso_%": round(r.taxa_sucesso, 1),
                "linhas": r.linhas_avaliadas,
                "status": "APROVADO" if r.sucesso else "REPROVADO",
            }
            for r in resultados
        ]
    )


def details_to_dataframe(resultados: list[QualityCheckResult]) -> pd.DataFrame:
    """Visão detalhada: uma linha por regra executada."""
    linhas = [
        {"tabela": r.tabela, **detalhe} for r in resultados for detalhe in r.detalhes
    ]
    return pd.DataFrame(linhas)


def save_quality_report(
    resultados: list[QualityCheckResult],
    path: Path | None = None,
    *,
    etapa: str = "pipeline",
) -> Path:
    """Grava o relatório consolidado em JSON (consumido pelo app Streamlit)."""
    path = Path(path or config.REPORTS_DIR / "quality_report.json")
    payload = {
        "etapa": etapa,
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sucesso_geral": all(r.sucesso for r in resultados),
        "tabelas_validadas": len(resultados),
        "regras_executadas": sum(r.total_regras for r in resultados),
        "regras_reprovadas": sum(r.regras_falhas for r in resultados),
        "resultados": [r.to_dict() for r in resultados],
    }
    write_json(payload, path)
    logger.info("Relatório de qualidade salvo em %s", path)
    return path


def publish_data_docs(
    context: Any | None = None, destino: Path | None = None
) -> Path | None:
    """Copia os Data Docs para ``docs/data_docs`` — pasta versionável no GitHub.

    O GX gera o HTML em ``gx/uncommitted/``, que por convenção não vai para o
    repositório. Como queremos que os alunos abram o relatório direto do
    GitHub Pages, copiamos o site gerado para ``docs/``.
    """
    context = context or get_context()
    context.build_data_docs()
    origem = config.GX_ROOT / "uncommitted" / "data_docs" / "local_site"
    if not origem.exists():
        logger.warning("Data Docs não encontrados em %s", origem)
        return None
    destino = Path(destino or config.DATA_DOCS_DIR)
    if destino.exists():
        shutil.rmtree(destino, ignore_errors=True)
    shutil.copytree(origem, destino)
    # Mantém a pasta rastreada pelo Git mesmo com o conteúdo ignorado.
    (destino / ".gitkeep").touch()
    logger.info("Data Docs publicados em %s", destino / "index.html")
    return destino / "index.html"
