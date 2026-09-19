"""Entrada e saída de arquivos.

Regras do projeto:

* JSON  -> camada RAW (o payload da API, sem alteração alguma)
* Parquet -> camadas BRONZE/SILVER/GOLD (tipado, comprimido e rápido de ler)

Se o `pyarrow` não estiver disponível caímos para CSV, para que o projeto
continue rodando em máquinas com instalação mínima.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

try:  # pragma: no cover - depende do ambiente
    import pyarrow  # noqa: F401

    PARQUET_AVAILABLE = True
except ImportError:  # pragma: no cover
    PARQUET_AVAILABLE = False

TABLE_SUFFIX = ".parquet" if PARQUET_AVAILABLE else ".csv"


def utc_now_iso() -> str:
    """Timestamp ISO-8601 em UTC — usado nos metadados de ingestão."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ensure_dir(path: Path) -> Path:
    """Cria o diretório (e os pais) se ainda não existir."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(payload: Any, path: Path, *, indent: int = 2) -> Path:
    ensure_dir(path.parent)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=indent), encoding="utf-8"
    )
    return path


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_table(df: pd.DataFrame, path: Path) -> Path:
    """Grava um DataFrame na camada tabular, escolhendo Parquet ou CSV."""
    path = Path(path).with_suffix(TABLE_SUFFIX)
    ensure_dir(path.parent)
    if PARQUET_AVAILABLE:
        df.to_parquet(path, index=False)
    else:  # pragma: no cover
        df.to_csv(path, index=False, encoding="utf-8")
    return path


def read_table(path: Path) -> pd.DataFrame:
    """Lê uma tabela gravada por :func:`write_table` (aceita caminho sem sufixo)."""
    path = Path(path)
    if path.suffix in {".parquet", ".csv"}:
        candidates = [path]
    else:
        candidates = [path.with_suffix(".parquet"), path.with_suffix(".csv")]
    for candidate in candidates:
        if candidate.exists():
            if candidate.suffix == ".parquet":
                return pd.read_parquet(candidate)
            return pd.read_csv(candidate)
    raise FileNotFoundError(
        f"Tabela não encontrada: {path}. Rode as etapas anteriores do pipeline."
    )


def file_digest(path: Path, algorithm: str = "sha256") -> str:
    """Hash do arquivo — evidência de que o dado bruto não foi adulterado."""
    digest = hashlib.new(algorithm)
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65_536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def human_size(num_bytes: float) -> str:
    """Formata bytes de forma legível (1536 -> '1.5 KB')."""
    for unit in ("B", "KB", "MB", "GB"):
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} TB"


def describe_layer(directory: Path) -> pd.DataFrame:
    """Inventário de uma camada: arquivo, tamanho e data de modificação.

    Útil nos notebooks para mostrar o que cada fase produziu.
    """
    directory = Path(directory)
    rows = []
    if directory.exists():
        for file in sorted(directory.rglob("*")):
            if file.is_file() and file.name != ".gitkeep":
                stat = file.stat()
                rows.append(
                    {
                        "arquivo": str(file.relative_to(directory)),
                        "tamanho": human_size(stat.st_size),
                        "bytes": stat.st_size,
                        "modificado_em": datetime.fromtimestamp(
                            stat.st_mtime
                        ).strftime("%Y-%m-%d %H:%M"),
                    }
                )
    return pd.DataFrame(rows, columns=["arquivo", "tamanho", "bytes", "modificado_em"])
