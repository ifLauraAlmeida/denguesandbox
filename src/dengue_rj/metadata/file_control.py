"""Inventário idempotente de integridade dos artefatos de dados."""

import csv
from datetime import UTC, datetime
from pathlib import Path

from dengue_rj.metadata.schemas import FILE_CONTROL_COLUMNS
from dengue_rj.utils.hashing import sha256_file

PIPELINE_VERSION = "0.1.0"


def refresh_file_control(
    root: Path = Path("."),
    output_file: Path = Path("data/metadata/controle_arquivos.csv"),
) -> Path:
    """Recria o controle para todos os arquivos brutos e processados presentes."""
    rows = []
    for layer in ("raw", "processed"):
        directory = root / "data" / layer
        for path in sorted(item for item in directory.rglob("*") if item.is_file()):
            if path.name == ".gitkeep":
                continue
            relative = path.relative_to(root).as_posix()
            line_count, column_count = _tabular_shape(path)
            stat = path.stat()
            domain = path.relative_to(directory).parts[0]
            rows.append(
                {
                    "arquivo": relative,
                    "camada": layer,
                    "fonte": _source_for(relative),
                    "data_criacao": _iso_timestamp(stat.st_ctime),
                    "data_modificacao": _iso_timestamp(stat.st_mtime),
                    "quantidade_linhas": line_count,
                    "quantidade_colunas": column_count,
                    "hash_sha256": sha256_file(path),
                    "arquivo_origem": (
                        "" if layer == "raw" else f"data/raw/{domain}/"
                    ),
                    "status_validacao": "inventariado_hash_calculado",
                    "versao_pipeline": PIPELINE_VERSION,
                }
            )
    destination = root / output_file
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FILE_CONTROL_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return destination


def _tabular_shape(path: Path) -> tuple[str | int, str | int]:
    if path.suffix.lower() != ".csv":
        return "", ""
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as stream:
        reader = csv.reader(stream)
        try:
            header = next(reader)
        except StopIteration:
            return 0, 0
        return sum(1 for _ in reader), len(header)


def _iso_timestamp(value: float) -> str:
    return datetime.fromtimestamp(value, UTC).isoformat()


def _source_for(relative: str) -> str:
    normalized = relative.casefold()
    if "sinan" in normalized or "dengue" in normalized:
        return "SINAN/DATASUS"
    if "liraa" in normalized:
        return "LIRAa/SES-RJ"
    if "ripsa" in normalized:
        return "RIPSA/SES-RJ"
    if "sinisa" in normalized:
        return "SINISA/Ministério das Cidades"
    if "snis" in normalized:
        return "SNIS/Ministério das Cidades"
    if "territorio" in normalized or "ibge" in normalized or "municip" in normalized:
        return "IBGE"
    return "fonte_mista_ou_derivada"
