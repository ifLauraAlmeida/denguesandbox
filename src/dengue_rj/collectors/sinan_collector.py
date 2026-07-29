"""Coleta oficial de microdados anuais de dengue do SINAN."""

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from zipfile import BadZipFile, ZipFile

import httpx

BASE_URL = (
    "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/"
    "SINAN/Dengue/csv/DENGBR{year_short:02d}.csv.zip"
)
PORTAL_URL = "https://dadosabertos.saude.gov.br/dataset/arboviroses-dengue"


@dataclass(frozen=True)
class SinanCollection:
    files: tuple[Path, ...]
    manifest_files: tuple[Path, ...]


def collect_sinan(
    years: tuple[int, ...] = (2020,),
    output_directory: Path = Path("data/raw/dengue/sinan"),
) -> SinanCollection:
    """Baixa ZIPs imutáveis; o piloto padrão coleta somente 2020."""
    invalid = set(years).difference(range(2000, 2100))
    if invalid:
        raise ValueError(f"Anos SINAN inválidos: {sorted(invalid)}")
    output_directory.mkdir(parents=True, exist_ok=True)
    files = []
    manifests = []
    for year in years:
        url = BASE_URL.format(year_short=year % 100)
        destination = output_directory / f"DENGBR{year % 100:02d}.csv.zip"
        if destination.exists():
            raise FileExistsError(f"Arquivo bruto já existe: {destination}")
        digest = hashlib.sha256()
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        try:
            with httpx.stream(
                "GET", url, timeout=httpx.Timeout(180, connect=30), follow_redirects=True
            ) as response:
                response.raise_for_status()
                with temporary.open("wb") as stream:
                    for chunk in response.iter_bytes():
                        digest.update(chunk)
                        stream.write(chunk)
            _validate_zip(temporary)
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
        manifest = destination.with_suffix(destination.suffix + ".metadata.json")
        metadata = {
            "source": "SINAN/Dengue — Portal de Dados Abertos do SUS",
            "portal_url": PORTAL_URL,
            "url": url,
            "year": year,
            "geographic_rule": "ID_MN_RESI (município de residência), obrigatório",
            "collected_at_utc": datetime.now(UTC).isoformat(),
            "bytes": destination.stat().st_size,
            "sha256": digest.hexdigest(),
        }
        manifest.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        files.append(destination)
        manifests.append(manifest)
    return SinanCollection(tuple(files), tuple(manifests))


def _validate_zip(path: Path) -> None:
    try:
        with ZipFile(path) as archive:
            members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
            if len(members) != 1 or archive.testzip() is not None:
                raise ValueError("ZIP SINAN deve conter um único CSV íntegro")
    except BadZipFile as error:
        raise ValueError("Resposta SINAN não é um ZIP válido") from error
