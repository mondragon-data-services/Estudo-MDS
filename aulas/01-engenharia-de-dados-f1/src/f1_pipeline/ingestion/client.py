"""Cliente HTTP para a API pública de Fórmula 1 (Jolpica / Ergast).

Conceitos de engenharia de dados demonstrados aqui:

1. **Rate limiting** — respeitamos o limite público (~4 req/s) espaçando as
   chamadas. Ingestão educada é ingestão que não é bloqueada.
2. **Retry com backoff exponencial** — falha de rede é normal, não é exceção.
3. **Paginação** — a API devolve no máximo 100 registros por página; o cliente
   percorre todas as páginas automaticamente.
4. **Rastreabilidade** — cada página vem acompanhada da URL, do horário e do
   tempo de resposta, para que a camada RAW seja auditável.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Iterator

import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from f1_pipeline import config
from f1_pipeline.utils.io import utc_now_iso
from f1_pipeline.utils.logging import get_logger

logger = get_logger(__name__)


class ApiError(RuntimeError):
    """Erro considerado recuperável (429, 5xx, timeout) — vale a pena tentar de novo."""


@dataclass
class ApiPage:
    """Uma página de resposta da API, com seus metadados de coleta."""

    payload: dict[str, Any]
    url: str
    page_number: int
    fetched_at: str
    elapsed_ms: int
    limit: int
    offset: int

    @property
    def mrdata(self) -> dict[str, Any]:
        return self.payload.get("MRData", {})

    @property
    def total(self) -> int:
        """Total de registros disponíveis no endpoint (não só nesta página)."""
        return int(self.mrdata.get("total", 0))

    def records(self, table_key: str, records_key: str) -> list[dict[str, Any]]:
        return self.mrdata.get(table_key, {}).get(records_key, [])

    def as_metadata(self) -> dict[str, Any]:
        return {
            "pagina": self.page_number,
            "url": self.url,
            "coletado_em": self.fetched_at,
            "tempo_resposta_ms": self.elapsed_ms,
            "limit": self.limit,
            "offset": self.offset,
            "total_disponivel": self.total,
        }


@dataclass
class ErgastClient:
    """Cliente com rate limit, retry e paginação para a API da F1."""

    base_url: str = config.API_BASE_URL
    page_size: int = config.API_PAGE_SIZE
    min_interval: float = config.API_MIN_INTERVAL_SECONDS
    timeout: float = config.API_TIMEOUT_SECONDS
    max_retries: int = config.API_MAX_RETRIES
    user_agent: str = config.API_USER_AGENT
    session: requests.Session = field(default_factory=requests.Session, repr=False)

    _last_request_at: float = field(default=0.0, init=False, repr=False)
    request_count: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        self.session.headers.update({"User-Agent": self.user_agent})

    # -- controle de vazão ------------------------------------------------

    def _throttle(self) -> None:
        """Garante um intervalo mínimo entre duas requisições."""
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_request_at = time.monotonic()

    # -- requisição unitária ----------------------------------------------

    def fetch_page(self, path: str, *, limit: int, offset: int) -> ApiPage:
        """Busca UMA página. O decorator de retry fica na função interna."""

        @retry(
            retry=retry_if_exception_type((ApiError, requests.RequestException)),
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=30),
            reraise=True,
        )
        def _do_request() -> ApiPage:
            self._throttle()
            url = f"{self.base_url}/{path.strip('/')}.json"
            params = {"limit": limit, "offset": offset}
            started = time.monotonic()
            response = self.session.get(url, params=params, timeout=self.timeout)
            elapsed_ms = int((time.monotonic() - started) * 1000)
            self.request_count += 1

            if response.status_code == 429:
                retry_after = float(response.headers.get("Retry-After", 5))
                logger.warning(
                    "429 Too Many Requests — aguardando %.1fs antes de tentar de novo",
                    retry_after,
                )
                time.sleep(retry_after)
                raise ApiError("rate limit atingido")
            if response.status_code >= 500:
                raise ApiError(f"erro do servidor: HTTP {response.status_code}")
            response.raise_for_status()

            return ApiPage(
                payload=response.json(),
                url=response.url,
                page_number=offset // max(limit, 1),
                fetched_at=utc_now_iso(),
                elapsed_ms=elapsed_ms,
                limit=limit,
                offset=offset,
            )

        return _do_request()

    # -- paginação ---------------------------------------------------------

    def iter_pages(self, path: str, *, max_pages: int | None = None) -> Iterator[ApiPage]:
        """Itera por TODAS as páginas de um endpoint.

        A API informa em ``MRData.total`` quantos registros existem no total;
        usamos isso para saber quando parar.
        """
        offset = 0
        page_index = 0
        while True:
            page = self.fetch_page(path, limit=self.page_size, offset=offset)
            logger.info(
                "GET %s | offset=%d | total=%d | %dms",
                path,
                offset,
                page.total,
                page.elapsed_ms,
            )
            yield page

            page_index += 1
            offset += self.page_size
            if offset >= page.total:
                break
            if max_pages is not None and page_index >= max_pages:
                logger.warning("Interrompido em max_pages=%s para %s", max_pages, path)
                break

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "ErgastClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
