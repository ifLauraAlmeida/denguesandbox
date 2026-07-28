"""Inicialização idempotente dos dicionários de metadados."""

import csv
import json
from collections.abc import Mapping
from pathlib import Path

from dengue_rj.metadata.schemas import (
    CALCULATION_COLUMNS,
    COLLECTION_COLUMNS,
    FILE_CONTROL_COLUMNS,
    VARIABLE_COLUMNS,
)

SCHEMAS = {
    "dicionario_coleta.csv": COLLECTION_COLUMNS,
    "dicionario_calculos.csv": CALCULATION_COLUMNS,
    "dicionario_variaveis.csv": VARIABLE_COLUMNS,
    "controle_arquivos.csv": FILE_CONTROL_COLUMNS,
}


def initialize_metadata(directory: Path = Path("data/metadata")) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    created = []
    for name, columns in SCHEMAS.items():
        path = directory / name
        if path.exists():
            continue
        with path.open("w", newline="", encoding="utf-8") as stream:
            csv.writer(stream).writerow(columns)
        created.append(path)
    return created


def append_collection_metadata(
    values: Mapping[str, object],
    path: Path = Path("data/metadata/dicionario_coleta.csv"),
) -> None:
    """Acrescenta coleta usando o schema canônico e JSON válido para objetos."""
    if not path.exists():
        initialize_metadata(path.parent)
    unknown = set(values).difference(COLLECTION_COLUMNS)
    if unknown:
        raise ValueError(f"Campos de coleta desconhecidos: {sorted(unknown)}")
    row: list[str] = []
    for column in COLLECTION_COLUMNS:
        value = values.get(column, "")
        serialized = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value
        row.append(str(serialized) if serialized is not None else "")
    with path.open("a", newline="", encoding="utf-8") as stream:
        csv.writer(stream).writerow(row)


def append_calculation_metadata(
    values: Mapping[str, object],
    path: Path = Path("data/metadata/dicionario_calculos.csv"),
) -> None:
    """Acrescenta cálculo usando o schema canônico."""
    if not path.exists():
        initialize_metadata(path.parent)
    unknown = set(values).difference(CALCULATION_COLUMNS)
    if unknown:
        raise ValueError(f"Campos de cálculo desconhecidos: {sorted(unknown)}")
    row = []
    for column in CALCULATION_COLUMNS:
        value = values.get(column, "")
        serialized = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value
        row.append(str(serialized) if serialized is not None else "")
    with path.open("a", newline="", encoding="utf-8") as stream:
        csv.writer(stream).writerow(row)
