"""Coleta da Malha Municipal 2024 oficial do IBGE."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from dengue_rj.collectors.http import download

SOURCE_URL = (
    "https://geoftp.ibge.gov.br/organizacao_do_territorio/"
    "malhas_territoriais/malhas_municipais/municipio_2024/UFs/RJ/"
    "RJ_Municipios_2024.zip"
)


@dataclass(frozen=True)
class SpatialCollection:
    raw_file: Path
    manifest_file: Path


def collect_spatial_mesh(
    destination: Path = Path("data/raw/territorio/RJ_Municipios_2024.zip"),
) -> SpatialCollection:
    """Baixa e valida o shapefile municipal do RJ sem sobrescrever."""
    raw_file, sha256 = download(SOURCE_URL, destination)
    _validate_spatial_zip(raw_file)
    manifest = destination.with_suffix(".zip.metadata.json")
    manifest.write_text(
        json.dumps(
            {
                "source": "Malha Municipal Digital 2024 — IBGE",
                "url": SOURCE_URL,
                "reference_year": 2024,
                "collected_at_utc": datetime.now(UTC).isoformat(),
                "bytes": raw_file.stat().st_size,
                "sha256": sha256,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return SpatialCollection(raw_file, manifest)


def _validate_spatial_zip(path: Path) -> None:
    required_suffixes = {".shp", ".shx", ".dbf", ".prj"}
    try:
        with ZipFile(path) as archive:
            suffixes = {Path(name).suffix.lower() for name in archive.namelist()}
            if not required_suffixes.issubset(suffixes) or archive.testzip() is not None:
                raise ValueError("ZIP territorial não contém shapefile íntegro")
    except BadZipFile as error:
        raise ValueError("Resposta territorial não é um ZIP válido") from error
