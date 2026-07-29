"""Coleta das planilhas anuais oficiais do LIRAa/SES-RJ."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from dengue_rj.collectors.http import download

PORTAL_URL = (
    "https://www.saude.rj.gov.br/informacao-sus/novidades/2026/05/"
    "levantamento-de-indice-rapido-para-o-aedes-aegypti-liraa"
)
YEAR_URLS = {
    2020: "https://www.saude.rj.gov.br/comum/code/MostrarArquivo.php?C=NzY4MzA%2C",
    2021: "https://www.saude.rj.gov.br/comum/code/MostrarArquivo.php?C=NzY4MzE%2C",
    2022: "https://www.saude.rj.gov.br/comum/code/MostrarArquivo.php?C=NzY4MzI%2C",
    2023: "https://www.saude.rj.gov.br/comum/code/MostrarArquivo.php?C=NzY4MzM%2C",
    2024: "https://www.saude.rj.gov.br/comum/code/MostrarArquivo.php?C=NzY4MzQ%2C",
}


@dataclass(frozen=True)
class LiraaCollection:
    files: tuple[Path, ...]
    manifests: tuple[Path, ...]


def collect_liraa(
    years: tuple[int, ...] = tuple(range(2020, 2025)),
    output_directory: Path = Path("data/raw/liraa"),
) -> LiraaCollection:
    """Baixa e valida ZIPs anuais do LIRAa sem sobrescrita silenciosa."""
    invalid = set(years).difference(YEAR_URLS)
    if invalid:
        raise ValueError(f"Anos LIRAa sem URL validada: {sorted(invalid)}")
    files = []
    manifests = []
    for year in years:
        destination = output_directory / f"LIRAa_{year}.zip"
        path, sha256 = download(YEAR_URLS[year], destination)
        _validate_liraa_zip(path)
        manifest = destination.with_suffix(".zip.metadata.json")
        manifest.write_text(
            json.dumps(
                {
                    "source": "LIRAa — SES-RJ",
                    "portal_url": PORTAL_URL,
                    "url": YEAR_URLS[year],
                    "year": year,
                    "collected_at_utc": datetime.now(UTC).isoformat(),
                    "bytes": path.stat().st_size,
                    "sha256": sha256,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        files.append(path)
        manifests.append(manifest)
    return LiraaCollection(tuple(files), tuple(manifests))


def _validate_liraa_zip(path: Path) -> None:
    try:
        with ZipFile(path) as archive:
            members = [
                name
                for name in archive.namelist()
                if name.lower().endswith((".xls", ".xlsx", ".csv"))
            ]
            if not members or archive.testzip() is not None:
                raise ValueError("ZIP LIRAa não contém planilha íntegra")
    except BadZipFile as error:
        raise ValueError("Resposta LIRAa não é um ZIP válido") from error
